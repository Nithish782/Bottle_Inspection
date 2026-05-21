"""
Sanity-check annotations before training.
Checks: missing labels, empty labels, out-of-range coords, class distribution.
Run: python verify_annotations.py
"""
import os, glob
from collections import Counter

CLASS_NAMES = ["fill_proper","fill_under","fill_over",
               "label_proper","label_torn","label_missing"]

SPLITS = {
    "train": ("../dataset/annotated/images/train",
              "../dataset/annotated/labels/train"),
    "val":   ("../dataset/annotated/images/val",
              "../dataset/annotated/labels/val"),
    "test":  ("../dataset/annotated/images/test",
              "../dataset/annotated/labels/test"),
}

def verify():
    total_errors = 0

    for split, (img_dir, lbl_dir) in SPLITS.items():
        images = glob.glob(os.path.join(img_dir, "*.jpg")) + \
                 glob.glob(os.path.join(img_dir, "*.png"))
        print(f"\n[{split.upper()}] {len(images)} images")

        class_counts = Counter()
        errors       = []

        for img_path in images:
            stem     = os.path.splitext(os.path.basename(img_path))[0]
            lbl_path = os.path.join(lbl_dir, stem + ".txt")

            if not os.path.exists(lbl_path):
                errors.append(f"  MISSING label: {stem}")
                continue

            with open(lbl_path) as f:
                lines = f.readlines()

            if not lines:
                errors.append(f"  EMPTY label: {stem}")
                continue

            for i, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) != 5:
                    errors.append(f"  BAD FORMAT {stem} line {i+1}: {line.strip()}")
                    continue
                cls_id = int(parts[0])
                coords = [float(x) for x in parts[1:]]

                if cls_id >= len(CLASS_NAMES):
                    errors.append(f"  INVALID class {cls_id} in {stem}")
                if not all(0.0 <= c <= 1.0 for c in coords):
                    errors.append(f"  OUT-OF-RANGE coords in {stem} line {i+1}")

                class_counts[cls_id] += 1

        print(f"  Errors found: {len(errors)}")
        for e in errors[:10]:
            print(e)
        if len(errors) > 10:
            print(f"  ... and {len(errors)-10} more")

        print("  Class distribution:")
        for cid, cnt in sorted(class_counts.items()):
            name = CLASS_NAMES[cid] if cid < len(CLASS_NAMES) else f"id={cid}"
            bar  = "#" * (cnt // 5)
            print(f"    {name:<20} {cnt:>4}  {bar}")

        total_errors += len(errors)

    print(f"\n[Verify] Total errors: {total_errors}")
    if total_errors == 0:
        print("[Verify] Dataset looks good. Ready to train!")

if __name__ == "__main__":
    verify()