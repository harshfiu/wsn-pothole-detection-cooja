#!/usr/bin/env python3
"""Builds the final project report PDF from the measured results."""
import json
import os

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

PROJ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = os.path.join(PROJ, "results")
ML = os.path.join(PROJ, "ml", "output")
OUT = os.path.join(PROJ, "deliverables", "WSN_Pothole_Project_Report.pdf")

s = pd.read_csv(os.path.join(RES, "summary.csv"))
ml = json.load(open(os.path.join(ML, "test_metrics.json")))
rank = pd.read_csv(os.path.join(ML, "priority_ranking.csv"))
rec = s[s.failure].recovery_s
nf = s[~s.failure].set_index("vehicles")
wf = s[s.failure].set_index("vehicles")

NAVY = colors.HexColor("#1a1a8c")
base = getSampleStyleSheet()
BODY = ParagraphStyle("B", parent=base["Normal"], fontName="Times-Roman", fontSize=11, leading=15, spaceAfter=7, allowWidows=0, allowOrphans=0)
H1 = ParagraphStyle("H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=15, textColor=NAVY,
                    spaceBefore=10, spaceAfter=7, keepWithNext=1)
H2 = ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12, spaceBefore=7, spaceAfter=5, keepWithNext=1)
CAP = ParagraphStyle("C", parent=BODY, fontSize=9.5, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#52514e"))
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=9.5, leading=12, spaceAfter=0)
HEAD = ParagraphStyle("Head", parent=CELL, fontName="Times-Bold", textColor=colors.white)
TITLE = ParagraphStyle("T", parent=H1, fontSize=22, leading=28, alignment=TA_CENTER, spaceAfter=18)
CENTER = ParagraphStyle("Ce", parent=BODY, alignment=TA_CENTER, fontSize=12, leading=18)

story = []


def p(text):
    story.append(Paragraph(text, BODY))


def h1(text):
    story.append(CondPageBreak(6.5 * cm))
    story.append(Paragraph(text, H1))


def h2(text):
    story.append(CondPageBreak(6.5 * cm))
    story.append(Paragraph(text, H2))


def bullets(items):
    for it in items:
        story.append(Paragraph("&bull;&nbsp; " + it, ParagraphStyle("L", parent=BODY, leftIndent=14, firstLineIndent=-10,
                                                                    spaceAfter=4)))
    story.append(Spacer(1, 4))


