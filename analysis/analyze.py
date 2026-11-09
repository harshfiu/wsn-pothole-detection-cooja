#!/usr/bin/env python3
"""Turns the raw Cooja logs into metrics tables and charts.

Every number here comes from results/raw/*.log. Log format: time_us <TAB> node <TAB> message.
"""
import glob
import os
import re
import statistics as st
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
RAW = os.path.join(ROOT, "raw")
CHARTS = os.path.join(ROOT, "charts")
os.makedirs(CHARTS, exist_ok=True)

# Tmote Sky current draw (mA) at 3 V; battery assumed 2 x AA, 2500 mAh.
I_CPU, I_LPM, I_TX, I_RX = 1.8, 0.0545, 17.7, 20.0
VOLTS, BATTERY_MAH = 3.0, 2500.0
RECORD_BYTES = 14
FAIL_S = 300
END_S = 600
START_S = 60

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlelocation": "left", "axes.titleweight": "bold", "axes.titlesize": 13,
    "axes.titlecolor": INK, "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID,
})


def parse(path):
    tx, rx = {}, {}
    energy = {}
    parents = []
    fail = None
    for line in open(path, encoding="utf-8", errors="replace"):
        p = line.rstrip("\n").split("\t")
        if len(p) != 3:
            continue
        t, node, msg = int(p[0]) / 1e6, int(p[1]), p[2]
        f = msg.split(",")
        if f[0] == "TX":
            tx[(int(f[1]), int(f[2]))] = t
        elif f[0] == "RX":
            key = (int(f[3]), int(f[4]))
            if key not in rx:
                rx[key] = (t, int(f[2]), int(f[1]))
        elif f[0] == "ENERGY":
            energy.setdefault(node, []).append((t, *map(int, f[2:6])))
        elif f[0] == "PARENT":
            parents.append((t, int(f[1]), int(f[2])))
        elif f[0] == "FAIL":
            fail = (t, int(f[1]))
    return tx, rx, energy, parents, fail


def power_mw(samples):
    """Average power between the first and last energy log of one node."""
    if len(samples) < 2:
        return None
    a, b = samples[0], samples[-1]
    d = [(y - x) / 32768.0 for x, y in zip(a[1:], b[1:])]
    total = d[0] + d[1]
    if total <= 0:
        return None
    return (d[0] * I_CPU + d[1] * I_LPM + d[2] * I_TX + d[3] * I_RX) * VOLTS / total


def recovery(parents, fail):
    """Slowest re-parenting among the victim's child gateways, in seconds."""
    if fail is None:
        return None, 0
    t_fail, victim = fail
    current = {}
    for t, n, p in parents:
        if t < t_fail:
            current[n] = p
    children = [n for n, p in current.items() if p == victim]
    times = []
    for c in children:
        for t, n, p in parents:
            if n == c and t >= t_fail and p not in (0, victim):
                times.append(t - t_fail)
                break
    if not children or len(times) != len(children):
        return None, len(children)
    return max(times), len(children)


def role(n):
    return "sink" if n == 1 else "gateway" if n <= 7 else "vehicle"


