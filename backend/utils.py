import cv2
import numpy as np
from config import CLASS_NAMES, FILL_CLASSES, LABEL_CLASSES, PASS_CLASSES, BOTTLE_CLASS


def xywh2xyxy(x):
    """Convert [cx, cy, w, h] → [x1, y1, x2, y2]."""
    y = np.copy(x)
    y[..., 0] = x[..., 0] - x[..., 2] / 2
    y[..., 1] = x[..., 1] - x[..., 3] / 2
    y[..., 2] = x[..., 0] + x[..., 2] / 2
    y[..., 3] = x[..., 1] + x[..., 3] / 2
    return y


def nms(boxes, scores, iou_thresh):
    """Pure-numpy Non-Maximum Suppression."""
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep  = []
    while order.size:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w   = np.maximum(0, xx2 - xx1)
        h   = np.maximum(0, yy2 - yy1)
        iou = (w * h) / (areas[i] + areas[order[1:]] - w * h + 1e-6)
        order = order[np.where(iou <= iou_thresh)[0] + 1]
    return keep


def letterbox(img, new_shape=640, color=(114, 114, 114)):
    """Resize image with unchanged aspect ratio using padding."""
    h, w = img.shape[:2]
    r = new_shape / max(h, w)
    new_w, new_h = int(round(w * r)), int(round(h * r))
    img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    dw = (new_shape - new_w) / 2
    dh = (new_shape - new_h) / 2
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    img = cv2.copyMakeBorder(img, top, bottom, left, right,
                             cv2.BORDER_CONSTANT, value=color)
    return img, r, (dw, dh)


def scale_boxes(boxes, r, pad, orig_shape):
    """Scale boxes from letterbox space back to original image space."""
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad[0]) / r
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad[1]) / r
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, orig_shape[1])
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, orig_shape[0])
    return boxes


def parse_bottle(class_id, conf, box):
    """
    Build a bottle result dict from a single detection.
    Returns None if class_id is unrecognised.
    """
    name = CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else "unknown"
    is_fill  = class_id in FILL_CLASSES
    is_label = class_id in LABEL_CLASSES

    return {
        "class_id":    int(class_id),
        "class_name":  name,
        "is_fill":     is_fill,
        "is_label":    is_label,
        "conf":        round(float(conf), 3),
        "box":         [round(float(v), 1) for v in box],   # x1,y1,x2,y2
        "pass":        class_id in PASS_CLASSES,
    }


def merge_bottle_detections(detections):
    """
    Group detections into per-bottle results.

    Strategy:
      1. If class-0 "bottle" anchors exist, use them as primary boxes and
         pair each with the best-overlapping fill & label sub-detections.
      2. Otherwise fall back to pairing fills with labels directly.
      3. Any detection that doesn't pair still appears as a standalone bottle.
    """
    bottle_anchors = [d for d in detections if d["class_id"] == BOTTLE_CLASS]
    fills   = [d for d in detections if d["is_fill"]]
    labels  = [d for d in detections if d["is_label"]]

    bottles = []

    # ── Path A: class-0 anchors present ────────────────────────────────
    if bottle_anchors:
        used_fills, used_labels = set(), set()

        for i, anchor in enumerate(bottle_anchors):
            ab = np.array(anchor["box"])

            # Best overlapping fill
            best_f_iou, best_f = 0, None
            for fi, f in enumerate(fills):
                if fi in used_fills:
                    continue
                iou = box_ioa(ab, np.array(f["box"]))
                if iou > best_f_iou:
                    best_f_iou, best_f = iou, fi
            fill_det = fills[best_f] if best_f is not None and best_f_iou > 0.3 else None
            if best_f is not None and best_f_iou > 0.3:
                used_fills.add(best_f)

            # Best overlapping label
            best_l_iou, best_l = 0, None
            for li, l in enumerate(labels):
                if li in used_labels:
                    continue
                iou = box_ioa(ab, np.array(l["box"]))
                if iou > best_l_iou:
                    best_l_iou, best_l = iou, li
            label_det = labels[best_l] if best_l is not None and best_l_iou > 0.3 else None
            if best_l is not None and best_l_iou > 0.3:
                used_labels.add(best_l)

            fill_name  = fill_det["class_name"]  if fill_det  else "unknown"
            label_name = label_det["class_name"] if label_det else "unknown"
            fill_conf  = fill_det["conf"]        if fill_det  else 0.0
            label_conf = label_det["conf"]       if label_det else 0.0

            fill_pass  = fill_det["pass"]  if fill_det  else False
            label_pass = label_det["pass"] if label_det else False
            passed = fill_pass and label_pass

            confs = [c for c in [anchor["conf"], fill_conf, label_conf] if c > 0]
            avg_conf = round(sum(confs) / max(len(confs), 1), 3)

            bottles.append({
                "id":           i + 1,
                "fill":         fill_name,
                "fill_conf":    fill_conf,
                "label":        label_name,
                "label_conf":   label_conf,
                "box":          anchor["box"],
                "label_box":    label_det["box"] if label_det else None,
                "pass":         passed,
                "overall_conf": avg_conf,
            })

    # ── Path B: no anchors — pair fills with labels directly ───────────
    else:
        used_labels_set = set()
        for i, f in enumerate(fills):
            fb = np.array(f["box"])
            best_iou, best_l = 0, None

            for j, l in enumerate(labels):
                if j in used_labels_set:
                    continue
                iou = box_iou(fb, np.array(l["box"]))
                if iou > best_iou:
                    best_iou, best_l = iou, j

            label_det = labels[best_l] if best_l is not None and best_iou > 0.1 else None
            if best_l is not None:
                used_labels_set.add(best_l)

            passed = f["pass"] and (label_det["pass"] if label_det else False)
            bottles.append({
                "id":           i + 1,
                "fill":         f["class_name"],
                "fill_conf":    f["conf"],
                "label":        label_det["class_name"] if label_det else "unknown",
                "label_conf":   label_det["conf"]       if label_det else 0.0,
                "box":          f["box"],
                "label_box":    label_det["box"] if label_det else None,
                "pass":         passed,
                "overall_conf": round((f["conf"] + (label_det["conf"] if label_det else 0)) / 2, 3),
            })

        # ── Orphan labels with no fill match → still show them ─────────
        for j, l in enumerate(labels):
            if j not in used_labels_set and not fills:
                bottles.append({
                    "id":           len(bottles) + 1,
                    "fill":         "unknown",
                    "fill_conf":    0.0,
                    "label":        l["class_name"],
                    "label_conf":   l["conf"],
                    "box":          l["box"],
                    "label_box":    l["box"],
                    "pass":         False,
                    "overall_conf": l["conf"],
                })

    return bottles


def box_ioa(b1, b2):
    """Intersection over Area of b2 (the sub-box)."""
    xi1 = max(b1[0], b2[0]); yi1 = max(b1[1], b2[1])
    xi2 = min(b1[2], b2[2]); yi2 = min(b1[3], b2[3])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    area2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
    return inter / (area2 + 1e-6)

def box_iou(b1, b2):
    """IoU between two boxes [x1,y1,x2,y2]."""
    xi1 = max(b1[0], b2[0]); yi1 = max(b1[1], b2[1])
    xi2 = min(b1[2], b2[2]); yi2 = min(b1[3], b2[3])
    inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    union = ((b1[2]-b1[0])*(b1[3]-b1[1]) +
             (b2[2]-b2[0])*(b2[3]-b2[1]) - inter)
    return inter / (union + 1e-6)