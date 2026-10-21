#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Recompute per-fold metrics and the four LOTO aggregations for SI Tables S8/S9.

The archived `loto_per_topology_final.csv` stores only `group, n_test, R2`, so per-fold
MAE/RMSE and the `weighted` aggregate were never archived and cannot be inverted from R2.
This script re-runs the same leave-one-topology-out protocol and records the missing
columns. It trains random forests, so it is the one reproduction step that fits models.

Modes
-----
  recompute --csv PATH [--outdir outputs]
      100,000-row sample, 120 trees, seed 42, leave-one-topology-out (11 folds).
      Writes outputs/loto_per_topology_metrics_100k.csv and outputs/loto_aggregates_100k.csv.

  recompute25k --csv PATH [--outdir outputs]
      25,000-row sample, 100 trees, five seeds (42/143/244/345/446), LOTO (11 folds each).
      Writes outputs/loto_per_topology_metrics_25k.csv and outputs/loto_aggregates_25k.csv.

  verify [--outdir outputs]
      Read-only. Checks the recomputed per-fold R2 against the archived
      `loto_per_topology_final.csv` and the archived aggregations in `metrics_audit.csv`.

`--n-jobs` defaults to -1 (all cores). A confined sandbox that denies named pipes cannot
start joblib's worker pools, so in such an environment pass `--n-jobs 1`; results are
identical because the forest's random_state is fixed, but single-threaded is ~10x slower
(measured: about 10 min per 100k fold, so ~1.8 h for the 11 folds).

Definitions (stated so they can be checked):
  MAE   = mean(|y - yhat|) over the fold's test rows.
  RMSE  = sqrt(mean((y - yhat)^2)).
  R2    = 1 - SSE/SST within the fold, valid only if n_test >= 2 and SST > 0.
  pooled   = R2 over all predictions concatenated against the global mean.
  weighted = sum(n_i * R2_i) / sum(n_i) over VALID folds (n_i = test size); the covered
             sample count is reported alongside.
  macro    = mean of valid-fold R2.
  median   = median of valid-fold R2.
Invalid folds are excluded from weighted/macro/median and are flagged in the metrics table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

