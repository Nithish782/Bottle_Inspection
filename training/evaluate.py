"""
Evaluate trained model on test set.
Prints mAP, per-class precision & recall.
Run: python evaluate.py
"""
from ultralytics import YOLO

MODEL_PT  = "../models/best.pt"
DATA_YAML = "../dataset/annotated/data.yaml"
IMG_SIZE  = 640

def evaluate():
    model   = YOLO(MODEL_PT)
    metrics = model.val(
        data    = DATA_YAML,
        imgsz   = IMG_SIZE,
        split   = "test",
        plots   = True,
        save_json = True,
    )

    print("\n====== Evaluation Results ======")
    print(f"mAP@0.5:      {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95: {metrics.box.map:.4f}")
    print(f"Precision:    {metrics.box.mp:.4f}")
    print(f"Recall:       {metrics.box.mr:.4f}")
    print("\nPer-class AP@0.5:")
    for name, ap in zip(metrics.names.values(), metrics.box.ap50):
        print(f"  {name:<20} {ap:.4f}")

if __name__ == "__main__":
    evaluate()