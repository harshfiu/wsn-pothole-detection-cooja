#!/usr/bin/env python3
"""Scores the trained detector on the held-out test images."""
import json
import os
import shutil

from ultralytics import YOLO

WORK = r"C:\Users\harsh\wsn-ml"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def main():
    os.makedirs(OUT, exist_ok=True)
    best = os.path.join(WORK, "runs", "pothole", "weights", "best.pt")
    shutil.copy(best, os.path.join(OUT, "pothole_yolov8s.pt"))
    m = YOLO(best).val(data=os.path.join(WORK, "pothole.yaml"), split="test", device=0, workers=0,
                       imgsz=640, batch=8, project=os.path.join(WORK, "runs"), name="test", exist_ok=True)
    img = os.path.join(WORK, "data", "manot_yolo", "images")
    counts = {s: len(os.listdir(os.path.join(img, s))) for s in ("train", "val", "test")}
    result = {"precision": float(m.box.mp), "recall": float(m.box.mr), "mAP50": float(m.box.map50),
              "mAP50_95": float(m.box.map), "model": "YOLOv8s", "images": counts}
    with open(os.path.join(OUT, "test_metrics.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    print(result)


if __name__ == "__main__":
    main()
