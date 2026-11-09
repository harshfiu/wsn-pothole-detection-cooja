#!/usr/bin/env python3
"""Applies the project changes to a new copy of the deck, through PowerPoint itself."""
import json
import os
import sys

import pandas as pd
import win32com.client

BASE = r"C:\Users\harsh\OneDrive\Desktop\WSN Project"
NAME = "WSN-Based-Intelligent-Road-Pothole-Detection-and-Priority-Monitoring-System-Using-Machine-Learning"
SRC = os.path.join(BASE, NAME + ".pptx")
DST = os.path.join(BASE, NAME + "-Updated.pptx")
PROJ = os.path.join(BASE, "Contiki Cooja", "pothole-wsn")
RES = os.path.join(PROJ, "results")
FIG = os.path.join(RES, "figures")

s = pd.read_csv(os.path.join(RES, "summary.csv"))
nf8 = s[(s.vehicles == 8) & (~s.failure)].iloc[0]
f8 = s[(s.vehicles == 8) & (s.failure)].iloc[0]
pdr2 = s[(s.vehicles == 2) & (~s.failure)].iloc[0].pdr
rec = s[s.failure].recovery_s
ml = json.load(open(os.path.join(PROJ, "ml", "output", "test_metrics.json")))
rec_txt = f"{rec.min():.0f}\u2013{rec.max():.0f} s"
worst_loss = max(s[~s.failure].pdr.values - s[s.failure].pdr.values)

app = win32com.client.Dispatch("PowerPoint.Application")
p = app.Presentations.Open(SRC, True, False, False)  # read-only, no window


def find(sl, prefix):
    for sh in sl.Shapes:
        if sh.HasTextFrame and sh.TextFrame.HasText and sh.TextFrame.TextRange.Text.startswith(prefix):
            return sh
    raise KeyError(prefix)


def para_with(sh, prefix):
    tr = sh.TextFrame.TextRange
    for i in range(1, tr.Paragraphs().Count + 1):
        if tr.Paragraphs(i).Text.startswith(prefix):
            return tr.Paragraphs(i)
    raise KeyError(prefix)


def set_run(run, text):
    run.Text = text + ("\r" if run.Text.endswith("\r") else "")


def plain(sl, prefix, text):
    tr = find(sl, prefix).TextFrame.TextRange
    set_run(tr.Runs(1), text)
    while tr.Runs().Count > 1:
        tr.Runs(2).Delete()


def body(sl, prefix, text, para=None):
    """Keeps the bold label (first run) and replaces what follows it."""
    sh = find(sl, prefix) if para is None else sl
    pr = sh.TextFrame.TextRange.Paragraphs(1) if para is None else para_with(sh, para)
    set_run(pr.Runs(2), text)


def picture(sl, path, *box):
    old = next(x for x in sl.Shapes if x.Type == 13)
    l, t, w, h = box if box else (old.Left, old.Top, old.Width, old.Height)
    old.Delete()
    new = sl.Shapes.AddPicture(path, False, True, l, t, w, h)
    new.AlternativeText = os.path.basename(path)


def cells(tbl, rows):
    for r, row in enumerate(rows, 1):
        for c, txt in enumerate(row, 1):
            if txt is not None:
                tbl.Cell(r, c).Shape.TextFrame.TextRange.Text = txt


S = p.Slides
# Slide 2
sl = S(2)
para = para_with(find(sl, "Problem:"), "Proposed solution")
set_run(para.Runs(2), " A WSN-based monitoring architecture: vehicle sensor nodes report road events wirelessly "
        "to a central system; dashcam images reach the server separately over 4G/Wi-Fi, where machine learning "
        "detects potholes and prioritizes maintenance.")
obj = para_with(find(sl, "Enable distributed"), "Detect and classify")
set_run(obj.Runs(1), "Detect potholes in dashcam images using YOLOv8.")
plain(sl, "YOLOv8 Detection", "YOLOv8 on Dashcam Images")

# Slide 3
sl = S(3)
sh = find(sl, "Vehicle Sensor Nodes:")
set_run(para_with(sh, "Gateway").Runs(2), " six static roadside units, in redundant pairs, aggregate reports "
        "and relay them wirelessly over multi-hop RPL.")
set_run(para_with(sh, "Monitoring").Runs(2), " combines WSN events with dashcam images for YOLOv8 detection.")
body(sl, "Justification:", " paired gateways give every node an alternate parent; vehicles stay one hop from the "
     "tree, so their movement never breaks a route.")
