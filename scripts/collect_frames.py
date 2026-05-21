"""
Webcam / RTSP frame collector for dataset building.

Usage Examples:
----------------
# Webcam
python collect_frames.py --source webcam --class fill_proper --count 200

# RTSP Stream
python collect_frames.py --source rtsp --rtsp "rtsp://username:password@192.168.1.10:554/stream" --class label_torn --count 150

# Auto capture every 1 second
python collect_frames.py --source rtsp --rtsp "rtsp://..." --class fill_under --count 300 --interval 1
"""

import cv2
import os
import time
import argparse

SAVE_ROOT = "../dataset/raw"

CLASSES = [
    "fill_proper",
    "fill_under",
    "fill_over",
    "label_proper",
    "label_torn",
    "label_missing"
]


def get_capture(
    source_type="webcam",
    cam_id=0,
    rtsp_url="rtsp://admin:Nvr@spritle@172.16.16.29:554/streaming/channels/1"
):
    """
    Create VideoCapture object for webcam or RTSP
    """

    if source_type == "webcam":
        print(f"[INFO] Opening webcam (ID={cam_id})")
        cap = cv2.VideoCapture(cam_id)

    elif source_type == "rtsp":
        if rtsp_url is None:
            raise ValueError("RTSP URL is required for RTSP source")

        print(f"[INFO] Opening RTSP stream...")
        cap = cv2.VideoCapture(rtsp_url)

    else:
        raise ValueError("Invalid source type")

    return cap


def collect(class_name, count, interval=0.5,
            source_type="webcam",
            cam_id=0,
            rtsp_url=None):

    if class_name not in CLASSES:
        print(f"Unknown class '{class_name}'")
        print(f"Choose from: {CLASSES}")
        return

    save_dir = os.path.join(SAVE_ROOT, class_name)
    os.makedirs(save_dir, exist_ok=True)

    # Find next available index
    existing = [f for f in os.listdir(save_dir) if f.endswith(".jpg")]
    start_idx = len(existing)

    # Open source
    cap = get_capture(
        source_type=source_type,
        cam_id=cam_id,
        rtsp_url=rtsp_url
    )

    if not cap.isOpened():
        print("[ERROR] Cannot open video source")
        return

    # Webcam resolution
    if source_type == "webcam":
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"\n[Collect] Class: '{class_name}'")
    print(f"[Collect] Target: {count} frames")
    print(f"[Collect] Source: {source_type}")

    print("\nControls:")
    print("  SPACE = capture")
    print("  A     = auto-capture toggle")
    print("  Q     = quit\n")

    saved = 0
    auto = False
    last_save = 0

    while saved < count:

        ret, frame = cap.read()

        if not ret:
            print("[WARNING] Failed to read frame")
            break

        # Resize display if RTSP frame is huge
        display = frame.copy()

        h, w = display.shape[:2]

        max_width = 1280
        if w > max_width:
            scale = max_width / w
            display = cv2.resize(
                display,
                (int(w * scale), int(h * scale))
            )

        # HUD
        cv2.putText(display,
                    f"Class: {class_name}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2)

        cv2.putText(display,
                    f"Saved: {saved}/{count}",
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2)

        cv2.putText(display,
                    f"Source: {source_type}",
                    (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 0),
                    2)

        cv2.putText(display,
                    f"Auto: {'ON' if auto else 'OFF'}",
                    (10, 135),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255) if auto else (100, 100, 100),
                    2)

        cv2.putText(display,
                    "SPACE=capture  A=auto  Q=quit",
                    (10, display.shape[0] - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (200, 200, 200),
                    1)

        cv2.imshow("AquaVision — Data Collector", display)

        key = cv2.waitKey(1) & 0xFF
        now = time.time()

        if key == ord('q'):
            break

        if key == ord('a'):
            auto = not auto
            last_save = now

        should_save = (
            key == ord(' ') or
            (auto and (now - last_save >= interval))
        )

        if should_save:

            fname = os.path.join(
                save_dir,
                f"{class_name}_{start_idx + saved:04d}.jpg"
            )

            cv2.imwrite(fname, frame)

            saved += 1
            last_save = now

            print(f"Saved: {fname}")

    cap.release()
    cv2.destroyAllWindows()

    print(f"\n[Collect] Done.")
    print(f"{saved} frames saved to '{save_dir}'")


if __name__ == "__main__":

    ap = argparse.ArgumentParser()

    # Source selection
    ap.add_argument(
        "--source",
        choices=["webcam", "rtsp"],
        default="webcam",
        help="Video source type"
    )

    # Webcam
    ap.add_argument(
        "--cam",
        type=int,
        default=0,
        help="Webcam ID"
    )

    # RTSP
    ap.add_argument(
        "--rtsp",
        type=str,
        default=None,
        help="RTSP stream URL"
    )

    # Dataset settings
    ap.add_argument(
        "--class",
        dest="cls",
        required=True,
        help="Class name"
    )

    ap.add_argument(
        "--count",
        type=int,
        default=200
    )

    ap.add_argument(
        "--interval",
        type=float,
        default=0.5,
        help="Seconds between auto captures"
    )

    args = ap.parse_args()

    collect(
        class_name=args.cls,
        count=args.count,
        interval=args.interval,
        source_type=args.source,
        cam_id=args.cam,
        rtsp_url=args.rtsp
    )