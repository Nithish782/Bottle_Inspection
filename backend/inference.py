import os
import time
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    print("[Inference] ERROR: ultralytics not installed. Run: pip install ultralytics")
    YOLO = None

from config import MODEL_PATH, CONF_THRESH, IOU_THRESH
from utils  import parse_bottle, merge_bottle_detections

class BottleInspector:
    def __init__(self):
        self.model = None

        if not os.path.exists(MODEL_PATH):
            print(f"[Inference] WARNING: Model not found at {MODEL_PATH}")
            print("[Inference] Running in DEMO mode — train and export model first.")
            return

        if YOLO is None:
            return

        print(f"[Inference] Loading YOLO model: {MODEL_PATH}")
        self.model = YOLO(MODEL_PATH)
        print("[Inference] Model loaded successfully.")

    def run(self, frame):
        """
        Full pipeline: frame → detections → merged bottle results.
        Returns (bottles, latency_ms).
        If no model loaded, returns empty list.
        """
        t0 = time.perf_counter()

        if self.model is None:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return [], latency_ms

        results = self.model.predict(
            source=frame,
            conf=CONF_THRESH,
            iou=IOU_THRESH,
            verbose=False,
        )

        detections = []
        if len(results) > 0:
            boxes = results[0].boxes
            if len(boxes) > 0:
                cls_list = [int(b.cls[0].item()) for b in boxes]
                conf_list = [round(float(b.conf[0].item()), 2) for b in boxes]
                print(f"[Inference] {len(boxes)} raw detections | Classes: {cls_list} | Confs: {conf_list}")
            
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy()
                detections.append(parse_bottle(cls_id, conf, xyxy))

        bottles = merge_bottle_detections(detections)
        if bottles:
            print(f"[Inference] → {len(bottles)} bottles merged | Pass: {sum(1 for b in bottles if b['pass'])}, Fail: {sum(1 for b in bottles if not b['pass'])}")

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return bottles, latency_ms


# Singleton — imported by main.py
inspector = BottleInspector()