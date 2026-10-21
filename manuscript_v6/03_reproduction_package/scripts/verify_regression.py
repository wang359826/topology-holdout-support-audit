#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Positive/negative regression test for the read-only LOTO verifier.

The verifier must (a) accept the archived data and (b) reject corrupted inputs. A
verifier that silently overwrites an earlier failure with a later pass would satisfy
(a) while failing (b), so this test exercises both directions.

It copies the four archived CSVs into a scratch directory under `outputs/`, corrupts
one field per case, runs `loto_full_metrics.py verify` on the copy, and checks the exit
code. **The archived CSVs are never modified.**

Usage (from 03_reproduction_package/):
    python scripts/verify_regression.py

Exit code 0 means every case behaved as expected.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(PKG, "outputs")
SCRIPT = os.path.join(HERE, "loto_full_metrics.py")
BASE = os.path.join(OUT, "_verify_regression_tmp")

FILES = ["loto_per_topology_metrics_100k.csv", "loto_aggregates_100k.csv",
         "loto_per_topology_metrics_25k.csv", "loto_aggregates_25k.csv"]


def _write(df, path):
    df.to_csv(path, index=False, encoding="utf-8-sig")


def case_archived(d):
    pass


def case_100k_mae_999(d):
    p = os.path.join(d, "loto_per_topology_metrics_100k.csv")
    df = pd.read_csv(p)
    df.loc[df.index[0], "MAE"] = 999.0
    _write(df, p)


def case_100k_r2_999(d):
    p = os.path.join(d, "loto_per_topology_metrics_100k.csv")
    df = pd.read_csv(p)
    df.loc[df.index[0], "R2"] = 999.0
    _write(df, p)


def case_25k_weighted_999(d):
    p = os.path.join(d, "loto_aggregates_25k.csv")
    df = pd.read_csv(p)
    df.loc[df.index[0], "weighted"] = 999.0
    _write(df, p)


def case_valid_flag_flipped(d):
    p = os.path.join(d, "loto_per_topology_metrics_100k.csv")
    df = pd.read_csv(p)
    df.loc[df.index[0], "valid_R2"] = False
    _write(df, p)


def case_negative_mae(d):
    p = os.path.join(d, "loto_per_topology_metrics_100k.csv")
    df = pd.read_csv(p)
    df.loc[df.index[0], "MAE"] = -1.0
    _write(df, p)


CASES = [
    ("archived data (unchanged)", case_archived, True),
    ("100k MAE -> 999", case_100k_mae_999, False),
    ("100k R2 -> 999", case_100k_r2_999, False),
    ("25k weighted -> 999", case_25k_weighted_999, False),
    ("100k valid_R2 -> False", case_valid_flag_flipped, False),
    ("100k MAE -> -1", case_negative_mae, False),
]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    missing = [f for f in FILES if not os.path.exists(os.path.join(OUT, f))]
    if missing:
        print("Cannot run: missing archived inputs:", ", ".join(missing))
        return 1

    os.makedirs(BASE, exist_ok=True)
    print("=== LOTO verifier regression (scratch copies) ===\n")
    all_ok = True
    try:
        for i, (name, mutate, expect_ok) in enumerate(CASES, start=1):
            d = os.path.join(BASE, f"case{i}")
            os.makedirs(d, exist_ok=True)
            for f in FILES:
                shutil.copy2(os.path.join(OUT, f), os.path.join(d, f))
            mutate(d)
            r = subprocess.run([sys.executable, SCRIPT, "verify", "--outdir", d],
                               capture_output=True, text=True, encoding="utf-8")
            got_ok = (r.returncode == 0)
            good = (got_ok == expect_ok)
            all_ok = all_ok and good
            print(f"{'PASS' if good else 'UNEXPECTED':11s} {name:26s} "
                  f"rc={r.returncode}  expected {'0' if expect_ok else 'non-zero'}")
            if not good:
                print("---- verifier output ----")
                print(((r.stdout or "") + (r.stderr or ""))[-1500:])
    finally:
        shutil.rmtree(BASE, ignore_errors=True)

    print("\nREGRESSION:", "ALL AS EXPECTED" if all_ok else "SOME CASES UNEXPECTED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