def table(rows, widths):
    data = [[Paragraph(str(c), HEAD if i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9c9c9")),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return KeepTogether([t])


def fig(path, width_cm, caption):
    w, h = PILImage.open(path).size
    img = Image(path, width=width_cm * cm, height=width_cm * cm * h / w)
    story.append(KeepTogether([img, Spacer(1, 4), Paragraph(caption, CAP), Spacer(1, 8)]))


story += [Spacer(1, 3.5 * cm),
          Paragraph("WSN-Based Intelligent Road Pothole Detection and Priority Monitoring System Using Machine Learning", TITLE),
          Paragraph("Project Report: Wireless Sensor Networks", CENTER), Spacer(1, 1.2 * cm),
          Paragraph("Harsh Gupta (RA2311003010866)", CENTER), Paragraph("Debabrata Bhattacharya (RA2311003010892)", CENTER),
          Spacer(1, 1.2 * cm), Paragraph("Simulation platform: Contiki 3.0 and Cooja, Tmote Sky motes", CENTER), PageBreak()]

h1("1. Aim")
p("To design and evaluate a wireless sensor network that lets vehicles report road damage to a central server, "
  "survives the failure of a roadside node, and feeds a machine-learning stage that ranks potholes for repair.")
h2("Objectives")
bullets(["Collect vibration and position reports from vehicle-mounted nodes.",
         "Deliver the reports to a sink through a redundant, multi-hop roadside network.",
         "Measure packet delivery, delay, throughput, energy and hop count in Cooja.",
         "Remove a gateway during simulation and measure the routing change and its effect.",
         "Detect potholes in images with YOLOv8 and rank repair sites by priority."])

h1("2. System Design")
h2("2.1 Topology")
p("The network is a hierarchical tree. Vehicles broadcast one hop to any roadside gateway in range. Six static gateways, "
  "in pairs along the road, aggregate those reports and forward them to the sink through a multi-hop RPL tree.")
fig(os.path.join(RES, "figures", "topology_rpl.png"), 15, "Figure 1. Network topology.")
p("<b>Justification.</b> Pairing gateways gives each one an alternate parent, so one failure does not disconnect the "
  "nodes behind it. Keeping vehicles out of the tree means their movement never breaks a route: a vehicle simply "
  "reaches whichever gateway is nearby, and the sink removes duplicates using vehicle ID and sequence number.")
h2("2.2 Node roles")
table_roles = [["Node", "IDs", "Function"],
               ["Sink", "1", "RPL root; radio always on; logs every received report"],
               ["Roadside gateway", "2-7", "RPL router; removes duplicates; batches up to 3 reports or flushes after 2 s"],
               ["Vehicle", "8-15", "IPv6 host with RPL compiled out; samples at 10 Hz; one report per 5 s window"]]
story += [table(table_roles, [3.5, 1.5, 11]), Spacer(1, 8)]
h2("2.3 Routing protocol selection")
story += [table([["Feature", "RPL (selected)", "AODV (alternative)"],
                 ["Type", "Proactive, DODAG tree", "Reactive, on-demand"],
                 ["Fit to this design", "Static gateway backbone with traffic flowing to one sink", "Better suited to mobile routers"],
                 ["Control traffic", "Periodic DIO, slowed by Trickle when stable", "Flooded RREQ for each discovery"],
                 ["Failure handling", "Switch to next-best parent", "RERR, then new RREQ"],
                 ["Contiki 3.0 support", "Native in the IPv6 stack", "Not in the IPv6 stack"]], [4, 6, 6]), Spacer(1, 8)]
p("AODV was not simulated, so this report claims no measured advantage of RPL over AODV.")
h2("2.4 Why images do not travel over the WSN")
p("An IEEE 802.15.4 frame carries at most 127 bytes, which makes image transfer over this network impractical. "
  "The WSN therefore carries short event reports of 14 bytes. Dashcam images would reach the server separately over "
  "4G or Wi-Fi, where YOLOv8 processes them.")

h1("3. Simulation Setup")
story += [table([["Parameter", "Value"],
                 ["OS / simulator", "Contiki 3.0 / Cooja, msp430-gcc 4.6.3"],
                 ["Mote type", "Tmote Sky (emulated by MSPSim)"],
                 ["Radio medium", "UDGM: 50 m transmission, 100 m interference, TX success 100%, RX success 90%"],
                 ["MAC / RDC", "CSMA / ContikiMAC at 8 Hz, channel 26"],
                 ["Network / routing", "IPv6, 6LoWPAN, RPL (sink and gateways)"],
                 ["Nodes", "1 sink, 6 gateways, 2-8 vehicles"],
                 ["Gateway positions", "x = 35, 70, 105 m; y = +12 and -12 m; sink at origin"],
                 ["Vehicle movement", "140 m road, 8 m/s, back and forth, moved by simulation script"],
                 ["Report interval", "5 s, starting 60 s after boot"],
                 ["Run length / repeats", "600 s; 5 random seeds per configuration; 40 runs"],
                 ["Failure", "At 300 s, the first-tier gateway that gateway 4 is using as its parent is removed"]], [5, 11]),
          Spacer(1, 8)]
p("<b>Simulated inputs.</b> Cooja has no road surface or GPS. Each vehicle node generates low acceleration noise, plus a "
  "spike when its simulated position passes one of five potholes, and computes its position from the same path the script "
  "uses to move it. Detection on the node (10 Hz sampling, window peak, thresholds) is real code running on the emulated mote.")
fig(os.path.join(RES, "screenshots", "cooja_running_before_failure.png"), 16,
    "Figure 2. Cooja at 4:00 with all gateways: Network, Radio Messages, Mote Output and PowerTracker windows.")
fig(os.path.join(RES, "screenshots", "cooja_after_gateway_failure.png"), 16,
    "Figure 3. Cooja after the failure: gateway 2 is gone (14 motes) and traffic continues.")

h1("4. Results")
h2("4.1 Effect of vehicle count")
rows = [["Vehicles", "PDR (%)", "Delay (s)", "Hops", "Throughput (bit/s)", "Vehicle (mW)", "Gateway (mW)"]]
for v in [2, 4, 6, 8]:
    r = nf.loc[v]
    rows.append([v, f"{r.pdr:.1f} &plusmn; {r.pdr_std:.1f}", f"{r.delay_s:.2f}", f"{r.hops:.2f}", f"{r.throughput_bps:.0f}",
                 f"{r.vehicle_mw:.2f}", f"{r.gateway_mw:.2f}"])
story += [table(rows, [1.9, 2.9, 1.9, 1.6, 3, 2.4, 2.4]), Paragraph("Table 1. No-failure runs, mean of 5 seeds.", CAP), Spacer(1, 8)]
p(f"PDR falls from {nf.loc[2].pdr:.1f}% to {nf.loc[8].pdr:.1f}% as vehicles are added. Vehicle broadcasts have no "
  "link-layer acknowledgement or retransmission, so a report lost to a collision is gone unless another gateway heard it. "
  f"Delay is highest with 2 vehicles ({nf.loc[2].delay_s:.2f} s). That is consistent with the aggregation rule: with little "
  "traffic, gateways more often wait for the 2 s timer instead of filling a batch of 3.")
fig(os.path.join(RES, "charts", "pdr_vs_vehicles.png"), 12.5, "Figure 4. PDR against number of vehicles.")
fig(os.path.join(RES, "charts", "delay_vs_vehicles.png"), 12.5, "Figure 5. End-to-end delay against number of vehicles.")
h2("4.2 Node failure analysis")
rows = [["Vehicles", "PDR no failure", "PDR with failure", "Delay no failure (s)", "Delay with failure (s)", "Recovery (s)"]]
for v in [2, 4, 6, 8]:
    a, b = nf.loc[v], wf.loc[v]
    rows.append([v, f"{a.pdr:.1f}", f"{b.pdr:.1f}", f"{a.delay_s:.2f}", f"{b.delay_s:.2f}", f"{b.recovery_s:.1f}"])
story += [table(rows, [1.9, 2.8, 2.8, 3, 3, 2.5]), Paragraph("Table 2. Performance with and without gateway failure, mean of 5 seeds.", CAP), Spacer(1, 8)]
p(f"In all 20 failure runs the children of the removed gateway selected a new parent. The slowest child took {rec.min():.1f}-{rec.max():.1f} s "
  f"on average, depending on vehicle count. The largest mean PDR loss was {max(nf.pdr.values - wf.pdr.values):.1f} points, "
  "which is smaller than the variation between random seeds, so these runs do not show a statistically clear loss.")
p("<b>Recovery mechanism.</b> When a gateway disappears, its children's unicast frames stop being acknowledged. RPL raises the "
  "estimated cost (ETX) of that link and selects the next-best parent. The twin gateway serves as that alternate path, and "
  "gateways with overlapping coverage continue to hear vehicles in the affected zone.")
fig(os.path.join(RES, "charts", "pdr_timeline.png"), 12.5,
    "Figure 6. PDR over time. The dip in the bin ending at 300 s includes reports still waiting in the removed gateway.")
h2("4.3 Energy and estimated lifetime")
p("Energy comes from Contiki's Energest time counters and Tmote Sky currents at 3 V: CPU 1.8 mA, low-power mode 0.0545 mA, "
  "transmit 17.7 mA, receive 20 mA. Cooja does not drain batteries, so lifetime is an estimate assuming 2 x AA cells of 2500 mAh.")
rows = [["Vehicles", "Vehicle lifetime (days)", "Gateway lifetime (days)"]]
for v in [2, 4, 6, 8]:
    rows.append([v, f"{nf.loc[v].vehicle_life_days:.0f}", f"{nf.loc[v].gateway_life_days:.0f}"])
story += [table(rows, [3, 5, 5]), Paragraph("Table 3. Estimated battery lifetime, no-failure runs.", CAP), Spacer(1, 8)]
fig(os.path.join(RES, "charts", "power_by_role.png"), 12.5, "Figure 7. Average power per node. The sink is assumed mains powered.")

h1("5. Machine Learning Module")
c = ml["images"]
p(f"A YOLOv8s detector was trained for 120 epochs on a public pothole dataset (Roboflow export, CC BY 4.0, via Hugging Face "
  f"manot/pothole-segmentation), with {c['train']} training, {c['val']} validation and {c['test']} held-out test images.")
story += [table([["Metric (test set)", "Value"], ["Precision", f"{ml['precision']:.3f}"], ["Recall", f"{ml['recall']:.3f}"],
                 ["mAP@50", f"{ml['mAP50']:.3f}"], ["mAP@50-95", f"{ml['mAP50_95']:.3f}"]], [6, 3]), Spacer(1, 8)]
h2("Priority ranking")
p("The server clusters pothole reports received in a Cooja run by road position and scores each site: vibration 30%, "
  "image-estimated size 25%, detector confidence 10%, traffic 20%, road importance 15%.")
rows = [["Rank", "Position (m)", "Segment", "Reports", "WSN severity", "YOLO size", "Score"]]
for _, r in rank.iterrows():
    rows.append([r["rank"], r.position_m, r.segment, r.reports, r.wsn_severity, r.yolo_size, r.priority_score])
story += [table(rows, [1.4, 2.4, 3.3, 1.8, 2.5, 2.2, 1.6]), Paragraph("Table 4. Maintenance ranking from an 8-vehicle run.", CAP), Spacer(1, 8)]
p("The network located all five simulated potholes. <b>Demonstration assumptions:</b> the pairing of test images to sites, "
  "and the traffic and road-importance values, are illustrative because no real road data was collected.")
fig(os.path.join(ML, "site4_detection.jpg"), 8.5, "Figure 8. YOLOv8 detection on a held-out test image.")

h1("6. Limitations")
bullets(["Vibration and GPS data are synthetic; no real vehicle trial was carried out.",
         "UDGM is an idealised radio model, so real-world links will perform differently.",
         "Vehicle broadcasts have no retransmission, which limits PDR at higher vehicle counts.",
         "Battery lifetime is calculated from duty cycle and is not a measured discharge.",
         "The image-to-site pairing and the traffic and road values in the ranking are assumed.",
         "AODV was compared qualitatively only."])

h1("7. Conclusion")
p(f"The system ran end to end in Cooja: vehicle nodes reported potholes, a redundant RPL gateway tree delivered "
  f"{nf.loc[8].pdr:.1f}-{nf.loc[2].pdr:.1f}% of reports with mean delay under 1.4 s, and the network re-formed within "
  f"{rec.min():.0f}-{rec.max():.0f} s of losing a gateway. YOLOv8 reached mAP@50 of {ml['mAP50']:.2f} on held-out images, and the "
  "server combined both sources into a repair ranking. The next steps would be acknowledged vehicle-to-gateway delivery "
  "to raise PDR, and a field trial with real accelerometers.")

story.append(PageBreak())
h1("Appendix: Viva Preparation")
qa = [("Why RPL and not AODV?", "Our backbone is static and all traffic goes to one sink, which is what a DODAG is built for. RPL is also native to Contiki's IPv6 stack. We did not simulate AODV, so we claim no measured advantage."),
      ("RPL handles mobility poorly. Why use it with vehicles?", "Vehicles are not part of RPL. They are IPv6 hosts with RPL compiled out and only broadcast one hop. Only the static gateways route."),
      ("What is a DODAG?", "A Destination-Oriented Directed Acyclic Graph: a loop-free structure in which every node has a route toward the root, here the sink."),
      ("What are DIO, DAO and DIS?", "DIO advertises the DODAG and rank. DIS asks neighbours for a DIO. DAO advertises downward routes."),
      ("How is a parent chosen?", "By rank from the objective function. Contiki 3.0 uses MRHOF with ETX by default, which estimates expected transmissions per link."),
      ("What is Trickle?", "A timer that spaces DIOs further apart while the network is stable and resets them when something changes, saving control traffic."),
      ("Why does PDR fall as vehicles increase?", "More vehicle broadcasts compete for the channel, and those broadcasts have no acknowledgement or retransmission."),
      ("Why is delay highest with 2 vehicles?", "Gateways flush after 3 records or 2 s. With little traffic, batches more often wait for the timer."),
      ("Why is the failure's PDR effect so small?", "Each gateway has a twin, coverage overlaps, and children re-parent in seconds. The difference is within seed-to-seed variation."),
      ("Why is sink power about 60 mW?", "Its radio is kept on continuously, because it is assumed mains powered. Other nodes duty-cycle using ContikiMAC."),
      ("Is the sensor data real?", "No. Cooja has no road or GPS, so inputs are synthetic. The sampling, detection, networking and routing code does run on emulated Sky motes."),
      ("How do YOLOv8 images reach the server?", "Not over the WSN, because 802.15.4 frames are at most 127 bytes. They would travel over 4G or Wi-Fi."),
      ("What does UDGM do?", "It models a disk: nodes within transmission range can receive, with a configurable success ratio; those within interference range can only interfere."),
      ("What does mAP@50 mean?", "Mean average precision, counting a detection as correct when its box overlaps the true box by at least 50% IoU.")]
for q, a in qa:
    story.append(KeepTogether([Paragraph(f"<b>Q. {q}</b>", ParagraphStyle("Q", parent=BODY, spaceAfter=1, fontSize=10.5, leading=13)), Paragraph(a, ParagraphStyle("A", parent=BODY, spaceAfter=5, fontSize=10.5, leading=13))]))


def footer(canvas, doc):
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(colors.HexColor("#52514e"))
    if doc.page > 1:
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, str(doc.page))


SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2.3 * cm, rightMargin=2.3 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
                  title="WSN-Based Pothole Detection and Priority Monitoring: Project Report",
                  author="Harsh Gupta, Debabrata Bhattacharya").build(story, onFirstPage=footer, onLaterPages=footer)
print(os.path.abspath(OUT))
