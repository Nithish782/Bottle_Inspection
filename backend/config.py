import os

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PT   = os.path.join(BASE_DIR, "..", "models", "best_v1.pt")
MODEL_ONNX = os.path.join(BASE_DIR, "..", "models", "best_v1.onnx")

# Prefer PT model if it exists, fallback to ONNX
MODEL_PATH = MODEL_PT if os.path.exists(MODEL_PT) else MODEL_ONNX

# ── Model ──────────────────────────────────────────────────────────────
INPUT_SIZE  = 640        # YOLOv8 input resolution
CONF_THRESH = 0.45       # minimum confidence to keep a detection
IOU_THRESH  = 0.5        # NMS IoU threshold

# ── Classes ────────────────────────────────────────────────────────────
CLASS_NAMES = [
    "bottle",
    "proper_fill",
    "under_fill",
    "over_fill",
    "label_proper",
    "label_torn",
    "label_missing",
]

BOTTLE_CLASS  = 0
FILL_CLASSES  = {1: "Proper Fill",  2: "Underfill",   3: "Overfill"}
LABEL_CLASSES = {4: "Proper Label", 5: "Torn Label",  6: "Missing Label"}

# A bottle PASSES only when both fill and label are proper
PASS_CLASSES  = {1, 4}

# ── Server ─────────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 8000

# ── Performance ────────────────────────────────────────────────────────
MAX_FPS        = 30      # cap frame processing rate
SKIP_FRAMES    = 1       # run detection every N frames (1 = every frame)
TRACKER_MAX_AGE = 10     # frames to keep a lost track alive