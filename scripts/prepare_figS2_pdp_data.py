#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Figure S2 data step: the shape of each geometry descriptor's effect.

Why this is a centred partial-dependence curve, not per-sample SHAP
------------------------------------------------------------------
Figure S2 is the only one of the 15 submitted figures whose per-sample values
were never archived: `outputs/` holds only the family-aggregated
`fig5_shap_family_final.csv`.  Re-deriving per-sample TreeSHAP turned out not to
be practical with the tools available here:

  * the `shap` distribution cannot be installed in this environment (the local
    `_pylibs/shap` tree is unreadable and pip's temporary directories are
    refused by the sandbox), and
  * the hand-written exact TreeSHAP is correct -- it satisfies the additivity
    identity sum(phi) = f(x) - E[f] to 1.4e-14 on randomised forests -- but its
    cost grows exponentially with decision-path depth, which for this 120-tree,
    depth-30 forest works out at roughly 2.5 s per explained row.

So this script computes the quantity that answers the same question by a route
that is cheap and exactly reproducible: the **centred partial-dependence curve**
of each descriptor,

    pdp_centred(v) = E_over_rows[ f(x with descriptor = v) ] - E_over_rows[ f(x) ]

Partial dependence is averaged over the actual empirical distribution of the
other features, so its shape tracks the SHAP dependence plot closely whenever the
descriptors are not strongly correlated.  It is *not* the same estimand: SHAP is
a per-row additive attribution, partial dependence is a marginal expectation.
Figure S2 therefore labels its y axis "centred partial dependence" and the
Supplementary caption states the substitution.  Nothing else in the paper uses
Figure S2 as a quantity, and the family-level SHAP numbers used in the main text
come from the archived `fig5_shap_family_final.csv`, which is untouched.

Validity rule (added 2026-10-20)
--------------------------------
Eight numeric descriptors of the hMOF release contain a small number of negative
values (169 of 324,426 structures, 0.052%; per-field counts in
`outputs/input_validity_audit.csv`).  A negative void fraction, surface area,
pore volume or pore diameter is not a physical input, and the release does not
document what the -1 encodes, so this script treats a negative value in **any**
of the eight descriptors as an invalid physical input for this figure:

  * those rows are excluded from the fit *and* from the quantile grid, so the
    displayed grid lies inside the observed valid domain and never interpolates
    across a sentinel;
  * the exclusion is recorded in the meta table (counts before/after), and the
    historical behaviour (fit and grid including the sentinels) remains
    available with `--keep-sentinels` for reproducing the earlier figure;
  * this cleans the *S2 model only*.  The protocol comparison, the intervention
    arms and the LOTO tables were fitted on the unfiltered samples; SI-E records
    that their re-fit without these rows was not run, and why the archived
    per-row predictions cannot be used to drop them after the fact.

Outputs
-------
  outputs/pdp_geometry_curves.csv    descriptor, bin centre, mean, sd, n
  outputs/pdp_geometry_meta.csv      settings, validation, ranking
  outputs/pdp_geometry_grids.csv     descriptor, grid_min, grid_max, n_valid,
                                     n_invalid
