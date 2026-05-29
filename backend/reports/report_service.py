import time
from datetime import datetime
from database.models import (
    save_detection,
    query_detections,
    get_summary_stats,
    get_camera_analytics,
    get_analytics_data,
    get_distinct_cameras,
    get_distinct_defect_types,
)

session_start_time = time.time()


def log_detection(bottle_id, status, defect_type, confidence, camera_source, frame_image_path=""):
    return save_detection(bottle_id, status, defect_type, confidence, camera_source, frame_image_path)


def log_bottles(bottles, camera_source="Unknown"):
    for b in bottles:
        bottle_id = f"BOT-{b.get('id', '?')}"
        passed = b.get("pass", False)
        status = "PASS" if passed else "DEFECT"

        defect_type = ""
        if not passed:
            defects = []
            fill = b.get("fill", "")
            label = b.get("label", "")
            if fill == "under_fill":
                defects.append("Underfill")
            elif fill == "over_fill":
                defects.append("Overfill")
            if label == "label_torn":
                defects.append("Torn Label")
            elif label == "label_missing":
                defects.append("Missing Label")
            defect_type = ", ".join(defects) if defects else "Unknown Defect"

        confidence = b.get("overall_conf", 0) or 0

        save_detection(bottle_id, status, defect_type, confidence, camera_source)


def get_summary():
    stats = get_summary_stats()
    cameras = get_distinct_cameras()
    active_camera = cameras[0] if cameras else "N/A"

    elapsed = time.time() - session_start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)
    duration_str = f"{hours:02d}h {minutes:02d}m"

    return {
        **stats,
        "active_camera_source": active_camera,
        "inspection_duration": duration_str,
    }


def get_history(page=1, limit=20, status=None, defect_type=None, camera_source=None,
                start_date=None, end_date=None, sort_by="timestamp", sort_order="desc"):
    records, total = query_detections(
        page=page, limit=limit, status=status, defect_type=defect_type,
        camera_source=camera_source, start_date=start_date, end_date=end_date,
        sort_by=sort_by, sort_order=sort_order
    )
    return {
        "records": records,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": max(1, (total + limit - 1) // limit),
    }


def get_camera_analytics_data():
    return get_camera_analytics()


def get_analytics():
    return get_analytics_data()
