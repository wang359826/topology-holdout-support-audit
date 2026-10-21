#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build the journal table-of-contents graphic for the v6 paper.

The v5 TOC was a composite of the superseded eight-figure layout. The first v6
attempt simply cropped two panels, which kept the panels' own "(a)" titles, the
eleven per-topology labels and the small decimals -- unreadable at 3.25 in.

This version draws a purpose-built two-block schematic instead:

    (a) what the split withholds  ->  74.7% of coarse compositions are private
                                      to one topology (read from the archive)
    (b) what that costs at screening -> top-1% recovery 50.4% -> 19.3%
                                      (five-seed means, read from the archive)

The two blocks are separated by a rule, not an arrow: the TOC must not suggest
that the support loss has been shown to cause the ranking loss (it has not).

    python scripts/build_toc_v6.py --width 975 --height 525 --dpi 300
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "outputs"
FIGDIR = PKG.parent / "01_manuscript" / "figures"
SEEDS = ["42", "143", "244", "345", "446"]


def read_csv(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def archive_numbers():
    """Return (single_topology_pct, random_pct, topology_pct) from the archive."""
    conf = [r for r in read_csv("confound_full.csv")
            if r["granularity"].startswith("coarse")][0]
    single = 100.0 * float(conf["frac_single_topology"])
    vals = {"random": [], "topology": []}
    for seed in SEEDS:
        for r in read_csv(f"screening_utility_seed{seed}.csv"):
            if abs(float(r["k_frac"]) - 0.01) < 1e-9 and r["strategy"] in vals:
                vals[r["strategy"]].append(100.0 * float(r["overlap_at_k"]))
    rand = sum(vals["random"]) / len(vals["random"])
    topo = sum(vals["topology"]) / len(vals["topology"])
    # guardrails: the TOC must print the numbers the paper quotes
    assert abs(single - 74.7226) < 0.01, single
    assert abs(rand - 50.40) < 0.01 and abs(topo - 19.28) < 0.01, (rand, topo)
    return single, rand, topo


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=975)
    ap.add_argument("--height", type=int, default=525)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=str(FIGDIR / "TOC_graphic.png"))
    args = ap.parse_args()

    single, rand, topo = archive_numbers()
    ink, mid, light = "#1a1a1a", "#5a5a5a", "#b9c6d6"
    blue, red = "#1f77b4", "#c0392b"

    fig = plt.figure(figsize=(args.width / args.dpi, args.height / args.dpi),
                     dpi=args.dpi)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # sizes are absolute points on a 3.25 x 1.75 in canvas: 1 pt = 0.8% of the
    # height, so the type hierarchy has to be chosen for print size, not screen
    F_LABEL, F_TITLE, F_BIG, F_BODY, F_BAR = 6.5, 8.0, 17.0, 5.6, 4.8

    # ---------------- block (a): support loss ----------------
    ax.text(0.035, 0.93, "(a)", fontsize=F_LABEL, fontweight="bold", color=mid,
            va="top")
    ax.text(0.035, 0.845, "Support removed", fontsize=F_TITLE,
            fontweight="bold", color=ink, va="top")
    ax.text(0.035, 0.60, f"{single:.1f}%", fontsize=F_BIG, fontweight="bold",
            color=blue, va="center")
    ax.text(0.035, 0.44,
            "of coarse compositions are\nprivate to one topology",
            fontsize=F_BODY, color=mid, va="top", linespacing=1.6)
    bar_x, bar_w, bar_h = 0.035, 0.34, 0.055
    ax.add_patch(Rectangle((bar_x, 0.18), bar_w, bar_h, facecolor=light,
                           edgecolor="none"))
    ax.add_patch(Rectangle((bar_x, 0.18), bar_w * single / 100.0, bar_h,
                           facecolor=blue, edgecolor="none"))
    # no side label: the caption above already names what the bar measures,
    # and a label here ran into the right-hand block
    ax.text(bar_x + bar_w * single / 100.0 - 0.008, 0.18 + bar_h / 2,
            f"{single:.1f}%", fontsize=F_BAR, color="white", va="center",
            ha="right")

    # ---------------- divider (a rule, not an arrow) ----------------
    ax.plot([0.495, 0.495], [0.12, 0.93], color="#d5d5d5", lw=0.8)

    # ---------------- block (b): screening cost ----------------
    ax.text(0.525, 0.93, "(b)", fontsize=F_LABEL, fontweight="bold", color=mid,
            va="top")
    ax.text(0.525, 0.845, "Cost at screening", fontsize=F_TITLE,
            fontweight="bold", color=ink, va="top")
    ax.text(0.520, 0.60, f"{rand:.1f}% \u2192 {topo:.1f}%",
            fontsize=F_BIG - 5, fontweight="bold", color=red, va="center")
    ax.text(0.525, 0.44,
            "top-1% recovery, 0\u2013100% scale\n(random split \u2192 topology hold-out)",
            fontsize=F_BODY, color=mid, va="top", linespacing=1.6)
    y0, h = 0.185, 0.035
    for j, (lab, v, c) in enumerate((("random", rand, blue),
                                     ("topology", topo, red))):
        y = y0 + (1 - j) * (h + 0.02)
        ax.add_patch(Rectangle((0.585, y), 0.30, h, facecolor=light,
                               edgecolor="none"))
        ax.add_patch(Rectangle((0.585, y), 0.30 * v / 100.0, h, facecolor=c,
                               edgecolor="none"))
        ax.text(0.578, y + h / 2, lab, fontsize=F_BAR, color=mid,
                va="center", ha="right")
        ax.text(0.585 + 0.30 + 0.010, y + h / 2, f"{v:.1f}%", fontsize=F_BAR,
                color=mid, va="center")

    out = Path(args.out)
    fig.savefig(out, dpi=args.dpi, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}  {args.width}x{args.height} px @ {args.dpi} dpi "
          f"({out.stat().st_size / 1024:.0f} KB)")
    print(f"  numbers read from the archive: {single:.1f}% | "
          f"{rand:.1f}% -> {topo:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
