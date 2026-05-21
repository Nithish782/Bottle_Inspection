"""
Run YOLOv8 inference on a video file or webcam and display results.
Usage:
    python inference_video.py --source video.mp4
    python inference_video.py --source 0          (webcam)
    python inference_video.py --source video.mp4 --save
"""
import cv2
import time
import argparse
import numpy as np
from ultralytics import YOLO

# ── Config ────────────────────────────────────────────────────────────
MODEL_PATH  = "../models/best_v1.pt"   # use .pt directly for simplicity
CONF_THRESH = 0.45
IOU_THRESH  = 0.5
INPUT_SIZE  = 640

# Class names must match your training order
CLASS_NAMES = [
    "bottle",
    "proper_fill",
    "under_fill",
    "over_fill",
    "label_proper",
    "label_torn",
    "label_missing",
]

# Colors per class (BGR)
CLASS_COLORS = {
    "bottle":        (255, 255, 255),  # white
    "proper_fill":   (0, 230, 118),    # green
    "under_fill":    (0, 171, 255),    # amber
    "over_fill":     (82,  82, 255),   # red
    "label_proper":  (0, 230, 118),    # green
    "label_torn":    (0, 171, 255),    # amber
    "label_missing": (82,  82, 255),   # red
}

PASS_CLASSES = {"proper_fill", "label_proper"}


def get_status_color(name):
    if name in PASS_CLASSES:
        return (0, 230, 118)   # green
    if name in {"fill_under", "label_torn"}:
        return (0, 171, 255)   # amber
    return (82, 82, 255)       # red


def draw_detections(frame, results):
    """Draw bounding boxes, labels, confidence on frame."""
    boxes = results[0].boxes
    elapsed = 0

    pass_count = 0
    fail_count = 0

    if boxes is not None and len(boxes):
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf    = float(box.conf[0])
            cls_id  = int(box.cls[0])
            name    = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else "unknown"
            color   = get_status_color(name)

            # Skip drawing separate box for bottle class
            # (it will be covered by fill/label boxes)
            if name == "bottle":
                # Draw thin white outline for bottle
                cv2.rectangle(frame, (x1, y1), (x2, y2), (180,180,180), 1)
                continue

            status = "PASS" if name in PASS_CLASSES else "FAIL"

            if name in PASS_CLASSES:
                pass_count += 1
            else:
                fail_count += 1

            # Bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Corner accents
            cs = 14
            corners = [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]
            for (cx, cy, dx, dy) in corners:
                cv2.line(frame, (cx+dx*cs, cy), (cx, cy), color, 3)
                cv2.line(frame, (cx, cy), (cx, cy+dy*cs), color, 3)

            # Label background
            label   = f"{name.replace('_',' ').title()}  {conf:.0%}  {status}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(frame, (x1, y1-26), (x1+tw+10, y1), (0, 0, 0), -1)
            cv2.putText(frame, label, (x1+5, y1-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)

            # Fill level line
            if "fill" in name:
                ratio  = 0.25 if name=="proper_fill" else 0.65 if name=="under_fill" else 0.05
                fy     = int(y1 + (y2-y1)*ratio)
                lcolor = (0,171,255) if name=="under_fill" else \
                         (82,82,255) if name=="over_fill"  else (0,230,118)
                dash_len = 8
                for dx in range(x1+4, x2-4, dash_len*2):
                    cv2.line(frame, (dx, fy), (min(dx+dash_len, x2-4), fy), lcolor, 1)

    return frame, pass_count, fail_count


def run(source, save=False, headless=False):
    print(f"[Video] Loading model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print("[Video] Model loaded.")

    # Open video or webcam
    cap = cv2.VideoCapture(int(source) if source.isdigit() else source)
    if not cap.isOpened():
        print(f"[Video] ERROR: Cannot open source '{source}'")
        return

    w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    # Video writer
    writer = None
    if save:
        out_path = source.rsplit(".", 1)[0] + "_result.mp4" if not source.isdigit() else "webcam_result.mp4"
        writer   = cv2.VideoWriter(out_path,
                                   cv2.VideoWriter_fourcc(*"mp4v"),
                                   fps, (w, h))
        print(f"[Video] Saving output to: {out_path}")

    frame_count = 0
    fps_list    = []
    total_pass  = 0
    total_fail  = 0

    print("[Video] Running... Press Q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t0 = time.perf_counter()

        # Inference
        results = model(frame,
                        conf    = CONF_THRESH,
                        iou     = IOU_THRESH,
                        imgsz   = INPUT_SIZE,
                        verbose = False)

        frame, p, f = draw_detections(frame, results)
        total_pass += p
        total_fail += f

        # FPS
        elapsed = time.perf_counter() - t0
        cur_fps = 1.0 / elapsed if elapsed > 0 else 0
        fps_list.append(cur_fps)
        if len(fps_list) > 30: fps_list.pop(0)
        avg_fps = sum(fps_list) / len(fps_list)

        frame_count += 1

        # HUD overlay
        cv2.rectangle(frame, (0, 0), (340, 90), (0, 0, 0), -1)
        cv2.putText(frame, f"AquaVision Inspection",
                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,210,255), 2)
        cv2.putText(frame, f"FPS: {avg_fps:.1f}   Latency: {elapsed*1000:.1f}ms",
                    (10, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,200), 1)
        cv2.putText(frame, f"PASS: {total_pass}   FAIL: {total_fail}   Frame: {frame_count}",
                    (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200,200,200), 1)

        if not headless:
            try:
                cv2.imshow("AquaVision — Bottle Inspection", frame)
            except cv2.error:
                print("[Video] GUI not available, running in headless mode")
                headless = True

        if writer:
            writer.write(frame)

        if not headless:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    if writer:
        writer.release()
    if not headless:
        cv2.destroyAllWindows()

    print(f"\n[Video] Done.")
    print(f"  Frames processed : {frame_count}")
    print(f"  Avg FPS          : {sum(fps_list)/len(fps_list):.1f}")
    print(f"  Total PASS       : {total_pass}")
    print(f"  Total FAIL       : {total_fail}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="0",
                    help="Video file path or webcam index (default: 0)")
    ap.add_argument("--save",   action="store_true",
                    help="Save output video with detections")
    ap.add_argument("--headless", action="store_true",
                    help="Run in headless mode (no GUI display)")
    args = ap.parse_args()
    run(args.source, args.save, args.headless)