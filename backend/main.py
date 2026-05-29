import base64
import time
import asyncio
import cv2
import numpy as np
import json
import os
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from inference import inspector
from tracker  import tracker
from camera   import RTSPCameraSource
from config   import HOST, PORT, MAX_FPS
from database.models import init_db
from reports.report_service import log_bottles, get_summary, get_history
from reports.report_service import get_camera_analytics_data, get_analytics
from reports.report_service import clear_all_history
from reports.export_csv import export_csv
from reports.export_pdf import generate_pdf
from reports.export_excel import generate_excel
from database.models import get_distinct_cameras
from auth.auth import router as auth_router

app = FastAPI(title="AquaVision Bottle Inspection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)



@app.get("/health")
def health():
    return {"status": "ok"}

# ── Init DB on startup ────────────────────────────────────────────────
init_db()

# ── Session counters ──────────────────────────────────────────────────
session = {"total_pass": 0, "total_fail": 0, "frames": 0, "counted_ids": set(), "camera_source": "Webcam 1"}
_min_frame_gap = 1.0 / MAX_FPS

# ── Settings ──────────────────────────────────────────────────────────
SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "save_detection_history": True,
    "default_camera_source": "webcam",
    "camera_resolution": "720p",
    "auto_record_on_detection": False,
    "video_save_path": os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings"),
    "recording_format": "mp4",
    "show_bounding_boxes": True,
    "show_labels": True,
    "show_confidence_score": True,
    "overlay_opacity": 100,
}

app_settings = {}

def load_settings():
    global app_settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded = json.load(f)
                app_settings = {**DEFAULT_SETTINGS, **loaded}
        except Exception as e:
            print(f"[Main] Error loading settings: {e}")
            app_settings = dict(DEFAULT_SETTINGS)
    else:
        app_settings = dict(DEFAULT_SETTINGS)
        save_settings()

def save_settings():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(app_settings, f, indent=4)
    except Exception as e:
        print(f"[Main] Error saving settings: {e}")

