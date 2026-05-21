"""
Quick diagnostic: test model detection on a frame from the mobile camera.
Run: python test_model.py
"""
import cv2
import sys

try:
    from ultralytics import YOLO
except ImportError:
    print("[ERROR] ultralytics not installed")
    sys.exit(1)

from config import MODEL_PATH, CONF_THRESH, IOU_THRESH, CLASS_NAMES

# ── 1. Check model ────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"Model path : {MODEL_PATH}")
print(f"Conf thresh: {CONF_THRESH}")
print(f"IoU thresh : {IOU_THRESH}")

model = YOLO(MODEL_PATH)
model_names = model.names  # dict {0: 'class0', 1: 'class1', ...}
print(f"\n── Model's built-in class names ──")
for idx, name in model_names.items():
    print(f"  {idx}: {name}")

print(f"\n── Config CLASS_NAMES ──")
for idx, name in enumerate(CLASS_NAMES):
    print(f"  {idx}: {name}")

# ── 2. Check if they match ────────────────────────────────────────────
mismatch = False
for idx, name in model_names.items():
    config_name = CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else "MISSING"
    if name != config_name:
        print(f"\n  ⚠️  MISMATCH at index {idx}: model='{name}' vs config='{config_name}'")
        mismatch = True
if not mismatch:
    print("\n  ✅ All class names match!")

# ── 3. Grab one frame from mobile camera ──────────────────────────────
MOBILE_URL = "http://172.16.16.115:8080/video"
print(f"\n{'='*60}")
print(f"Connecting to: {MOBILE_URL}")

cap = cv2.VideoCapture(MOBILE_URL)
if not cap.isOpened():
    print("[ERROR] Cannot open mobile camera stream")
    sys.exit(1)

ret, frame = cap.read()
cap.release()

if not ret or frame is None:
    print("[ERROR] Could not read a frame")
    sys.exit(1)

print(f"Frame shape: {frame.shape}, mean pixel: {frame.mean():.2f}")

# ── 4. Run inference ──────────────────────────────────────────────────
print(f"\nRunning inference...")
results = model.predict(source=frame, conf=CONF_THRESH, iou=IOU_THRESH, verbose=False)

boxes = results[0].boxes
print(f"\n── Results ──")
print(f"Total detections: {len(boxes)}")

if len(boxes) == 0:
    print("\n⚠️  No objects detected!")
    print("   Try lowering CONF_THRESH in config.py (e.g. 0.25)")
    print("   Or point the camera at a bottle and run again.")
else:
    for i, box in enumerate(boxes):
        cls_id = int(box.cls[0].item())
        conf   = float(box.conf[0].item())
        xyxy   = box.xyxy[0].cpu().numpy()
        cls_name = model_names.get(cls_id, "unknown")
        print(f"  [{i}] class={cls_id} ({cls_name}), conf={conf:.3f}, box={xyxy}")

# ── 5. Save annotated frame ──────────────────────────────────────────
annotated = results[0].plot()
out_path = "test_detection.jpg"
cv2.imwrite(out_path, annotated)
print(f"\n✅ Saved annotated frame to: {out_path}")
print(f"{'='*60}\n")