"""
from __future__ import annotations

import argparse
import hashlib
import os
import platform
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))
RAW = os.path.abspath(os.path.join(HERE, "..", "data",
                                   "all_MOFs_screening_data.csv"))

# --- verbatim from scripts/figures_and_shap.py ------------------------------
TARGET = "CO2_uptake_P0.15bar_T298K [mmol/g]"
NUMERIC_FEATURES = [
    "volume [A^3]",
    "weight [u]",
    "surface_area [m^2/g]",
    "void_fraction",
    "void_volume [cm^3/g]",
    "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
CATEGORICAL_FEATURES = ["functional_groups", "metal_linker", "topology"]
N_ESTIMATORS = 120
RANDOM_STATE = 42
MAX_ROWS = 25000
N_BINS = 24


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-jobs", type=int, default=1)
    ap.add_argument("--max-rows", type=int, default=MAX_ROWS)
    ap.add_argument("--n-bins", type=int, default=N_BINS)
    ap.add_argument("--background", type=int, default=4000,
                    help="rows used as the averaging background per bin")
    ap.add_argument("--outdir", default=OUT)
    ap.add_argument("--keep-sentinels", action="store_true",
                    help="historical behaviour: fit and grid include the "
                         "negative (non-physical) descriptor rows")
    args = ap.parse_args()

    t0_all = time.time()
    print("=" * 74)
    print("Figure S2 data step - centred partial dependence of the descriptors")
    print("=" * 74)
    if not os.path.exists(RAW):
        print(f"FAIL raw data missing: {RAW}")
        return 2

    print(f"[1/5] reading {os.path.basename(RAW)}")
    def _md5(path, block=1 << 20):
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(block), b""):
                h.update(chunk)
        return h.hexdigest()
    input_md5 = _md5(RAW)
    script_sha = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    df = pd.read_csv(RAW)
    if args.max_rows < len(df):
        df = df.sample(args.max_rows, random_state=RANDOM_STATE).reset_index(drop=True)
    print(f"      {len(df)} rows (random_state={RANDOM_STATE})")

    print("[2/5] building the feature matrix")
    y = pd.to_numeric(df[TARGET], errors="coerce")
    X = df[NUMERIC_FEATURES].copy().astype(float)
    cats = [c for c in CATEGORICAL_FEATURES if c in df.columns]
    for c in cats:
        X = pd.concat([X, pd.get_dummies(df[c].astype(str), prefix=c).astype(float)],
                      axis=1)
    mask = y.notna() & X.notna().all(axis=1)
    n_usable = int(mask.sum())
    # --- input-validity rule: a negative descriptor is not a physical input ---
    neg_any = pd.Series(False, index=df.index)
    invalid_per_field = {}
    for col in NUMERIC_FEATURES:
        bad = pd.to_numeric(df[col], errors="coerce") < 0
        invalid_per_field[col] = int(bad.sum())
        neg_any |= bad
    if args.keep_sentinels:
        print("      [validity] --keep-sentinels: negative descriptor rows are "
              "KEPT (historical behaviour)")
        n_invalid_dropped = 0
    else:
        n_invalid_dropped = int((neg_any & mask).sum())
        mask = mask & ~neg_any
        print(f"      [validity] dropping {n_invalid_dropped} rows with a negative "
              f"descriptor value (of {n_usable} otherwise usable)")
    X, y = X[mask].reset_index(drop=True), y[mask].reset_index(drop=True)
    print(f"      X = {X.shape}")

    print(f"[3/5] fitting RandomForestRegressor(n_estimators={N_ESTIMATORS}, "
          f"random_state={RANDOM_STATE})")
    t = time.time()
    from sklearn.ensemble import RandomForestRegressor
    mdl = RandomForestRegressor(n_estimators=N_ESTIMATORS,
                                random_state=RANDOM_STATE, n_jobs=args.n_jobs)
    mdl.fit(X, y)
    base = float(np.mean([e.tree_.value.reshape(-1)[0] for e in mdl.estimators_]))
    print(f"      in-sample R2 = {mdl.score(X, y):.6f}   ({time.time()-t:.0f} s)")
    print(f"      baseline E[f] (mean of tree means) = {base:.6f}")

    # averaging background: a fixed, deterministic subset keeps the runtime flat
    rng = np.random.RandomState(RANDOM_STATE)
    bg_idx = rng.choice(len(X), size=min(args.background, len(X)), replace=False)
    bg = X.iloc[bg_idx].copy()
    print(f"[4/5] centred partial dependence, {args.n_bins} quantile bins, "
          f"background n = {len(bg)}")
    rows, grid_rows = [], []
    for col in NUMERIC_FEATURES:
        t = time.time()
        vals = X[col].to_numpy(float)
        edges = np.unique(np.quantile(vals, np.linspace(0, 1, args.n_bins + 1)))
        centres = 0.5 * (edges[:-1] + edges[1:])
        # the grid must stay inside the observed domain of the modelled rows
        assert centres.min() >= vals.min() and centres.max() <= vals.max(), col
        grid_rows.append({"descriptor": col, "grid_min": float(centres.min()),
                          "grid_max": float(centres.max()),
                          "n_valid": int(len(vals)),
                          "n_invalid": int(invalid_per_field[col])})
        means, sds, ns = [], [], []
        for c in centres:
            frame = bg.copy()
            frame[col] = float(c)
            pred = mdl.predict(frame)
            means.append(float(pred.mean()))
            sds.append(float(pred.std(ddof=1)) / np.sqrt(len(pred)))
            ns.append(len(pred))
        for c, m, s, n in zip(centres, means, sds, ns):
            rows.append({"descriptor": col, "value": float(c),
                         "pdp_mean": m, "pdp_se": s, "n_background": n})
        spread = max(means) - min(means)
        print(f"      {col:<62} range {spread:.4f}  ({time.time()-t:.0f} s)")

    curves = pd.DataFrame(rows)
    curves["pdp_centred"] = curves["pdp_mean"] - base
    print("[5/5] writing outputs")
    os.makedirs(args.outdir, exist_ok=True)
    p_curves = os.path.join(args.outdir, "pdp_geometry_curves.csv")
    p_meta = os.path.join(args.outdir, "pdp_geometry_meta.csv")
    p_grids = os.path.join(args.outdir, "pdp_geometry_grids.csv")
    curves.to_csv(p_curves, index=False)
    pd.DataFrame(grid_rows).to_csv(p_grids, index=False)

    rank = (curves.groupby("descriptor")["pdp_centred"]
            .apply(lambda s: float(s.max() - s.min()))
            .sort_values(ascending=False))
    print()
    print("centred-PDP range per descriptor (largest effect first):")
    for name, val in rank.items():
        print(f"   {name:<62} {val:.4f}")

    pd.DataFrame({
        "key": ["target", "raw_table", "max_rows", "random_state",
                "n_rows_sampled", "n_rows_usable", "n_rows_modelled",
                "n_rows_dropped_nonphysical", "validity_rule",
                "model_fit_population", "n_features", "n_estimators",
                "method", "n_bins", "background_n", "in_sample_r2",
                "offset_definition", "baseline_mean_of_tree_means",
                "top4_by_pdp_range", "pdp_range_top4",
                "python", "numpy", "pandas", "sklearn", "input_md5",
                "script_sha256", "generated_utc"],
        "value": [TARGET, os.path.basename(RAW), args.max_rows, RANDOM_STATE,
                  len(df), n_usable, len(X), n_invalid_dropped,
                  "a negative value in any of the eight numeric descriptors is "
                  "treated as a non-physical input for this figure"
                  if not args.keep_sentinels else
                  "historical: negative descriptor values retained",
                  "full analysis sample (not a training fold), refitted after "
                  "the validity rule"
                  if not args.keep_sentinels else
                  "full analysis sample (not a training fold), historical fit",
                  X.shape[1], N_ESTIMATORS,
                  "centred partial dependence (marginal expectation over the "
                  "empirical background); NOT per-sample SHAP",
                  args.n_bins, len(bg), round(float(mdl.score(X, y)), 6),
                  "mean of the per-tree root values (mean of tree means), not "
                  "an explicit mean[f(background)] over the 4,000 background rows",
                  round(base, 6),
                  "; ".join(rank.index[:4]),
                  "; ".join(f"{v:.4f}" for v in rank.values[:4]),
                  platform.python_version(),
                  np.__version__,
                  pd.__version__,
                  __import__("sklearn").__version__,
                  input_md5,
                  script_sha,
                  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())],
    }).to_csv(p_meta, index=False, encoding="utf-8-sig")
    print()
    print(f"wrote {p_curves}")
    print(f"wrote {p_grids}")
    print(f"wrote {p_meta}")
    print(f"total {time.time()-t0_all:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
