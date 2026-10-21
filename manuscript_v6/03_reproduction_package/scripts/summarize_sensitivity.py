#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Summarize the five-seed cleaning sensitivity (v6 supplement, 2026-10-21).

Reads the per-seed `sensitivity_screening_seed<N>.csv` and
`sensitivity_arms_seed<N>.csv` tables (produced by
`sensitivity_invalid_rows.py`) and writes one row per seed with the
top-1% and intervention metrics used in SI-A.4.

Usage:
  python scripts/summarize_sensitivity.py --outdir outputs
"""
import argparse
import os
import sys

import pandas as pd

SEEDS = [42, 143, 244, 345, 446]


def _top1(frame, strategy, population):
    sub = frame[
        (frame["analysis"] == f"screening::{strategy}")
        & (frame["fit_population"] == population)
        & (frame["scoring_rows"] == "all_rows")
        & (abs(pd.to_numeric(frame["k_frac"]) - 0.01) < 1e-9)
    ]
    if len(sub) != 1:
        raise SystemExit(f"screening::{strategy}/{population}: {len(sub)} rows at k=1%")
    return float(sub["overlap_at_k"].iloc[0])


def _arm_mae(frame, topology, arm, population):
    sub = frame[
        (frame["analysis"] == f"arms::{topology}::{arm}")
        & (frame["fit_population"] == population)
        & (frame["scoring_rows"] == "all_rows")
        & (abs(pd.to_numeric(frame["k_frac"]) + 1) < 1e-9)
    ]
    if len(sub) != 1:
        raise SystemExit(f"arms::{topology}::{arm}/{population}: {len(sub)} aggregate rows")
    return float(sub["mae"].iloc[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(__file__), "..", "outputs"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    outdir = os.path.abspath(args.outdir)
    rows = []
    for seed in SEEDS:
        sp = os.path.join(outdir, f"sensitivity_screening_seed{seed}.csv")
        ap_ = os.path.join(outdir, f"sensitivity_arms_seed{seed}.csv")
        if not (os.path.exists(sp) and os.path.exists(ap_)):
            raise SystemExit(f"missing seed {seed}: {sp} or {ap_}")
        s = pd.read_csv(sp)
        a = pd.read_csv(ap_)
        r_h, r_c = _top1(s, "random", "historical"), _top1(s, "random", "cleaned")
        t_h, t_c = _top1(s, "topology", "historical"), _top1(s, "topology", "cleaned")
        na_h, na_c = _arm_mae(a, "nbo", "a", "historical"), _arm_mae(a, "nbo", "a", "cleaned")
        nb_h, nb_c = _arm_mae(a, "nbo", "b", "historical"), _arm_mae(a, "nbo", "b", "cleaned")
        ne_h, ne_c = _arm_mae(a, "nbo", "e", "historical"), _arm_mae(a, "nbo", "e", "cleaned")
        pa_h, pa_c = _arm_mae(a, "pcu", "a", "historical"), _arm_mae(a, "pcu", "a", "cleaned")
        pe_h, pe_c = _arm_mae(a, "pcu", "e", "historical"), _arm_mae(a, "pcu", "e", "cleaned")
        rows.append({
            "seed": seed,
            "random_h": r_h, "random_c": r_c,
            "topology_h": t_h, "topology_c": t_c,
            "gap_h": r_h - t_h, "gap_c": r_c - t_c,
            "dgap": (r_c - t_c) - (r_h - t_h),
            "nbo_a_h": na_h, "nbo_a_c": na_c,
            "nbo_b_h": nb_h, "nbo_b_c": nb_c,
            "nbo_e_h": ne_h, "nbo_e_c": ne_c,
            "nbo_ab_h": nb_h - na_h, "nbo_ab_c": nb_c - na_c,
            "pcu_a_h": pa_h, "pcu_a_c": pa_c,
            "pcu_e_h": pe_h, "pcu_e_c": pe_c,
            "pcu_ae_h": pe_h - pa_h, "pcu_ae_c": pe_c - pa_c,
        })
    frame = pd.DataFrame(rows)
    out = args.out or os.path.join(outdir, "sensitivity_five_seeds_summary.csv")
    frame.to_csv(out, index=False, encoding="utf-8")
    print(f"wrote {out} ({len(frame)} seeds)")
    print(frame.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
