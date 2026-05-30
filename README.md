# AquaVision — Real-Time Bottle Inspection System

AI-powered industrial inspection dashboard for real-time bottle quality control. Detects fill-level defects (underfill, overfill) and label issues (torn, missing) on a live conveyor feed using YOLOv8, with a full-featured web interface for monitoring, analytics, and reporting.

---

## Features

- **Live Inspection** — Real-time object detection with bounding boxes, confidence scores, and pass/fail status
- **Multi-Source Camera** — Webcam, mobile camera (MJPEG), RTSP streams, and local video files
- **ROI Management** — Draw and configure regions of interest directly on the video feed
- **Detection Tracking** — Centroid-based tracker assigns stable IDs across frames to avoid duplicate counting
- **Reports & Export** — Paginated detection history with CSV, PDF, and Excel export
- **Camera Analytics** — Per-camera pass/fail breakdown and accuracy statistics
- **Daily/Trend Charts** — Bar and line charts for daily inspections and historical trends
- **Settings Panel** — Configure camera source, recording, overlay visibility, and system preferences
- **Auto Recording** — Automatically record video clips when defects are detected
- **Light/Dark Theme** — Toggle between dark and light modes
- **System Reset** — Clear all detection history, reports, and analytics with a single action

---

## Tech Stack

| Layer     | Technology                                                    |
|-----------|---------------------------------------------------------------|
| Model     | YOLOv8 (Ultralytics) — PT and ONNX support                   |
| Backend   | FastAPI + Uvicorn, WebSocket for real-time frame streaming    |
| Database  | SQLite (WAL mode) for detection records                       |
| Frontend  | Vanilla HTML/CSS/JS single-page app, Chart.js for analytics   |
| Exports   | ReportLab (PDF), openpyxl (Excel), native CSV                 |

---

## Project Structure

```
aquavision/
├── backend/
│   ├── main.py              # FastAPI app — endpoints, WebSocket handlers
│   ├── inference.py         # YOLOv8 model loading and prediction pipeline
│   ├── tracker.py           # Centroid-based bottle tracker
│   ├── camera.py            # RTSP camera source with auto-reconnect
│   ├── config.py            # Model paths, thresholds, server config
│   ├── utils.py             # Detection parsing and bottle merging logic
│   ├── settings.json        # Persisted user settings
│   ├── rois.json            # Saved ROI configurations
│   ├── requirements.txt     # Python dependencies
│   ├── database/
│   │   ├── models.py        # SQLite schema, queries, CRUD operations
│   │   └── reports.db       # SQLite database (auto-created)
│   └── reports/
│       ├── report_service.py  # Business logic for reports and history
│       ├── export_csv.py      # CSV export
│       ├── export_pdf.py      # PDF generation (ReportLab)
│       └── export_excel.py    # Excel export (openpyxl)
├── frontend/
│   ├── index.html           # Single-page app (all pages + styles)
│   ├── css/                 # Stylesheets
│   ├── assets/              # Logo and static assets
│   └── js/
│       ├── app.js           # Core app logic, WebSocket connection
│       ├── camera.js        # Camera source management
│       ├── overlay.js       # Bounding box and detection overlay renderer
│       ├── stats.js         # Live statistics tracking
│       ├── analytics.js     # Dashboard analytics charts
│       ├── roi.js           # ROI drawing and management
│       ├── reports.js       # Reports page — history, filters, charts
│       └── settings.js      # Settings panel logic
├── models/
│   ├── best_v1.pt           # YOLOv8 model (PyTorch)
│   └── best_v1.onnx         # YOLOv8 model (ONNX)
└── docs/                    # Additional documentation
```

---

## Prerequisites

