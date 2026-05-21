"""
Extra augmentation pass using Albumentations.
Doubles the training set size with hard augmentations.
Run: python augment.py
"""
import os, cv2, glob, shutil
import numpy as np
import albumentations as A

SRC_IMG = "../dataset/annotated/images/train"
SRC_LBL = "../dataset/annotated/labels/train"
OUT_IMG = "../dataset/augmented/images"
OUT_LBL = "../dataset/augmented/labels"

transform = A.Compose([
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.8),
    A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=30, val_shift_limit=20, p=0.5),
    A.GaussNoise(var_limit=(10, 50), p=0.4),
    A.MotionBlur(blur_limit=5, p=0.3),
    A.RandomShadow(p=0.3),
    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, p=0.2),
    A.ImageCompression(quality_lower=60, quality_upper=95, p=0.3),
    A.HorizontalFlip(p=0.5),
    A.ShiftScaleRotate(shift_limit=0.05, scale_limit=0.1, rotate_limit=5, p=0.5),
], bbox_params=A.BboxParams(format="yolo", label_fields=["class_labels"]))


def load_yolo_labels(label_path):
    boxes, cls = [], []
    if not os.path.exists(label_path):
        return boxes, cls
    with open(label_path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 5:
                cls.append(int(parts[0]))
                boxes.append([float(x) for x in parts[1:]])
    return boxes, cls


def save_yolo_labels(label_path, boxes, cls):
    with open(label_path, "w") as f:
        for c, b in zip(cls, boxes):
            f.write(f"{c} {' '.join(f'{v:.6f}' for v in b)}\n")


def augment():
    os.makedirs(OUT_IMG, exist_ok=True)
    os.makedirs(OUT_LBL, exist_ok=True)

    images = glob.glob(os.path.join(SRC_IMG, "*.jpg")) + \
             glob.glob(os.path.join(SRC_IMG, "*.png"))

    count = 0
    for img_path in images:
        stem      = os.path.splitext(os.path.basename(img_path))[0]
        lbl_path  = os.path.join(SRC_LBL, stem + ".txt")
        boxes, cls = load_yolo_labels(lbl_path)

        img = cv2.imread(img_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        try:
            aug = transform(image=img, bboxes=boxes, class_labels=cls)
        except Exception:
            continue

        out_img = cv2.cvtColor(aug["image"], cv2.COLOR_RGB2BGR)
        out_path = os.path.join(OUT_IMG, f"aug_{stem}.jpg")
        cv2.imwrite(out_path, out_img)

        out_lbl = os.path.join(OUT_LBL, f"aug_{stem}.txt")
        save_yolo_labels(out_lbl, aug["bboxes"], aug["class_labels"])
        count += 1

    print(f"[Augment] Generated {count} augmented images -> {OUT_IMG}")


if __name__ == "__main__":
    augment()