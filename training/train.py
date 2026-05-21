"""
YOLOv8 Training Script for Water Bottle Inspection
Run: python train.py
"""
from ultralytics import YOLO
import os

# ── Config ────────────────────────────────────────────────────────────
DATA_YAML  = "../dataset/annotated/data.yaml"
MODEL_BASE = "yolov8s.pt"       # yolov8n=fastest, yolov8s=balanced, yolov8m=accurate
EPOCHS     = 100
IMG_SIZE   = 640
BATCH      = 16
PROJECT    = "runs"
RUN_NAME   = "bottle_inspection"
DEVICE     = 0                  # 0=GPU, "cpu"=CPU

def train():
    model = YOLO(MODEL_BASE)

    results = model.train(
        data        = DATA_YAML,
        epochs      = EPOCHS,
        imgsz       = IMG_SIZE,
        batch       = BATCH,
        project     = PROJECT,
        name        = RUN_NAME,
        device      = DEVICE,
        patience    = 20,           # early stopping
        save        = True,
        plots       = True,
        workers     = 4,
        optimizer   = "AdamW",
        lr0         = 0.001,
        lrf         = 0.01,
        momentum    = 0.937,
        weight_decay= 0.0005,
        warmup_epochs    = 3,
        box         = 7.5,
        cls         = 0.5,
        dfl         = 1.5,
        # Augmentation
        hsv_h       = 0.015,
        hsv_s       = 0.7,
        hsv_v       = 0.4,
        degrees     = 5.0,
        translate   = 0.1,
        scale       = 0.5,
        flipud      = 0.0,
        fliplr      = 0.5,
        mosaic      = 1.0,
        mixup       = 0.1,
        copy_paste  = 0.1,
    )

    print("\n[Train] Training complete.")
    print(f"[Train] Best weights: {results.save_dir}/weights/best.pt")

    # Copy best weights to /models/
    import shutil
    os.makedirs("../models", exist_ok=True)
    shutil.copy(f"{results.save_dir}/weights/best.pt", "../models/best.pt")
    print("[Train] Copied best.pt to ../models/")

if __name__ == "__main__":
    train()