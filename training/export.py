"""
Export best.pt → ONNX for backend inference.
Run: python export.py
"""
from ultralytics import YOLO
import shutil, os

MODEL_PT   = "../models/best_v1.pt"
OUTPUT_DIR = "../models"

def export():
    model = YOLO(MODEL_PT)

    # Standard ONNX (CPU inference)
    model.export(
        format   = "onnx",
        imgsz    = 640,
        opset    = 17,
        simplify = True,
        dynamic  = False,
    )

    # FP16 ONNX (faster on GPU)
    model.export(
        format   = "onnx",
        imgsz    = 640,
        opset    = 17,
        simplify = True,
        half     = True,
        dynamic  = False,
    )

    # Move exported files to /models/
    for fname in ["best.onnx"]:
        src = os.path.join(os.path.dirname(MODEL_PT), fname)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUTPUT_DIR, fname))
            print(f"[Export] Saved: {OUTPUT_DIR}/{fname}")

    print("[Export] Done. Use best.onnx in backend/config.py")

if __name__ == "__main__":
    export()