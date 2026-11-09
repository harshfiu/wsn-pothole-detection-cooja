#!/usr/bin/env python3
"""Trains YOLOv8 on a public pothole image set and evaluates it on held-out images.

Dataset: manot/pothole-segmentation on Hugging Face (Roboflow export, CC BY 4.0).
582 train / 157 validation / 80 test images, COCO annotations converted to YOLO boxes.
"""
import glob
import json
import os
import shutil
import zipfile

from huggingface_hub import snapshot_download
from ultralytics import YOLO

WORK = r"C:\Users\harsh\wsn-ml"
RAW = os.path.join(WORK, "data", "manot_raw")
DATA = os.path.join(WORK, "data", "manot_yolo")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def prepare():
    snapshot_download("manot/pothole-segmentation", repo_type="dataset", local_dir=RAW,
                      allow_patterns=["data/train.zip", "data/valid.zip", "data/test.zip"])
    counts = {}
    for split, target in [("train", "train"), ("valid", "val"), ("test", "test")]:
        src = os.path.join(RAW, "extracted", split)
        with zipfile.ZipFile(os.path.join(RAW, "data", f"{split}.zip")) as zf:
            zf.extractall(src)
        ann_path = glob.glob(os.path.join(src, "**", "*.json"), recursive=True)[0]
        coco = json.load(open(ann_path, encoding="utf-8"))
        boxes = {}
        for a in coco["annotations"]:
            boxes.setdefault(a["image_id"], []).append(a["bbox"])
        os.makedirs(os.path.join(DATA, "images", target), exist_ok=True)
        os.makedirs(os.path.join(DATA, "labels", target), exist_ok=True)
        n = 0
        root = os.path.dirname(ann_path)
        for im in coco["images"]:
            path = os.path.join(root, im["file_name"])
            if not os.path.exists(path):
                continue
            shutil.copy(path, os.path.join(DATA, "images", target, im["file_name"]))
            stem = os.path.splitext(im["file_name"])[0]
            with open(os.path.join(DATA, "labels", target, stem + ".txt"), "w") as fh:
                for x, y, w, h in boxes.get(im["id"], []):
                    fh.write(f"0 {(x + w / 2) / im['width']:.6f} {(y + h / 2) / im['height']:.6f} "
                             f"{w / im['width']:.6f} {h / im['height']:.6f}\n")
            n += 1
        counts[target] = n
    print("images:", counts)
    return counts


def main():
    os.makedirs(OUT, exist_ok=True)
    counts = prepare()
    yaml_path = os.path.join(WORK, "pothole.yaml")
    with open(yaml_path, "w") as fh:
        fh.write(f"path: {DATA}\ntrain: images/train\nval: images/val\ntest: images/test\n"
                 "nc: 1\nnames: ['pothole']\n")

    model = YOLO("yolov8s.pt")
    model.train(data=yaml_path, epochs=120, imgsz=640, batch=16, device=0, workers=0, seed=42,
                patience=30, project=os.path.join(WORK, "runs"), name="pothole", exist_ok=True,
                verbose=False, plots=True)

    best = os.path.join(WORK, "runs", "pothole", "weights", "best.pt")
    shutil.copy(best, os.path.join(OUT, "pothole_yolov8s.pt"))
    metrics = YOLO(best).val(data=yaml_path, split="test", device=0, workers=0, imgsz=640,
                             project=os.path.join(WORK, "runs"), name="test", exist_ok=True)
    result = {"precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
              "mAP50": float(metrics.box.map50), "mAP50_95": float(metrics.box.map),
              "model": "YOLOv8s", "images": counts}
    with open(os.path.join(OUT, "test_metrics.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    print(result)


if __name__ == "__main__":
    main()