# ── Detection Recorder ────────────────────────────────────────────────
class DetectionRecorder:
    def __init__(self):
        self.writer = None
        self.recording = False
        self.last_detection_time = 0
        self.current_file = ""
        self.recording_timeout = 5.0

    def _get_fourcc(self, fmt):
        codecs = {
            "mp4": cv2.VideoWriter_fourcc(*"mp4v"),
            "avi": cv2.VideoWriter_fourcc(*"XVID"),
            "mov": cv2.VideoWriter_fourcc(*"mp4v"),
        }
        return codecs.get(fmt, cv2.VideoWriter_fourcc(*"mp4v"))

    def _draw_overlay(self, frame, bottles):
        h, w = frame.shape[:2]
        for b in bottles:
            x1, y1, x2, y2 = map(int, b["box"])
            x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)

            if b["pass"]:
                color = (0, 230, 118)
            elif b.get("fill") in ("under_fill",) or b.get("label") in ("label_torn",):
                color = (0, 171, 255)
            else:
                color = (82, 82, 255)

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Corner brackets
            cs = min(16, (x2 - x1) * 0.15, (y2 - y1) * 0.1)
            for cx, cy, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
                cv2.line(frame, (int(cx + dx * cs), cy), (cx, cy), color, 3)
                cv2.line(frame, (cx, cy), (cx, int(cy + dy * cs)), color, 3)

            # Fill line
            fill = b.get("fill", "")
            bw = x2 - x1
            bh = y2 - y1
            ratio = 0.25
            line_col = (68, 138, 255)
            if fill == "under_fill":
                ratio = 0.65
                line_col = (0, 171, 255)
            elif fill == "over_fill":
                ratio = 0.05
                line_col = (82, 82, 255)
            fy = y1 + int(bh * ratio)
            cv2.line(frame, (x1 + 6, fy), (x2 - 6, fy), line_col, 2, cv2.LINE_AA)

            # Label chip
            status = "PASS" if b["pass"] else "FAIL"
            fill_str = fill.replace("_", " ").title()
            lbl_str = b.get("label", "").replace("_", " ").title()
            conf = int((b.get("overall_conf", 0) or 0) * 100)
            text = f"#{b.get('id', '?')} {status} | {fill_str} | {lbl_str} | {conf}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, 0.45, 1)
            lx1, ly1 = max(0, x1), max(0, y1 - 24)
            lx2, ly2 = min(w, x1 + tw + 18), max(0, y1 - 2)
            cv2.rectangle(frame, (lx1, ly1), (lx2, ly2), (0, 0, 0), -1)
            cv2.putText(frame, text, (x1 + 9, y1 - 8), font, 0.45, color, 1, cv2.LINE_AA)

            # Label sub-box
            if b.get("label_box"):
                lx1b, ly1b, lx2b, ly2b = map(int, b["label_box"])
                lx1b, ly1b = max(0, lx1b), max(0, ly1b)
                lx2b, ly2b = min(w, lx2b), min(h, ly2b)
                lcol = (0, 230, 118) if b.get("label") == "label_proper" else ((0, 171, 255) if b.get("label") == "label_torn" else (82, 82, 255))
                cv2.rectangle(frame, (lx1b, ly1b), (lx2b, ly2b), lcol, 1, cv2.LINE_AA)
                cv2.putText(frame, lbl_str, (lx1b + 2, ly1b - 4), font, 0.4, lcol, 1, cv2.LINE_AA)

        return frame

    def update(self, frame, bottles):
        has_detections = len(bottles) > 0
        if not app_settings.get("auto_record_on_detection", False):
            if self.recording:
                self.stop()
            return

        save_path = app_settings.get("video_save_path", "")
        if save_path:
            os.makedirs(save_path, exist_ok=True)
        else:
            if self.recording:
                self.stop()
            return

        rec_format = app_settings.get("recording_format", "mp4")

        if has_detections:
            frame = self._draw_overlay(frame, bottles)

            if not self.recording:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"detection_recording_{timestamp}.{rec_format}"
                filepath = os.path.join(save_path, filename)
                h, w = frame.shape[:2]
                fourcc = self._get_fourcc(rec_format)
                self.writer = cv2.VideoWriter(filepath, fourcc, min(app_settings.get("camera_fps", 20), 30), (w, h))
                self.recording = True
                self.current_file = filepath

            if self.writer:
                self.writer.write(frame)
            self.last_detection_time = time.time()

        elif self.recording and time.time() - self.last_detection_time > self.recording_timeout:
            self.stop()

    def stop(self):
        if self.writer:
            self.writer.release()
            self.writer = None
        self.recording = False
        self.current_file = ""

detection_recorder = DetectionRecorder()
load_settings()

# ── RTSP state ────────────────────────────────────────────────────────
rtsp_cap    = None
rtsp_active = False

# ── ROI state ─────────────────────────────────────────────────────────
ROI_FILE = "rois.json"
active_rois = []

if os.path.exists(ROI_FILE):
    try:
        with open(ROI_FILE, "r") as f:
            active_rois = json.load(f)
            print(f"[Main] Loaded {len(active_rois)} ROIs from {ROI_FILE}")
    except Exception as e:
        print(f"[Main] Error loading ROIs: {e}")

class RoiBody(BaseModel):
    rois: list

class SettingsBody(BaseModel):
    settings: dict

@app.get("/rois")
def get_rois():
    return {"rois": active_rois}

@app.post("/set-roi")
def set_roi(body: RoiBody):
    global active_rois
    active_rois = body.rois
    try:
        with open(ROI_FILE, "w") as f:
            json.dump(active_rois, f)
    except Exception as e:
        print(f"[Main] Error saving ROIs: {e}")
    return {"status": "ok", "count": len(active_rois)}

class RtspBody(BaseModel):
    url: str

@app.post("/open-rtsp")
def open_rtsp(body: RtspBody):
    global rtsp_cap, rtsp_active
    if rtsp_cap:
        rtsp_cap.release()
    try:
        rtsp_cap = RTSPCameraSource(body.url)
        rtsp_cap.open()
    except Exception as e:
        rtsp_cap = None
        return {"error": str(e)}
    rtsp_active = True
    return {"status": "ok"}

