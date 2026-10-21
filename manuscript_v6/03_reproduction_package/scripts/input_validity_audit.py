#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Archive the input-validity audit behind SI-A / SI-E (review 2026-10-20, §9.1).

Why
---
Eight numeric descriptors in the hMOF release contain a small number of negative
values (for example void_fraction = -1 and surface_area = -1).  A negative void
fraction or surface area is not a physical input, but the release does not say
whether the value is a sentinel, a failed calculation, or something else.  The
paper therefore has to do three things, and this script does all three:

  1. report the per-field counts (missing / negative / zero) and the union mask,
     so the size of the problem is a number rather than an assurance;
  2. report how many of those rows land in each analysis sample (25k / 50k /
     100k, every seed), because a 0.05% database-level rate can be larger in a
     small sample;
  3. re-run the *model-free* support audit with and without the affected rows,
     so the structural headline (74.7% / 61.3% / 82.0%) has a sensitivity check.
     Model-based endpoints are not refitted here (see the note in the SI).

    python scripts/input_validity_audit.py \
        --hmof ../path/to/all_MOFs_screening_data.csv \
        --out outputs/input_validity_audit.csv

Output rows are (check, field, scope, metric, value) so that a reader can grep a
single line instead of parsing a wide table.  No row is dropped from the
archived analysis by this script; it only measures.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PKG / "outputs" / "input_validity_audit.csv"

NUMERIC = [
    "volume [A^3]",
    "weight [u]",
    "surface_area [m^2/g]",
    "void_fraction",
    "void_volume [cm^3/g]",
    "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
TARGET = "CO2_uptake_P0.15bar_T298K [mmol/g]"
KEYS = ["metal_linker", "organic_linker1", "organic_linker2"]
SEEDS = [42, 143, 244, 345, 446]
SAMPLE_SIZES = [25_000, 50_000, 100_000]


def _entropy(values) -> float:
    counts = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    n = float(sum(counts.values()))
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def main() -> int:
    import numpy as np
    import pandas as pd

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hmof", required=True)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    df = pd.read_csv(args.hmof, usecols=NUMERIC + [TARGET, "topology"] + KEYS)
    n_all = len(df)
    rows = []
    add = rows.append

    # ---- 1. per-field validity -------------------------------------------
    for col in NUMERIC + [TARGET]:
        s = pd.to_numeric(df[col], errors="coerce")
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="n", value=n_all))
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="n_missing", value=int(s.isna().sum())))
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="n_negative", value=int((s < 0).sum())))
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="n_zero", value=int((s == 0).sum())))
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="min", value=float(s.min())))
        add(dict(check="field_validity", field=col, scope="full_database",
                 metric="max", value=float(s.max())))

    neg_any = pd.Series(False, index=df.index)
    for col in NUMERIC:
        neg_any |= pd.to_numeric(df[col], errors="coerce") < 0
    n_neg = int(neg_any.sum())
    add(dict(check="union_mask", field="|".join(NUMERIC), scope="full_database",
             metric="n_negative_union", value=n_neg))
    add(dict(check="union_mask", field="|".join(NUMERIC), scope="full_database",
             metric="share_of_rows", value=round(100.0 * n_neg / n_all, 4)))

    # where the affected rows sit
    for topo, k in df.loc[neg_any, "topology"].value_counts().items():
        add(dict(check="union_mask_by_topology", field=str(topo),
                 scope="full_database", metric="n_negative", value=int(k)))

    # ---- 2. how many affected rows land in each analysis sample ----------
    for size in SAMPLE_SIZES:
        seeds = SEEDS if size == 25_000 else [42]
        for seed in seeds:
            samp = df.sample(size, random_state=seed)
            k = int(neg_any.loc[samp.index].sum())
            add(dict(check="sample_incidence", field=f"n{size}_seed{seed}",
                     scope="analysis_sample", metric="n_rows", value=size))
            add(dict(check="sample_incidence", field=f"n{size}_seed{seed}",
                     scope="analysis_sample", metric="n_negative", value=k))
            add(dict(check="sample_incidence", field=f"n{size}_seed{seed}",
                     scope="analysis_sample", metric="share_of_rows",
                     value=round(100.0 * k / size, 4)))
        del samp

    # ---- 3. model-free support audit, with and without the affected rows --
    comp = df[KEYS].fillna("NA").astype(str).agg("|".join, axis=1)
    for label, mask in (("all_rows", pd.Series(True, index=df.index)),
                        ("excluding_negative_descriptors", ~neg_any)):
        d = df[mask]
        c = comp[mask]
        frame = pd.DataFrame({"c": c, "t": d["topology"].astype(str)})
        n = len(frame)
        marg = frame.groupby("c").size()
        joint = frame.groupby(["c", "t"]).size()
        n_topo = frame.groupby("c")["t"].nunique()
        singleton = n_topo == 1
        h_t = _entropy(frame["t"].tolist())
        h_c = _entropy(c.tolist())
        h_joint = _entropy([a + "||" + b for a, b in zip(c, frame["t"])])
        h_t_given_c = h_joint - h_c
        single_comp = float(singleton.mean())
        # structure-level: share of structures whose composition is single-topology
        single_struct = float(singleton[marg.index].reindex(c).to_numpy().mean())
        add(dict(check="support_audit_sensitivity", field=label, scope="full_database",
                 metric="n_rows", value=n))
        add(dict(check="support_audit_sensitivity", field=label, scope="full_database",
                 metric="n_compositions", value=int(len(marg))))
        add(dict(check="support_audit_sensitivity", field=label, scope="full_database",
                 metric="single_topology_by_composition",
                 value=round(100.0 * single_comp, 6)))
        add(dict(check="support_audit_sensitivity", field=label, scope="full_database",
                 metric="single_topology_by_structure",
                 value=round(100.0 * single_struct, 6)))
        add(dict(check="support_audit_sensitivity", field=label, scope="full_database",
                 metric="H_T_given_C_over_H_T",
                 value=round(h_t_given_c / h_t, 6)))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=["check", "field", "scope", "metric", "value"]).to_csv(
        out, index=False)
    print(f"wrote {out}  ({len(rows)} rows, {n_all:,} structures)")
    print(f"negative-descriptor rows: {n_neg} ({100.0 * n_neg / n_all:.4f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
