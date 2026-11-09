#!/usr/bin/env python3
"""Monitoring-server pipeline: WSN events + YOLOv8 image results -> maintenance priority.

1. Reads what the sink received in a Cooja run (deduplicated reports).
2. Clusters pothole events by position along the road.
3. Runs YOLOv8 on one held-out image per cluster, standing in for the geotagged
   dashcam image that would arrive over 4G/Wi-Fi (not over the WSN).
4. Scores each site and ranks it.

Assumed inputs, because no real road data exists here:
- which image belongs to which site (a demonstration pairing);
- traffic and road class per road segment (the SEGMENTS table).
"""
import glob
import json
import os
from collections import Counter

import cv2
import pandas as pd
from ultralytics import YOLO

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
LOG = os.path.join(HERE, "..", "results", "raw", "v8_f0_s1.log")
TEST_IMAGES = r"C:\Users\harsh\wsn-ml\data\manot_yolo\images\test"
BASE_LON_E6 = 80044400
MICRODEG_PER_M = 9.2
CLUSTER_GAP_M = 8

# name, last metre of the segment, traffic 0-1, road importance 0-1 (assumed)
SEGMENTS = [("School zone", 40, 0.7, 1.0), ("Market road", 90, 1.0, 0.7), ("Residential", 140, 0.4, 0.4)]
WEIGHTS = {"vibration": 0.30, "size": 0.25, "confidence": 0.10, "traffic": 0.20, "road": 0.15}


def load_events():
    seen = {}
    for line in open(LOG, encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[2].startswith("RX,"):
            f = p[2].split(",")
            key = (int(f[3]), int(f[4]))
            if key not in seen:
                seen[key] = dict(vehicle=key[0], peak_mg=int(f[5]), severity=int(f[6]),
                                 x_m=(int(f[8]) - BASE_LON_E6) / MICRODEG_PER_M)
    return pd.DataFrame(seen.values()), len(seen)


def clusters(ev):
    ev = ev[ev.severity > 0].sort_values("x_m").reset_index(drop=True)
    group, last, out = 0, None, []
    for x in ev.x_m:
        if last is not None and x - last > CLUSTER_GAP_M:
            group += 1
        out.append(group)
        last = x
    ev["site"] = out
    return ev


def segment(x):
    return next(s for s in SEGMENTS if x <= s[1] or s is SEGMENTS[-1])


def main():
    ev, total = load_events()
    ev = clusters(ev)
    model = YOLO(os.path.join(OUT, "pothole_yolov8s.pt"))
    images = sorted(glob.glob(os.path.join(TEST_IMAGES, "*.jpg")))
    picks = []
    for path in images:  # the first test images with a confident detection, in file order
        r = model.predict(path, conf=0.4, device=0, verbose=False)[0]
        if len(r.boxes):
            picks.append((path, r))
        if len(picks) == ev.site.nunique():
            break

    rows = []
    for (site, g), (path, r) in zip(ev.groupby("site"), picks):
        x = g.x_m.median()
        sev = Counter(g.severity).most_common(1)[0][0]
        best = int(r.boxes.conf.argmax())
        area = float(r.boxes.xywhn[best][2] * r.boxes.xywhn[best][3]) * 100
        conf = float(r.boxes.conf[best])
        size = "Large" if area >= 6 else "Medium" if area >= 2 else "Small"
        name, _, traffic, road = segment(x)
        vib = min(g.peak_mg.median() / 2000.0, 1.0)
        sz = {"Small": 0.33, "Medium": 0.66, "Large": 1.0}[size]
        score = 100 * (WEIGHTS["vibration"] * vib + WEIGHTS["size"] * sz + WEIGHTS["confidence"] * conf
                       + WEIGHTS["traffic"] * traffic + WEIGHTS["road"] * road)
        rows.append({"site": site + 1, "position_m": round(x, 1), "segment": name, "reports": len(g),
                     "vehicles": g.vehicle.nunique(), "median_peak_mg": int(g.peak_mg.median()),
                     "wsn_severity": ["", "Low", "Medium", "High"][sev], "yolo_confidence": round(conf, 2),
                     "box_area_pct": round(area, 1), "yolo_size": size, "priority_score": round(score, 1),
                     "image": os.path.basename(path)})
        cv2.imwrite(os.path.join(OUT, f"site{site + 1}_detection.jpg"), r.plot())

    df = pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", df.index + 1)
    df.to_csv(os.path.join(OUT, "priority_ranking.csv"), index=False)
    print("unique reports:", total, "pothole reports:", len(ev))
    print(df.drop(columns="image").to_string(index=False))


if __name__ == "__main__":
    main()