@app.post("/close-rtsp")
def close_rtsp():
    global rtsp_cap, rtsp_active
    rtsp_active = False
    if rtsp_cap:
        rtsp_cap.release()
        rtsp_cap = None
    return {"status": "closed"}

# ── WebSocket — Webcam / Mobile (browser sends frames) ───────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    print("[WS] Client connected")
    last_frame_time = 0.0
    try:
        while True:
            data = await ws.receive_json()
            now  = time.perf_counter()
            if now - last_frame_time < _min_frame_gap:
                continue
            last_frame_time = now
            try:
                img_bytes = base64.b64decode(data["frame"])
                arr       = np.frombuffer(img_bytes, np.uint8)
                frame     = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    raise ValueError("Empty frame")
            except Exception as e:
                await ws.send_json({"error": str(e)})
                continue

            bottles, latency = inspector.run(frame)
            # Filter bottles by ROI if any are configured
            if active_rois:
                frame_h, frame_w = frame.shape[:2]
                filtered_bottles = []
                for b in bottles:
                    bx1, by1, bx2, by2 = b["box"]
                    bcx = ((bx1 + bx2) / 2) / frame_w
                    bcy = ((by1 + by2) / 2) / frame_h
                    
                    in_roi = False
                    for r in active_rois:
                        if r["x"] <= bcx <= (r["x"] + r["w"]) and r["y"] <= bcy <= (r["y"] + r["h"]):
                            in_roi = True
                            break
                    if in_roi:
                        filtered_bottles.append(b)
                bottles = filtered_bottles
                
            bottles = tracker.update(bottles)
            detection_recorder.update(frame.copy(), bottles)

            session["frames"] += 1
            new_bottles = []
            for b in bottles:
                if b.get("id") not in session["counted_ids"]:
                    session["counted_ids"].add(b.get("id"))
                    if b["pass"]: session["total_pass"] += 1
                    else:         session["total_fail"] += 1
                    new_bottles.append(b)

            if new_bottles:
                log_bottles(new_bottles, session.get("camera_source", "Webcam 1"))

            await ws.send_json({
                "bottles":    bottles,
                "latency_ms": latency,
                "total_pass": session["total_pass"],
                "total_fail": session["total_fail"],
                "ts":         data.get("ts", 0)
            })
    except WebSocketDisconnect:
        print("[WS] Client disconnected")

# ── WebSocket — RTSP (backend reads frames, sends to browser) ────────
@app.websocket("/ws-rtsp")
async def websocket_rtsp(ws: WebSocket):
    await ws.accept()
    print("[WS-RTSP] Client connected")
    try:
        while rtsp_active and rtsp_cap and rtsp_cap.isOpened():
            ret, frame = rtsp_cap.read()
            if not ret or frame is None:
                await asyncio.sleep(0.05)
                continue

            if session["frames"] % 30 == 0:
                print(f"[DEBUG] Frame mean: {frame.mean():.2f}")

            bottles, latency = inspector.run(frame)
            bottles = tracker.update(bottles)
            detection_recorder.update(frame.copy(), bottles)

            session["frames"] += 1
            new_bottles = []
            for b in bottles:
                if b.get("id") not in session["counted_ids"]:
                    session["counted_ids"].add(b.get("id"))
                    if b["pass"]: session["total_pass"] += 1
                    else:         session["total_fail"] += 1
                    new_bottles.append(b)

            if new_bottles:
                log_bottles(new_bottles, session.get("camera_source", "Webcam 1"))

            # Encode frame as JPEG base64 to send to browser
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_b64 = base64.b64encode(buf).decode()

            await ws.send_json({
                "frame":      frame_b64,
                "bottles":    bottles,
                "latency_ms": latency,
                "total_pass": session["total_pass"],
                "total_fail": session["total_fail"],
            })
            await asyncio.sleep(1.0 / MAX_FPS)
    except WebSocketDisconnect:
        print("[WS-RTSP] Client disconnected")