picture(sl, os.path.join(FIG, "topology_rpl.png"))

# Slide 4
sl = S(4)
plain(sl, "Routing Strategy:", "Routing Strategy: RPL Suits a Static Roadside Tree")
body(sl, "Selected protocol:", " RPL (IPv6 Routing Protocol for Low-Power and Lossy Networks), a proactive "
     "protocol that builds a tree rooted at the sink. Static gateways form the tree; moving vehicles stay out of it.")
tbl = next(x for x in sl.Shapes if x.HasTable).Table
cells(tbl, [
    (None, "RPL (Selected)", "AODV (Alternative)"),
    (None, "Proactive, DODAG-based", "Reactive, on-demand"),
    (None, "Maintains routing structure", "When required"),
    (None, "Weak for mobile routers; vehicles kept out of the tree", "Can rediscover broken routes"),
    (None, "Designed for constrained devices", "Avoids periodic route maintenance when idle"),
    (None, "Supports large LLN topologies", "Depends on network size and discovery overhead"),
    (None, "Static roadside gateway backbone", "Not in Contiki 3.0\u2019s IPv6 stack"),
])
body(sl, "Justification:", f" the gateway tree is static, RPL is native to Contiki, and it recovered in {rec_txt} "
     "in Cooja. AODV was not simulated, so no measured superiority is claimed.")
plain(sl, "AODV PROTOCOL CYCLE", "RPL PROTOCOL CYCLE")
for old, label, text in [
    ("Route Discovery:", "DODAG Formation:", " the sink broadcasts DIO messages advertising its rank."),
    ("Route Reply:", "Parent Selection:", " each gateway picks the neighbour with the lowest cost to the sink."),
    ("Data Transmission:", "Data Forwarding:", " packets travel upward through preferred parents."),
    ("Route Maintenance:", "Local Repair:", " when a parent fails, the node switches to its next-best parent."),
]:
    tr = find(sl, old).TextFrame.TextRange
    set_run(tr.Runs(1), label)
    set_run(tr.Runs(2), text)
picture(sl, os.path.join(FIG, "rpl_cycle.png"))

# Slide 5
sl = S(5)
plain(sl, "Performance Analysis:", "Performance Analysis: Measured in Cooja")
plain(sl, "SIMULATION FRAMEWORK", "COOJA RESULTS: PDR VS VEHICLE NODES")
plain(sl, "The evaluation aims", f"40 Cooja runs. PDR falls from {pdr2:.1f}% (2 vehicles) to {nf8.pdr:.1f}% (8) as "
      f"vehicle broadcasts compete; mean delay stays under 1.4 s.")
picture(sl, os.path.join(FIG, "slide5_pdr.png"))

# Slide 6
sl = S(6)
tbl = next(x for x in sl.Shapes if x.HasTable).Table
cells(tbl, [(None, None, "Tested"), (None, None, "Redundant sensing through multiple vehicles"),
            (None, None, "Link-layer retransmission and alternate parents"),
            (None, None, "RPL parent switching"),
            (None, None, "Paired gateways, alternate parents (tested)")])
tbl.Cell(1, 3).Shape.TextFrame.TextRange.Text = "Solution"
plain(sl, "AODV ROUTE RECOVERY", "RPL ROUTE RECOVERY TOPOLOGY")
tr = find(sl, "Active wireless link").TextFrame.TextRange
set_run(tr.Paragraphs(1).Runs(1), "Gateway removed mid-run \u00b7 Its children see link-layer transmissions fail.")
set_run(tr.Paragraphs(2).Runs(1), "Each child switches to its next-best parent \u00b7 Data resumes through the twin gateway.")
plain(sl, "Labelled recovery", f"Measured in Cooja: slowest child re-parents in {rec_txt} (mean).")
body(sl, "Suggested improvements", " data buffering during temporary disconnections and further gateway redundancy.")
picture(sl, os.path.join(FIG, "rpl_recovery.png"))

# Number the following slides before inserting the new one.
for i, new in [(8, "9"), (7, "8")]:
    for sh in S(i).Shapes:
        if sh.HasTextFrame and sh.TextFrame.HasText and sh.TextFrame.TextRange.Text.strip() == str(i) and sh.Top > 480:
            sh.TextFrame.TextRange.Text = new

