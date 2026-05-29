import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "reports.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bottle_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('PASS', 'DEFECT')),
            defect_type TEXT DEFAULT '',
            confidence REAL DEFAULT 0.0,
            camera_source TEXT DEFAULT '',
            frame_image_path TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_detections_timestamp
        ON detections(timestamp)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_detections_status
        ON detections(status)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_detections_defect_type
        ON detections(defect_type)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_detections_camera_source
        ON detections(camera_source)
    """)
    conn.commit()
    conn.close()


def save_detection(bottle_id, status, defect_type, confidence, camera_source, frame_image_path=""):
    conn = get_connection()
    conn.execute(
        """INSERT INTO detections (timestamp, bottle_id, status, defect_type, confidence, camera_source, frame_image_path)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bottle_id, status, defect_type, round(confidence, 4), camera_source, frame_image_path)
    )
    conn.commit()
    detection_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return detection_id


def query_detections(page=1, limit=20, status=None, defect_type=None, camera_source=None,
                     start_date=None, end_date=None, sort_by="timestamp", sort_order="desc"):
    allowed_sort = {"id", "timestamp", "bottle_id", "status", "defect_type", "confidence", "camera_source"}
    if sort_by not in allowed_sort:
        sort_by = "timestamp"
    if sort_order.lower() not in ("asc", "desc"):
        sort_order = "desc"

    conditions = []
    params = []

    if status and status.upper() in ("PASS", "DEFECT"):
        conditions.append("status = ?")
        params.append(status.upper())

    if defect_type:
        conditions.append("defect_type LIKE ?")
        params.append(f"%{defect_type}%")

    if camera_source:
        conditions.append("camera_source = ?")
        params.append(camera_source)

    if start_date:
        conditions.append("timestamp >= ?")
        params.append(start_date)

    if end_date:
        conditions.append("timestamp <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    conn = get_connection()

    count_row = conn.execute(
        f"SELECT COUNT(*) FROM detections WHERE {where_clause}", params
    ).fetchone()
    total_count = count_row[0]

    offset = (page - 1) * limit
    rows = conn.execute(
        f"SELECT * FROM detections WHERE {where_clause} ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()

    conn.close()

    results = [dict(r) for r in rows]
    return results, total_count


def get_summary_stats():
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN status='DEFECT' THEN 1 ELSE 0 END) AS defective
        FROM detections
    """).fetchone()

    first_row = conn.execute("SELECT timestamp FROM detections ORDER BY timestamp ASC LIMIT 1").fetchone()
    conn.close()

    total = row["total"] or 0
    passed = row["passed"] or 0
    defective = row["defective"] or 0
    accuracy = round((passed / total * 100), 1) if total > 0 else 0.0

    return {
        "total_bottles": total,
        "passed_bottles": passed,
        "defective_bottles": defective,
        "detection_accuracy": accuracy,
    }


def get_camera_analytics():
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            camera_source,
            COUNT(*) AS total,
            SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN status='DEFECT' THEN 1 ELSE 0 END) AS rejected
        FROM detections
        WHERE camera_source != ''
        GROUP BY camera_source
        ORDER BY total DESC
    """).fetchall()
    conn.close()

    result = []
    for r in rows:
        total = r["total"] or 0
        passed = r["passed"] or 0
        rejected = r["rejected"] or 0
        accuracy = round((passed / total * 100), 1) if total > 0 else 0.0
        result.append({
            "camera": r["camera_source"],
            "total_bottles": total,
            "passed_bottles": passed,
            "rejected_bottles": rejected,
            "accuracy": accuracy,
        })
    return result


def get_analytics_data():
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            DATE(timestamp) AS day,
            COUNT(*) AS total,
            SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) AS passed,
            SUM(CASE WHEN status='DEFECT' THEN 1 ELSE 0 END) AS defective
        FROM detections
        GROUP BY DATE(timestamp)
        ORDER BY day ASC
    """).fetchall()
    conn.close()

    daily = []
    weekly = {}
    monthly = {}

    for r in rows:
        day_str = r["day"]
        day_date = datetime.strptime(day_str, "%Y-%m-%d")
        total = r["total"]
        passed = r["passed"]
        defective = r["defective"]

        daily.append({
            "date": day_str,
            "total": total,
            "passed": passed,
            "defective": defective,
        })

        week_key = day_date.strftime("%Y-W%W")
        if week_key not in weekly:
            weekly[week_key] = {"week": week_key, "total": 0, "passed": 0, "defective": 0}
        weekly[week_key]["total"] += total
        weekly[week_key]["passed"] += passed
        weekly[week_key]["defective"] += defective

        month_key = day_date.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"month": month_key, "total": 0, "passed": 0, "defective": 0}
        monthly[month_key]["total"] += total
        monthly[month_key]["passed"] += passed
        monthly[month_key]["defective"] += defective

    return {
        "daily": daily,
        "weekly": sorted(weekly.values(), key=lambda x: x["week"]),
        "monthly": sorted(monthly.values(), key=lambda x: x["month"]),
    }


def get_distinct_cameras():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT camera_source FROM detections WHERE camera_source != '' ORDER BY camera_source").fetchall()
    conn.close()
    return [r["camera_source"] for r in rows]


def clear_all_detections():
    """Delete all detection records and reset the autoincrement counter."""
    conn = get_connection()
    conn.execute("DELETE FROM detections")
    conn.execute("DELETE FROM sqlite_sequence WHERE name='detections'")
    conn.commit()
    conn.close()


def get_distinct_defect_types():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT defect_type FROM detections WHERE defect_type != '' ORDER BY defect_type").fetchall()
    conn.close()
    return [r["defect_type"] for r in rows]