- **Python 3.9+**
- **pip** (Python package manager)
- **Webcam** or an RTSP-capable IP camera (optional)
- A modern browser (Chrome, Edge, or Firefox recommended)

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <repository-url>
cd aquavision
```

### 2. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `fastapi` + `uvicorn` — Web server and API framework
- `ultralytics` — YOLOv8 inference engine
- `opencv-python` — Image processing and camera capture
- `numpy` — Numerical operations
- `reportlab` — PDF report generation
- `openpyxl` — Excel report generation
- `websockets` + `python-multipart` — WebSocket and file upload support
- `onnxruntime` — ONNX model inference (fallback)

### 3. Verify the model file

Ensure at least one model file exists in the `models/` directory:

```
models/best_v1.pt     ← preferred (PyTorch)
models/best_v1.onnx   ← fallback  (ONNX)
```

> **Note:** If no model file is found, the system starts in **demo mode** — the backend runs but returns no detections. See `docs/setup.md` for training instructions.

### 4. Start the backend server

```bash
cd backend
python main.py
```

Or with Uvicorn directly:

```bash
cd backend
uvicorn main:app --host localhost --port 8000
```

You should see:

```
[Inference] Loading YOLO model: ..\models\best_v1.pt
[Inference] Model loaded successfully.
INFO:     Uvicorn running on http://localhost:8000
```

### 5. Open the frontend

Open your browser and navigate to:

```
http://localhost:8000
```

The FastAPI backend serves the frontend as static files — no separate web server required.

---

## Usage

### Live Inspection

1. Go to **ROI & Camera Add** in the sidebar
2. Select a camera source (Webcam, Mobile, RTSP, or Video)
3. Optionally draw ROI regions to limit the inspection area
4. Navigate to **Live Camera** and click **START SYSTEM**
5. Detected bottles appear with bounding boxes showing pass/fail status

### Reports

- Navigate to **Reports** to view detection history
- Use filters (date range, status, defect type, camera) to narrow results
- Export data as **CSV**, **PDF**, or **Excel**

### Settings

- **Save Detection History** — Toggle whether detections are stored in the database
- **Clear History** — Permanently wipe all detection records, reports, analytics, and counters (prompts for confirmation)
- **Camera/Recording** — Configure default source, resolution, auto-record, and video format
- **Overlay** — Toggle bounding boxes, labels, confidence scores, and overlay opacity
- **Reset All Settings** — Restore all settings to defaults

---

## API Endpoints

| Method | Endpoint                       | Description                              |
|--------|--------------------------------|------------------------------------------|
| GET    | `/health`                      | Health check                             |
| WS     | `/ws`                          | WebSocket — webcam/mobile frame stream   |
| WS     | `/ws-rtsp`                     | WebSocket — RTSP stream (server-side)    |
| POST   | `/open-rtsp`                   | Open an RTSP stream                      |
| POST   | `/close-rtsp`                  | Close the RTSP stream                    |
| POST   | `/reset`                       | Reset live session counters              |
| GET    | `/rois`                        | Get configured ROIs                      |
| POST   | `/set-roi`                     | Save ROI configuration                   |
| GET    | `/settings`                    | Get current settings                     |
| POST   | `/settings`                    | Update settings                          |
| POST   | `/settings/reset`              | Reset settings to defaults               |
| GET    | `/reports/summary`             | Report summary (totals, accuracy)        |
| GET    | `/reports/history`             | Paginated detection history              |
| GET    | `/reports/camera-analytics`    | Per-camera analytics breakdown           |
| GET    | `/reports/analytics`           | Daily/weekly/monthly analytics data      |
| GET    | `/reports/camera-sources`      | List distinct camera sources             |
| POST   | `/reports/clear-history`       | **Clear all detection history & reports** |
| GET    | `/reports/export/csv`          | Export filtered history as CSV           |
| GET    | `/reports/export/pdf`          | Export summary report as PDF             |
| GET    | `/reports/export/excel`        | Export filtered history as Excel          |

---

## Detection Classes

The YOLOv8 model detects 7 classes:

| Class ID | Name            | Category |
|----------|-----------------|----------|
| 0        | `bottle`        | Object   |
| 1        | `proper_fill`   | Fill ✅   |
| 2        | `under_fill`    | Fill ❌   |
| 3        | `over_fill`     | Fill ❌   |
| 4        | `label_proper`  | Label ✅  |
| 5        | `label_torn`    | Label ❌  |
| 6        | `label_missing` | Label ❌  |

A bottle **passes** inspection only when both fill = `proper_fill` **and** label = `label_proper`.

---

## Configuration

Key settings in `backend/config.py`:

| Setting           | Default   | Description                              |
|-------------------|-----------|------------------------------------------|
| `HOST`            | localhost | Server bind address                      |
| `PORT`            | 8000      | Server port                              |
| `CONF_THRESH`     | 0.25      | Minimum detection confidence             |
| `IOU_THRESH`      | 0.5       | NMS IoU threshold                        |
| `MAX_FPS`         | 30        | Maximum frame processing rate            |
| `TRACKER_MAX_AGE` | 10        | Frames to keep a lost track alive        |

---

## Troubleshooting

| Issue                            | Solution                                                                                              |
|----------------------------------|-------------------------------------------------------------------------------------------------------|
| `[Errno 10048]` port in use     | Kill the existing process: `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F`              |
| Black screen on webcam           | Ensure browser has camera permission; use `https://` or `localhost` (secure context required)         |
| No detections showing            | Verify model file exists in `models/`; check console for `Model loaded successfully`                  |
| RTSP stream not connecting       | Confirm URL format: `rtsp://user:pass@ip:port/path`; ensure OpenCV has FFmpeg support                |
| Reports page shows stale data    | Use **Settings → Clear History** to fully reset, or refresh the Reports page                          |

---

## License

Internal project — SeeWise AI.