TARGET = "CO2_uptake_P0.15bar_T298K [mmol/g]"
NUMERIC = [
    "volume [A^3]", "weight [u]", "surface_area [m^2/g]", "void_fraction",
    "void_volume [cm^3/g]", "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
CATS = ["functional_groups", "metal_linker", "topology"]
SEEDS_25K = [42, 143, 244, 345, 446]

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_OUT = os.path.join(PKG, "outputs")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(csv_path):
    df = pd.read_csv(csv_path)
    print(f"raw: {len(df):,} rows x {df.shape[1]} cols")
    return df


def build_xy(df, n_rows, seed):
    """Match mof_leakage_benchmark: sample, then one-hot features, then drop NaN rows."""
    d = df
    if n_rows < len(d):
        d = d.sample(n_rows, random_state=seed).reset_index(drop=True)
    y = pd.to_numeric(d[TARGET], errors="coerce")
    cols = [c for c in NUMERIC if c in d.columns]
    X = d[cols].copy().astype(float)
    for c in CATS:
        if c in d.columns:
            X = pd.concat(
                [X, pd.get_dummies(d[c].astype(str), prefix=c).astype(float)], axis=1)
    mask = y.notna() & X.notna().all(axis=1)
    return (X[mask].reset_index(drop=True),
            y[mask].reset_index(drop=True),
            d.loc[mask, "topology"].astype(str).reset_index(drop=True))


def loto_folds(X, y, topo, seed, n_trees, n_jobs=-1):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import r2_score

    rows, all_true, all_pred = [], [], []
    for g in sorted(topo.unique()):
        te = (topo == g).to_numpy()
        tr = ~te
        mdl = RandomForestRegressor(n_estimators=n_trees, random_state=seed, n_jobs=n_jobs)
        mdl.fit(X.iloc[tr], y.iloc[tr])
        pred = mdl.predict(X.iloc[te])
        yt = y.iloc[te].to_numpy(float)
        n = int(len(yt))
        sst = float(((yt - yt.mean()) ** 2).sum())
        sse = float(((yt - pred) ** 2).sum())
        valid = bool(n >= 2 and sst > 0)
        all_true.extend(yt.tolist())
        all_pred.extend(pred.tolist())
        rows.append({
            "group": g, "n_train": int(tr.sum()), "n_test": n,
            "MAE": float(np.abs(yt - pred).mean()),
            "RMSE": float(np.sqrt(((yt - pred) ** 2).mean())),
            "R2": float(r2_score(yt, pred)) if valid else float("nan"),
            "SSE": sse, "SST": sst, "valid_R2": valid,
        })
        print(f"    {g:>4s} n_test={n:6d} MAE={rows[-1]['MAE']:.4f} "
              f"RMSE={rows[-1]['RMSE']:.4f} R2={rows[-1]['R2']:+.4f} valid={valid}")
    pooled = float(r2_score(all_true, all_pred))
    return pd.DataFrame(rows), pooled


def aggregate(rows, pooled):
    v = rows[rows.valid_R2]
    n = v.n_test.to_numpy(float)
    r2 = v.R2.to_numpy(float)
    return {
        "pooled": pooled,
        "weighted": float((n * r2).sum() / n.sum()),
        "macro": float(r2.mean()),
        "median": float(np.median(r2)),
        "n_valid_folds": int(len(v)),
        "n_covered": int(n.sum()),
        "n_total_folds": int(len(rows)),
    }


def recompute(csv_path, outdir, n_rows, n_trees, seeds, tag, n_jobs=-1):
    df = load_raw(csv_path)
    per_seed, agg_rows = [], []
    for seed in seeds:
        print(f"\n=== seed {seed} (n={n_rows:,}, {n_trees} trees) ===")
        X, y, topo = build_xy(df, n_rows, seed)
        print(f"  modelled rows: {len(y):,}  features: {X.shape[1]}  topologies: {topo.nunique()}")
        rows, pooled = loto_folds(X, y, topo, seed, n_trees, n_jobs)
        rows.insert(0, "seed", seed)
        per_seed.append(rows)
        agg = aggregate(rows, pooled)
        agg["seed"] = seed
        agg_rows.append(agg)
        print(f"  aggregates: pooled={agg['pooled']:+.4f} weighted={agg['weighted']:+.4f} "
              f"macro={agg['macro']:+.4f} median={agg['median']:+.4f} "
              f"valid={agg['n_valid_folds']}/{agg['n_total_folds']}")

    os.makedirs(outdir, exist_ok=True)
    mpath = os.path.join(outdir, f"loto_per_topology_metrics_{tag}.csv")
    apath = os.path.join(outdir, f"loto_aggregates_{tag}.csv")
    pd.concat(per_seed).to_csv(mpath, index=False, encoding="utf-8-sig")
    agg_df = pd.DataFrame(agg_rows)[
        ["seed", "pooled", "weighted", "macro", "median",
         "n_valid_folds", "n_total_folds", "n_covered"]]
    agg_df.to_csv(apath, index=False, encoding="utf-8-sig")
    print(f"\nwrote {mpath}")
    print(f"wrote {apath}")
    return agg_df


def _fold_arithmetic(df, label):
    """Internal consistency of one per-fold table.

    Checks, all of which must hold for the recorded numbers to describe the same
    predictions: RMSE^2 * n_test == SSE; for valid folds R2 == 1 - SSE/SST;
    MAE <= RMSE; error metrics and sums of squares non-negative; the valid_R2
    flag matches its own definition (n_test >= 2 and SST > 0); and n_test /
    n_train positive.
    """
    ok = True
    v = df.copy()
    v["rmse_from_sse"] = np.sqrt(v.SSE / v.n_test)
    v["r2_from_sse"] = 1.0 - v.SSE / v.SST
    d_rmse = float(np.max(np.abs(v.rmse_from_sse - v.RMSE)))
    print(f"{label}: max |sqrt(SSE/n) - RMSE| = {d_rmse:.2e}")
    ok = ok and d_rmse <= 1e-8

    # the flag must follow the stated definition, not merely be taken on trust
    expected_valid = (v.n_test >= 2) & (v.SST > 0)
    valid_ok = bool((v.valid_R2.astype(bool) == expected_valid).all())
    print(f"{label}: valid_R2 matches n_test/SST definition = {valid_ok}")
    ok = ok and valid_ok

    vv = v[v.valid_R2]
    d_r2 = float(np.max(np.abs(vv.r2_from_sse - vv.R2))) if len(vv) else 0.0
    print(f"{label}: max |1 - SSE/SST - R2| over valid folds = {d_r2:.2e}")
    ok = ok and d_r2 <= 1e-8

    mae_le_rmse = bool((v.MAE <= v.RMSE + 1e-12).all())
    print(f"{label}: MAE <= RMSE on every fold = {mae_le_rmse}")
    ok = ok and mae_le_rmse

    nonnegative = bool(
        (v.MAE >= 0).all() and (v.RMSE >= 0).all()
        and (v.SSE >= 0).all() and (v.SST >= 0).all())
    print(f"{label}: error metrics and sums of squares nonnegative = {nonnegative}")
    ok = ok and nonnegative

    pos = bool((v.n_test > 0).all() and (v.n_train > 0).all())
    print(f"{label}: n_test and n_train positive = {pos}")
    ok = ok and pos
    return ok


def _reaggregate(folds):
    """Recompute weighted/macro/median and coverage from a per-fold table."""
    v = folds[folds.valid_R2]
    n = v.n_test.to_numpy(float)
    r2 = v.R2.to_numpy(float)
    return {
        "weighted": float((n * r2).sum() / n.sum()),
        "macro": float(r2.mean()),
        "median": float(np.median(r2)),
        "n_valid_folds": int(len(v)),
        "n_covered": int(n.sum()),
    }


def verify(outdir):
    need = ["loto_per_topology_metrics_100k.csv", "loto_aggregates_100k.csv",
            "loto_per_topology_metrics_25k.csv", "loto_aggregates_25k.csv"]
    missing = [f for f in need if not os.path.exists(os.path.join(outdir, f))]
    if missing:
        print("Cannot verify yet; missing:", ", ".join(missing))
        print("Run `recompute` and `recompute25k` first.")
        return False
    ok = True

    # --- Table S8: 100k per-fold R2 and pooled/weighted/macro/median ---
    m = pd.read_csv(os.path.join(outdir, "loto_per_topology_metrics_100k.csv"))
    a = pd.read_csv(os.path.join(outdir, "loto_aggregates_100k.csv"))
    dup = int(m.group.duplicated().sum())
    print(f"100k per-fold table: {len(m)} rows, duplicate group keys = {dup}")
    ok = ok and (len(m) == 11 and dup == 0)
    arithmetic_ok = _fold_arithmetic(m, "100k folds")
    ok = ok and arithmetic_ok
    # recompute the three fold-score aggregates from the per-fold table itself
    ra = _reaggregate(m)
    for col in ("weighted", "macro", "median"):
        same = abs(ra[col] - float(a[col].iloc[0])) <= 1e-9
        print(f"100k {col} rebuilt from per-fold table: {same}")
        ok = ok and same
    for col in ("n_valid_folds", "n_covered"):
        same = int(ra[col]) == int(a[col].iloc[0])
        print(f"100k {col} rebuilt from per-fold table: {same}")
        ok = ok and same

    # archived reference files always live in the package outputs directory
    ref = pd.read_csv(os.path.join(DEFAULT_OUT, "loto_per_topology_final.csv"))
    j = m.merge(ref, on="group", suffixes=("_new", "_ref"))
    if len(j) != len(ref):
        print(f"FAIL: fold count mismatch ({len(j)} vs {len(ref)})")
        ok = False
    else:
        r2_ok = np.allclose(j.R2_new, j.R2_ref, rtol=1e-6, atol=1e-9)
        n_ok = (j.n_test_new == j.n_test_ref).all()
        print(f"per-fold R2 matches archived loto_per_topology_final.csv: {r2_ok}")
        print(f"per-fold n_test matches: {n_ok}")
        ok = ok and bool(r2_ok and n_ok)

    ma = pd.read_csv(os.path.join(DEFAULT_OUT, "metrics_audit.csv"))
    row = ma[ma.result.str.strip() == "LOTO / topology (100k)"].iloc[0]
    # metrics_audit stores the pooled value under `pooled_as_reported`
    colmap = {"pooled": "pooled_as_reported", "weighted": "weighted",
              "macro": "macro", "median": "median"}
    for col, src in colmap.items():
        got = float(a[col].iloc[0])
        want = float(row[src])
        same = abs(got - want) <= 1e-6
        print(f"aggregate {col}: recomputed={got:+.6f} archived={want:+.6f} match={same}")
        ok = ok and same

    # --- Table S9: 25k five-seed weighted ---
    m25 = pd.read_csv(os.path.join(outdir, "loto_per_topology_metrics_25k.csv"))
    a25 = pd.read_csv(os.path.join(outdir, "loto_aggregates_25k.csv"))
    dup25 = int(m25.duplicated(["seed", "group"]).sum())
    print(f"25k per-fold table: {len(m25)} rows, duplicate (seed, group) keys = {dup25}")
    ok = ok and (len(m25) == 55 and dup25 == 0)
    arithmetic_ok = _fold_arithmetic(m25, "25k folds")
    ok = ok and arithmetic_ok
    # rebuild each seed's weighted/macro/median/coverage from its own folds
    rebuilt = []
    for seed, g in m25.groupby("seed"):
        r = _reaggregate(g)
        r["seed"] = seed
        rebuilt.append(r)
    rb = pd.DataFrame(rebuilt).sort_values("seed").reset_index(drop=True)
    cmp_cols = ["weighted", "macro", "median"]
    same_w = np.allclose(rb[cmp_cols].to_numpy(),
                         a25.sort_values("seed")[cmp_cols].to_numpy(),
                         rtol=1e-12, atol=1e-12)
    same_n = (rb.n_valid_folds.to_numpy() == a25.sort_values("seed").n_valid_folds.to_numpy()).all() \
        and (rb.n_covered.to_numpy() == a25.sort_values("seed").n_covered.to_numpy()).all()
    print(f"25k weighted/macro/median rebuilt from per-fold table: {same_w}")
    print(f"25k valid-fold count and covered rows rebuilt: {same_n}")
    ok = ok and bool(same_w and same_n)

    ref25 = pd.read_csv(os.path.join(DEFAULT_OUT, "multi_seed_uptake25k_fix.csv"))
    j25 = a25.merge(ref25[["seed", "loto_pooled", "loto_macro", "loto_median",
                           "loto_n_valid_folds"]], on="seed")
    print(f"25k seeds matched: {len(j25)}/5")
    if len(j25) != 5:
        ok = False
    else:
        p_ok = np.allclose(j25.pooled, j25.loto_pooled, rtol=1e-6, atol=1e-9)
        m_ok = np.allclose(j25.macro, j25.loto_macro, rtol=1e-4, atol=1e-6)
        d_ok = np.allclose(j25["median"], j25.loto_median, rtol=1e-6, atol=1e-9)
        v_ok = (j25.n_valid_folds == j25.loto_n_valid_folds).all()
        print(f"25k pooled match={p_ok} macro match={m_ok} median match={d_ok} validfold match={v_ok}")
        ok = ok and bool(p_ok and m_ok and d_ok and v_ok)

    print("\nverify:", "OK" if ok else "FAILED")
    return ok


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r1 = sub.add_parser("recompute")
    r1.add_argument("--csv", required=True)
    r1.add_argument("--outdir", default=DEFAULT_OUT)
    r1.add_argument("--n-jobs", type=int, default=-1)
    r2 = sub.add_parser("recompute25k")
    r2.add_argument("--csv", required=True)
    r2.add_argument("--outdir", default=DEFAULT_OUT)
    r2.add_argument("--n-jobs", type=int, default=-1)
    v = sub.add_parser("verify")
    v.add_argument("--outdir", default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.cmd == "recompute":
        recompute(args.csv, args.outdir, 100_000, 120, [42], "100k", args.n_jobs)
    elif args.cmd == "recompute25k":
        recompute(args.csv, args.outdir, 25_000, 100, SEEDS_25K, "25k", args.n_jobs)
    else:
        sys.exit(0 if verify(args.outdir) else 1)


if __name__ == "__main__":
    main()
