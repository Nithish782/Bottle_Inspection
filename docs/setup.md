# Setup & Run Instructions

## Prerequisites
- Python 3.9+
- pip
- Webcam

---

## 1. Install dependencies

### Training (run once)
```bash
cd aquavision/training
pip install -r requirements.txt
```

### Backend
```bash
cd aquavision/backend
pip install -r requirements.txt
```

---

## 2. Collect data
```bash
cd aquavision/scripts
python collect_frames.py --class fill_proper  --count 200
python collect_frames.py --class fill_under   --count 200
python collect_frames.py --class fill_over    --count 200
python collect_frames.py --class label_proper --count 200
python collect_frames.py --class label_torn   --count 150
python collect_frames.py --class label_missing --count 150
```

---

## 3. Annotate
- Upload `dataset/raw/` images to [Roboflow](https://roboflow.com)
- Draw bounding boxes, assign class labels
- Export as **YOLOv8** format into `dataset/annotated/`

---

## 4. Verify dataset
```bash
cd aquavision/scripts
python verify_annotations.py
```

---

## 5. Train
```bash
cd aquavision/training
python train.py
```

---

## 6. Export to ONNX
```bash
python export.py
```

---

## 7. Start backend
```bash
cd aquavision/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 8. Open frontend
Open `aquavision/frontend/index.html` in your browser.
Select **Live Backend Mode** in the dropdown and click **Start Camera**.

---

## 9. Benchmark
```bash
cd aquavision/scripts
python benchmark.py
```