# Slide 7 (new): with and without failure
sl = S(6).Duplicate().Item(1)
plain(sl, "RUBRIC CRITERION 4", "RUBRIC CRITERION 4 \u00b7 MEASURED IMPACT OF NODE FAILURE")
plain(sl, "Failure Analysis", "Performance With and Without Gateway Failure")
plain(sl, "NETWORK FAULT MATRIX", "8 VEHICLES, MEAN OF 5 RANDOM SEEDS")
find(sl, "Suggested improvements").Delete()
for x in list(sl.Shapes):
    if x.HasTextFrame and x.TextFrame.HasText and x.TextFrame.TextRange.Text.strip() == "6" and x.Top > 480:
        x.TextFrame.TextRange.Text = "7"
tshape = next(x for x in sl.Shapes if x.HasTable)
tbl = tshape.Table
while tbl.Rows.Count < 8:
    tbl.Rows.Add()
rows = [("Metric", "No failure", "Gateway failure"),
        ("PDR (%)", f"{nf8.pdr:.1f}", f"{f8.pdr:.1f}"),
        ("End-to-end delay (s)", f"{nf8.delay_s:.2f}", f"{f8.delay_s:.2f}"),
        ("Mean hop count", f"{nf8.hops:.2f}", f"{f8.hops:.2f}"),
        ("Throughput (bit/s)", f"{nf8.throughput_bps:.0f}", f"{f8.throughput_bps:.0f}"),
        ("Gateway power (mW)", f"{nf8.gateway_mw:.2f}", f"{f8.gateway_mw:.2f}"),
        ("Vehicle power (mW)", f"{nf8.vehicle_mw:.2f}", f"{f8.vehicle_mw:.2f}"),
        ("Route recovery (s)", "\u2013", f"{f8.recovery_s:.1f}")]
cells(tbl, rows)
for r in range(1, 9):
    tbl.Rows(r).Height = 37
plain(sl, "RPL ROUTE RECOVERY", "PDR OVER TIME")
find(sl, "PDR OVER TIME").Left = 620
picture(sl, os.path.join(RES, "charts", "pdr_timeline.png"), 620, 178, 292, 175)
tx = find(sl, "Gateway removed mid-run")
tx.Top, tx.Left, tx.Width = 360, 620, 292
tr = tx.TextFrame.TextRange
set_run(tr.Paragraphs(1).Runs(1), f"Across all vehicle counts, the failure cost at most {worst_loss:.1f} PDR points.")
tr.Paragraphs(2).Delete()
end = find(sl, "Measured in Cooja")
end.Delete()

# Slide 8 (was 7)
sl = S(8)
plain(sl, "Distributed sensing,", "Distributed sensing, wireless communication, resilient roadside routing, "
      "fault-tolerant data collection.")
plain(sl, "AODV Routing", "RPL Routing")
plain(sl, "Route discovery and", "Static gateway tree with parent switching.")
plain(sl, "Detects potholes;", f"Detects potholes in dashcam images (4G/Wi-Fi). Test mAP@50: {ml['mAP50']:.2f}.")

# Slide 9 (was 8)
sl = S(9)
sh = find(sl, "Distributed Monitoring:")
pr = para_with(sh, "Mobility-Aware")
set_run(pr.Runs(1), "Resilient Routing:")
set_run(pr.Runs(2), f" RPL rerouted around a failed gateway in {rec_txt}.")
set_run(para_with(sh, "Intelligent").Runs(2), f" YOLOv8 reached mAP@50 of {ml['mAP50']:.2f} on held-out images.")
set_run(para_with(sh, "Fault Tolerance").Runs(2), f" paired gateways limited PDR loss to {worst_loss:.1f} points or less.")
tbl = next(x for x in sl.Shapes if x.HasTable).Table
for r in range(1, tbl.Rows.Count + 1):
    t = tbl.Cell(r, 2).Shape.TextFrame.TextRange
    if t.Text.startswith("AODV routing"):
        t.Text = "RPL routing, compared against AODV."
    elif t.Text.startswith("PDR,"):
        t.Text = "PDR, delay, throughput, energy, network lifetime and hop count, measured in Cooja."
    elif t.Text.startswith("Route recovery"):
        t.Text = "RPL parent switching and redundant gateways, tested in Cooja."

if os.path.exists(DST):
    os.remove(DST)
p.SaveAs(DST)
out = sys.argv[1]
p.Export(out, "PNG", 1280, 720)
print("slides:", p.Slides.Count)
p.Close()
