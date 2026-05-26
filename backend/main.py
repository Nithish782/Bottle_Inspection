import base64
import time
import asyncio
import cv2
import numpy as np
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from inference import inspector
from tracker  import tracker
from camera   import RTSPCameraSource
from config   import HOST, PORT, MAX_FPS

app = FastAPI(title="AquaVision Bottle Inspection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health")
def health():
    return {"status": "ok"}

# ── Session counters ──────────────────────────────────────────────────
session = {"total_pass": 0, "total_fail": 0, "frames": 0, "counted_ids": set()}
_min_frame_gap = 1.0 / MAX_FPS

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

            session["frames"] += 1
            for b in bottles:
                if b.get("id") not in session["counted_ids"]:
                    session["counted_ids"].add(b.get("id"))
                    if b["pass"]: session["total_pass"] += 1
                    else:         session["total_fail"] += 1

            await ws.send_json({
                "bottles":    bottles,
                "latency_ms": latency,
                "total_pass": session["total_pass"],
                "total_fail": session["total_fail"],
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

            session["frames"] += 1
            for b in bottles:
                if b.get("id") not in session["counted_ids"]:
                    session["counted_ids"].add(b.get("id"))
                    if b["pass"]: session["total_pass"] += 1
                    else:         session["total_fail"] += 1

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

app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)