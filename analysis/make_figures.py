#!/usr/bin/env python3
"""Draws the replacement diagrams for the slides and the report.

Each figure matches the aspect ratio of the picture it replaces in the deck.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)

NAVY, BLUE, GREEN, RED, GREY, INK, PANEL = "#1a1a8c", "#2a78d6", "#2e8b57", "#d93a3a", "#6b6b6b", "#0b0b0b", "#f4f4f4"
plt.rcParams.update({"font.family": "DejaVu Sans"})


def canvas(w, h, xlim, ylim):
    fig, ax = plt.subplots(figsize=(w, h), dpi=220)
    fig.patch.set_facecolor(PANEL)
    ax.set_facecolor(PANEL)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    return fig, ax


def node(ax, x, y, text, colour, r=9, size=12, txt="white"):
    ax.add_patch(plt.Circle((x, y), r, color=colour, zorder=3))
    ax.text(x, y, text, ha="center", va="center", color=txt, fontsize=size, fontweight="bold", zorder=4)


def link(ax, a, b, colour=GREY, lw=2, ls="-", arrow=True, shrink=11):
    style = "-|>" if arrow else "-"
    ax.annotate("", xy=b, xytext=a, zorder=2,
                arrowprops=dict(arrowstyle=style, color=colour, lw=lw, ls=ls, shrinkA=shrink, shrinkB=shrink,
                                mutation_scale=14))


def topology():
    fig, ax = canvas(8.54, 4.2, (-22, 205), (-62, 50))
    pos = {2: (35, 18), 3: (35, -18), 4: (85, 18), 5: (85, -18), 6: (135, 18), 7: (135, -18)}
    ax.add_patch(plt.Rectangle((-14, -6), 214, 12, color="#d9d9d9", zorder=1))
    ax.text(186, 0, "road", ha="center", va="center", fontsize=11, color=GREY)
    for a, b in [(6, 4), (7, 5), (4, 2), (5, 3), (2, 1), (3, 1)]:
        link(ax, pos[a], pos.get(b, (-6, 0)), NAVY, 2.2, shrink=12)
    for a, b in [(6, 5), (7, 4), (4, 3), (5, 2)]:
        link(ax, pos[a], pos[b], "#9a9ad0", 1.2, "--", shrink=12)
    node(ax, -6, 0, "Sink", INK, 11, 11)
    for n, (x, y) in pos.items():
        node(ax, x, y, f"G{n}", NAVY, 9.5, 12)
    for x, y, t in [(46, 0, "V"), (98, 0, "V"), (158, 0, "V")]:
        node(ax, x, y, t, GREEN, 6.5, 11)
    for sx, gx, gy in [(46, 35, -18), (98, 85, 18), (158, 135, -18)]:
        link(ax, (sx, 0), (gx, gy), GREEN, 1.2, ":", shrink=9)
    ax.text(85, 41, "Static roadside gateways: wireless, multi-hop RPL tree (solid = current parent, dashed = backup)",
            ha="center", fontsize=10.5, color=NAVY)
    ax.text(100, -37, "V = vehicle node (accelerometer + GPS): one-hop broadcast to any gateway in range",
            ha="center", fontsize=10.5, color=GREEN)
    ax.add_patch(plt.Rectangle((-14, -60), 214, 15, color="white", ec="#c9c9c9", zorder=1))
    ax.text(93, -52.5, "Sink  →  Monitoring server (serial)        Dashcam images  →  server over 4G/Wi-Fi  →  YOLOv8",
            ha="center", va="center", fontsize=10.5, color=INK)
    fig.savefig(os.path.join(FIG, "topology_rpl.png"))
    plt.close(fig)


def cycle():
    fig, ax = canvas(6.42, 2.44, (0, 263), (0, 100))
    root, a, b, c = (28, 50), (108, 80), (108, 20), (205, 50)
    for s, d, lab, xy in [(root, a, "", None), (root, b, "", None), (a, c, "", None), (b, c, "", None)]:
        link(ax, s, d, BLUE, 1.6, "--", shrink=16)
    ax.text(68, 84, "DIO", color=BLUE, fontsize=11, fontweight="bold", ha="center")
    link(ax, (205, 40), (116, 12), GREEN, 2.4, shrink=16)
    link(ax, (100, 12), (28, 40), GREEN, 2.4, shrink=16)
    ax.text(160, 7, "data to sink", color=GREEN, fontsize=11, fontweight="bold", ha="center")
    node(ax, *root, "Sink", INK, 13, 11)
    node(ax, *a, "G2", NAVY, 12, 11)
    node(ax, *b, "G3", NAVY, 12, 11)
    node(ax, *c, "G4", NAVY, 12, 11)
    ax.text(205, 79, "rank = cost\nto sink", color=GREY, fontsize=10.5, ha="center", va="center")
    fig.savefig(os.path.join(FIG, "rpl_cycle.png"))
    plt.close(fig)


def recovery(rec_s):
    fig, ax = canvas(5.24, 2.48, (0, 214), (0, 101))
    sink, g2, g3, g4 = (22, 50), (108, 80), (108, 20), (192, 50)
    link(ax, g4, g2, GREY, 2, shrink=15)
    link(ax, g2, sink, GREY, 2, shrink=15)
    link(ax, g4, g3, GREEN, 3, shrink=15)
    link(ax, g3, sink, GREEN, 3, shrink=15)
    node(ax, *sink, "Sink", INK, 13, 10)
    node(ax, *g2, "G2", "#9a9a9a", 12, 11)
    node(ax, *g3, "G3", GREEN, 12, 11)
    node(ax, *g4, "G4", NAVY, 12, 11)
    ax.plot([116, 130], [82, 96], color=RED, lw=4, zorder=5)
    ax.plot([116, 130], [96, 82], color=RED, lw=4, zorder=5)
    ax.text(135, 89, "removed", color=RED, fontsize=11, fontweight="bold", va="center")
    ax.text(127, 11, f"new parent in about {rec_s:.0f} s", color=GREEN, fontsize=11, fontweight="bold", va="center")
    fig.savefig(os.path.join(FIG, "rpl_recovery.png"))
    plt.close(fig)


def slide_chart():
    s = pd.read_csv(os.path.join(ROOT, "summary.csv"))
    fig, ax = plt.subplots(figsize=(6.16, 4.4), dpi=220)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for fail, colour, label, m in [(False, "#2a78d6", "No failure", "o"), (True, "#eb6834", "Gateway failure at 300 s", "s")]:
        d = s[s.failure == fail]
        ax.errorbar(d.vehicles, d.pdr, yerr=d.pdr_std, color=colour, lw=2.4, marker=m, ms=10, mec="#fcfcfb", mew=2,
                    capsize=4, label=label)
    ax.set_ylim(70, 102)
    ax.set_xticks([2, 4, 6, 8])
    ax.set_xlabel("Number of vehicle nodes", fontsize=13, color="#52514e")
    ax.set_ylabel("PDR (%), mean ± SD, 5 seeds", fontsize=13, color="#52514e")
    ax.tick_params(colors="#52514e", labelsize=12)
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]:
        ax.spines[sp].set_color("#e6e5e0")
    ax.grid(axis="y", color="#e6e5e0")
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=12, labelcolor="#52514e", loc="lower left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "slide5_pdr.png"))
    plt.close(fig)


if __name__ == "__main__":
    s = pd.read_csv(os.path.join(ROOT, "summary.csv"))
    topology()
    cycle()
    recovery(s[s.failure].recovery_s.mean())
    slide_chart()