@app.post("/reset")
def reset_session():
    session["total_pass"] = 0
    session["total_fail"] = 0
    session["frames"]     = 0
    session["counted_ids"] = set()
    return {"status": "reset"}

class CameraSourceBody(BaseModel):
    name: str

@app.get("/camera-source")
def get_camera_source():
    return {"name": session.get("camera_source", "Unknown")}

@app.post("/camera-source")
def set_camera_source(body: CameraSourceBody):
    session["camera_source"] = body.name
    print(f"[Main] Camera source changed to: {body.name}")
    return {"status": "ok", "name": body.name}

# ── Settings API ──────────────────────────────────────────────────────
@app.get("/settings")
def get_settings():
    return {"settings": app_settings}

@app.post("/settings")
def update_settings(body: SettingsBody):
    global app_settings
    app_settings.update(body.settings)
    save_settings()
    return {"status": "ok", "settings": app_settings}

@app.post("/settings/reset")
def reset_settings():
    global app_settings
    app_settings = dict(DEFAULT_SETTINGS)
    save_settings()
    return {"status": "ok", "settings": app_settings}

# ── Reports API ───────────────────────────────────────────────────────
class ReportsQueryBody(BaseModel):
    page: int = 1
    limit: int = 20
    status: str | None = None
    defect_type: str | None = None
    camera_source: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    sort_by: str = "timestamp"
    sort_order: str = "desc"

@app.get("/reports/summary")
def reports_summary():
    summary = get_summary()
    active = session.get("camera_source")
    if active:
        summary["active_camera_source"] = active
    return summary

@app.get("/reports/history")
def reports_history(page: int = 1, limit: int = 20,
                    status: str | None = None,
                    defect_type: str | None = None,
                    camera_source: str | None = None,
                    start_date: str | None = None,
                    end_date: str | None = None,
                    sort_by: str = "timestamp",
                    sort_order: str = "desc"):
    return get_history(page=page, limit=limit, status=status,
                       defect_type=defect_type, camera_source=camera_source,
                       start_date=start_date, end_date=end_date,
                       sort_by=sort_by, sort_order=sort_order)

@app.get("/reports/camera-analytics")
def reports_camera_analytics():
    return {"cameras": get_camera_analytics_data()}

@app.get("/reports/camera-sources")
def reports_camera_sources():
    return {"sources": get_distinct_cameras()}

@app.get("/reports/analytics")
def reports_analytics():
    return get_analytics()

@app.post("/reports/clear-history")
def reports_clear_history():
    """Clear all detection history, reset counters, and wipe analytics data."""
    result = clear_all_history()
    # Also reset in-memory session counters
    session["total_pass"] = 0
    session["total_fail"] = 0
    session["frames"] = 0
    session["counted_ids"] = set()
    # Reset tracker state
    tracker.reset()
    return result

@app.get("/reports/export/csv")
def reports_export_csv(page: int = 1, limit: int = 10000,
                       status: str | None = None,
                       defect_type: str | None = None,
                       camera_source: str | None = None,
                       start_date: str | None = None,
                       end_date: str | None = None):
    csv_data = export_csv(page=page, limit=limit, status=status,
                          defect_type=defect_type, camera_source=camera_source,
                          start_date=start_date, end_date=end_date)
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        iter([csv_data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@app.get("/reports/export/pdf")
def reports_export_pdf():
    try:
        pdf_buffer = generate_pdf()
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([pdf_buffer.getvalue()]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
        )
    except RuntimeError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/reports/export/excel")
def reports_export_excel(page: int = 1, limit: int = 10000,
                         status: str | None = None,
                         defect_type: str | None = None,
                         camera_source: str | None = None,
                         start_date: str | None = None,
                         end_date: str | None = None):
    try:
        excel_buffer = generate_excel(page=page, limit=limit, status=status,
                                      defect_type=defect_type, camera_source=camera_source,
                                      start_date=start_date, end_date=end_date)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            iter([excel_buffer.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=inspection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
        )
    except RuntimeError as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"error": str(e)})

app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)