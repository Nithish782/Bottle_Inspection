import csv
import io
from database.models import query_detections


def export_csv(page=1, limit=10000, status=None, defect_type=None, camera_source=None,
               start_date=None, end_date=None):
    records, _ = query_detections(
        page=1, limit=limit, status=status, defect_type=defect_type,
        camera_source=camera_source, start_date=start_date, end_date=end_date,
        sort_by="timestamp", sort_order="desc"
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Bottle ID", "Status", "Defect Type", "Confidence", "Camera Source"])

    for r in records:
        writer.writerow([
            r["id"],
            r["timestamp"],
            r["bottle_id"],
            r["status"],
            r["defect_type"],
            f'{r["confidence"]:.2%}' if isinstance(r["confidence"], float) else r["confidence"],
            r["camera_source"],
        ])

    return output.getvalue()
