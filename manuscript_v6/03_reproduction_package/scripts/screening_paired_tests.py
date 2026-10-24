#!/usr/bin/env python
"""Paired-seed tests quoted in the manuscript, recomputed from archived outputs.

Two quantities are produced, both from five paired seeds (42, 143, 244, 345, 446):

1. the screening gap  random top-1% overlap - topology top-1% overlap  (percentage points);
2. the nbo-side arm (a) -> (b) MAE change, reported both in mmol/g and as a
   percentage of the arm-(a) mean with that denominator held fixed.

Everything uses the standard library only (no numpy/scipy): the two-sided p-value
of a t statistic with df = 4 is evaluated from the closed-form CDF of the
t(4) distribution, F(t) = 1/2 + u(3 + 2u^2) / (4 (1 + u^2)^(3/2)), u = t/2.
The same 95% multiplier T4 = 2.7764451051977987 is used by
verify_followup_tables.py, so the intervals are on one convention.

Writes outputs/paired_tests_20261024.csv. Run from any working directory:

    python scripts/screening_paired_tests.py
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / "outputs"
SEEDS = ["42", "143", "244", "345", "446"]
T4 = 2.7764451051977987          # two-sided 95% multiplier, df = 4
DF = 4


def read_csv(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def t4_sf_two_sided(t: float) -> float:
    """Two-sided p for a t statistic with df = 4 (closed form)."""
    u = abs(t) / 2.0
    return 1.0 - u * (3.0 + 2.0 * u * u) / (2.0 * (1.0 + u * u) ** 1.5)


def paired(diffs):
    n = len(diffs)
    m = statistics.mean(diffs)
    sd = statistics.stdev(diffs)
    se = sd / math.sqrt(n)
    t = m / se
    return {
        "n": n, "estimate": m, "sd": sd, "se": se, "t": t,
        "df": DF, "p": t4_sf_two_sided(t),
        "ci_low": m - T4 * se, "ci_high": m + T4 * se,
    }


def screening_gap():
    top = {}
    for s in SEEDS:
        rows = read_csv(f"screening_utility_seed{s}.csv")
        vals = {r["strategy"]: float(r["overlap_at_k"]) * 100.0
                for r in rows if abs(float(r["k_frac"]) - 0.01) < 1e-9}
        top[s] = (vals["random"], vals["topology"])
    diffs = [top[s][0] - top[s][1] for s in SEEDS]
    res = paired(diffs)
    res["random_mean"] = statistics.mean(top[s][0] for s in SEEDS)
    res["random_sd"] = statistics.stdev(top[s][0] for s in SEEDS)
    res["topology_mean"] = statistics.mean(top[s][1] for s in SEEDS)
    res["topology_sd"] = statistics.stdev(top[s][1] for s in SEEDS)
    res["per_seed"] = {s: top[s] for s in SEEDS}
    return res


def nbo_arm_ab():
    rows = read_csv("isoreticular_control_seeds.csv")
    by = {}
    for r in rows:
        if r["test_topo"] == "nbo":
            by.setdefault(r["seed"], {})[r["regime"]] = float(r["MAE"])
    diffs = [by[s]["without_pair"] - by[s]["with_pair"] for s in SEEDS]
    a_mean = statistics.mean(by[s]["with_pair"] for s in SEEDS)
    res = paired(diffs)
    res["a_mean"] = a_mean
    res["pct"] = 100.0 * res["estimate"] / a_mean
    res["pct_ci_low"] = 100.0 * res["ci_low"] / a_mean
    res["pct_ci_high"] = 100.0 * res["ci_high"] / a_mean
    res["per_seed"] = {s: by[s] for s in SEEDS}
    return res


def main() -> int:
    gap = screening_gap()
    ab = nbo_arm_ab()

    rows = [
        {
            "test": "screening top-1% overlap, random minus topology",
            "unit": "percentage points",
            "n": gap["n"], "estimate": gap["estimate"], "sd": gap["sd"],
            "se": gap["se"], "t": gap["t"], "df": gap["df"], "p": gap["p"],
            "ci_low": gap["ci_low"], "ci_high": gap["ci_high"],
            "reference": "random 50.4 / topology 19.3, five 25,000-row redraws",
        },
        {
            "test": "nbo MAE, arm (b) minus arm (a)",
            "unit": "mmol/g",
            "n": ab["n"], "estimate": ab["estimate"], "sd": ab["sd"],
            "se": ab["se"], "t": ab["t"], "df": ab["df"], "p": ab["p"],
            "ci_low": ab["ci_low"], "ci_high": ab["ci_high"],
            "reference": "arm (a) mean 0.1065 mmol/g, denominator held fixed",
        },
        {
            "test": "nbo MAE change, arm (a) to (b)",
            "unit": "percent of arm-(a) mean",
            "n": ab["n"], "estimate": ab["pct"], "sd": "",
            "se": "", "t": ab["t"], "df": ab["df"], "p": ab["p"],
            "ci_low": ab["pct_ci_low"], "ci_high": ab["pct_ci_high"],
            "reference": "interval bounds are the mmol/g bounds divided by 0.1065",
        },
    ]

    path = OUT / "paired_tests_20261024.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.6f}" if isinstance(v, float) else v)
                        for k, v in r.items()})

    print(f"wrote {path.relative_to(PKG)}")
    print(f"  screening gap          : {gap['estimate']:.4f} pp  "
          f"SD {gap['sd']:.4f}  95% CI [{gap['ci_low']:.4f}, {gap['ci_high']:.4f}]  "
          f"t({gap['df']}) = {gap['t']:.4f}  p = {gap['p']:.6f}")
    print(f"    random   {gap['random_mean']:.2f} +/- {gap['random_sd']:.2f}")
    print(f"    topology {gap['topology_mean']:.2f} +/- {gap['topology_sd']:.2f}")
    print(f"  nbo (b)-(a)            : {ab['estimate']:.6f} mmol/g  "
          f"95% CI [{ab['ci_low']:.6f}, {ab['ci_high']:.6f}]  "
          f"t({ab['df']}) = {ab['t']:.4f}  p = {ab['p']:.6f}")
    print(f"  nbo (b)/(a) - 1        : {ab['pct']:.2f}%  "
          f"95% CI [{ab['pct_ci_low']:.2f}, {ab['pct_ci_high']:.2f}]%")
    print("  note: intervals carry the five-seed, one-database scope of main-text 2.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