rows, bins = [], defaultdict(lambda: defaultdict(lambda: [0, 0]))
for path in sorted(glob.glob(os.path.join(RAW, "v*_f*_s*.log"))):
    m = re.search(r"v(\d+)_f(\d+)_s(\d+)", path)
    veh, fail_s, seed = map(int, m.groups())
    tx, rx, energy, parents, fail = parse(path)
    delays = [rx[k][0] - t for k, t in tx.items() if k in rx]
    hops = [rx[k][1] for k in tx if k in rx]
    delivered = sum(1 for k in tx if k in rx)
    pre = [k for k, t in tx.items() if t < FAIL_S]
    post = [k for k, t in tx.items() if t >= FAIL_S]
    power = defaultdict(list)
    for n, s in energy.items():
        w = power_mw(s)
        if w is not None:
            power[role(n)].append(w)
    rec, children = recovery(parents, fail)
    avg = lambda v: sum(v) / len(v) if v else float("nan")
    veh_mw, gw_mw = avg(power["vehicle"]), avg(power["gateway"])
    rows.append({
        "vehicles": veh, "failure": fail_s > 0, "seed": seed, "sent": len(tx), "delivered": delivered,
        "pdr": 100.0 * delivered / len(tx), "delay_s": avg(delays), "hops": avg(hops),
        "throughput_bps": delivered * RECORD_BYTES * 8.0 / (END_S - START_S),
        "pdr_before": 100.0 * sum(k in rx for k in pre) / max(len(pre), 1),
        "pdr_after": 100.0 * sum(k in rx for k in post) / max(len(post), 1),
        "delay_before": avg([rx[k][0] - tx[k] for k in pre if k in rx]),
        "delay_after": avg([rx[k][0] - tx[k] for k in post if k in rx]),
        "hops_before": avg([rx[k][1] for k in pre if k in rx]),
        "hops_after": avg([rx[k][1] for k in post if k in rx]),
        "vehicle_mw": veh_mw, "gateway_mw": gw_mw, "sink_mw": avg(power["sink"]),
        "vehicle_life_days": BATTERY_MAH * VOLTS / veh_mw / 24.0,
        "gateway_life_days": BATTERY_MAH * VOLTS / gw_mw / 24.0,
        "failed_node": fail[1] if fail else None, "children": children, "recovery_s": rec,
    })
    for k, t in tx.items():
        b = int(t // 30) * 30
        bins[(veh, fail_s > 0)][b][0] += 1
        bins[(veh, fail_s > 0)][b][1] += k in rx

df = pd.DataFrame(rows)
df.to_csv(os.path.join(ROOT, "per_run_metrics.csv"), index=False)

cols = ["pdr", "delay_s", "hops", "throughput_bps", "vehicle_mw", "gateway_mw", "sink_mw",
        "vehicle_life_days", "gateway_life_days", "pdr_before", "pdr_after",
        "delay_before", "delay_after", "hops_before", "hops_after", "recovery_s"]
g = df.groupby(["vehicles", "failure"])
summary = g[cols].mean().round(3)
for c in ["pdr", "delay_s"]:
    summary[c + "_std"] = g[c].std().round(3)
summary["runs"] = g.size()
summary["children_mean"] = g["children"].mean().round(2)
summary["recovered_runs"] = g["recovery_s"].count()
summary.to_csv(os.path.join(ROOT, "summary.csv"))
print(summary.T.to_string())
print("runs:", len(df), "failed nodes:", df["failed_node"].value_counts().to_dict())


def compare(col, std, title, ylabel, fname, ylim=None):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
    for fail, colour, label, marker in [(False, BLUE, "No failure", "o"),
                                        (True, ORANGE, "Gateway failure at 300 s", "s")]:
        s = summary.xs(fail, level="failure")
        ax.errorbar(s.index, s[col], yerr=s[std] if std else None, color=colour, lw=2,
                    marker=marker, ms=8, mec=SURFACE, mew=2, capsize=3, label=label)
    ax.set_title(title, pad=14)
    ax.set_xlabel("Number of vehicle nodes")
    ax.set_ylabel(ylabel)
    ax.set_xticks([2, 4, 6, 8])
    if ylim:
        ax.set_ylim(*ylim)
    ax.legend(frameon=False, labelcolor=MUTED)
    fig.tight_layout()
    fig.savefig(os.path.join(CHARTS, fname))
    plt.close(fig)


low = max(0, min(df["pdr"].min() - 5, 80))
compare("pdr", "pdr_std", "Packet delivery ratio", "PDR (%), mean of 5 seeds", "pdr_vs_vehicles.png", (low, 101))
compare("delay_s", "delay_s_std", "End-to-end delay", "Delay (s), mean of 5 seeds", "delay_vs_vehicles.png", (0, None))

# PDR over time, 8 vehicles.
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
for fail, colour, label, marker in [(False, BLUE, "No failure", "o"), (True, ORANGE, "Gateway failure at 300 s", "s")]:
    d = bins[(8, fail)]
    xs = sorted(k for k in d if k >= 60 and k + 30 <= END_S)
    ax.plot([x + 15 for x in xs], [100.0 * d[x][1] / d[x][0] for x in xs], color=colour, lw=2,
            marker=marker, ms=6, mec=SURFACE, mew=1.5, label=label)
ax.axvline(FAIL_S, color=MUTED, lw=1, ls="--")
ax.annotate("gateway removed", (FAIL_S, low + 2), xytext=(6, 0), textcoords="offset points", color=MUTED, fontsize=10)
ax.set_title("PDR over time with 8 vehicles", pad=14)
ax.set_xlabel("Simulation time (s), 30 s bins")
ax.set_ylabel("PDR (%), 5 seeds pooled")
ax.set_ylim(low, 101)
ax.legend(frameon=False, labelcolor=MUTED, loc="lower left")
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "pdr_timeline.png"))
plt.close(fig)

# Power by role, no-failure runs.
s = df[~df["failure"]][["vehicle_mw", "gateway_mw", "sink_mw"]].mean()
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=200)
labels = ["Vehicle node", "Roadside gateway", "Sink (radio always on)"]
bars = ax.bar(labels, s.values, color=BLUE, width=0.45)
for b, v in zip(bars, s.values):
    ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f} mW", ha="center", va="bottom", color=INK)
ax.set_title("Average power per node", pad=14)
ax.set_ylabel("Power (mW), no-failure runs")
fig.tight_layout()
fig.savefig(os.path.join(CHARTS, "power_by_role.png"))
plt.close(fig)
