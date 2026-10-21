#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Paired leave-one-topology-out sensitivity to non-physical descriptor rows.

For the 100,000-row / 120-tree / seed-42 LOTO run behind Table S8, this script
fits, for each held-out topology:

* historical: all training rows, scored on all test rows (must reproduce the
  archived Table S8 values);
* historical-legal: the same fitted model, scored on the legal test rows;
* cleaned-legal: the same folds, but the non-physical rows (any of the eight
  numeric descriptors < 0) are dropped from the training part only; scored on
  the same legal test rows.

The three variants are paired at the row level.  The historical-all gate fails
closed if the archived Table S8 per-fold MAE/RMSE/R2 is not reproduced.

Outputs:
  outputs/loto_cleaned_per_topology_100k.csv
  outputs/loto_cleaned_aggregates_100k.csv

Usage:
  python scripts/loto_cleaned_sensitivity.py \
    --csv ../../03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv \
    --outdir outputs --workers 4
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "03_投稿专用包", "03_reproduction_package",
    "data", "all_MOFs_screening_data.csv"))
DEFAULT_OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))
TARGET = "CO2_uptake_P0.15bar_T298K [mmol/g]"
NUMERIC = [
    "volume [A^3]", "weight [u]", "surface_area [m^2/g]", "void_fraction",
    "void_volume [cm^3/g]", "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
CATS = ["functional_groups", "metal_linker", "topology"]
GATE_TOL = 1e-6


def build_frame(csv_path, n_rows, seed):
    df = pd.read_csv(csv_path)
    d = df.sample(n_rows, random_state=seed).reset_index(drop=True) if n_rows < len(df) else df.reset_index(drop=True)
    y = pd.to_numeric(d[TARGET], errors="coerce")
    X = d[[c for c in NUMERIC if c in d.columns]].copy().astype(float)
    for c in CATS:
        if c in d.columns:
            X = pd.concat([X, pd.get_dummies(d[c].astype(str), prefix=c).astype(float)], axis=1)
    mask = y.notna() & X.notna().all(axis=1)
    X = X[mask].reset_index(drop=True)
    y = y[mask].reset_index(drop=True)
    d = d.loc[mask].reset_index(drop=True)
    invalid = (d[NUMERIC] < 0).any(axis=1).to_numpy()
    return X, y, d["topology"].astype(str).reset_index(drop=True), invalid


def metrics(yt, pred):
    yt = np.asarray(yt, float)
    pred = np.asarray(pred, float)
    sst = float(((yt - yt.mean()) ** 2).sum())
    sse = float(((yt - pred) ** 2).sum())
    return {
        "n": int(len(yt)),
        "MAE": float(np.abs(yt - pred).mean()),
        "RMSE": float(np.sqrt(((yt - pred) ** 2).mean())),
        "R2": float(1.0 - sse / sst) if len(yt) >= 2 and sst > 0 else float("nan"),
        "SST": sst,
    }


def aggregate(rows, pooled_preds):
    v = [r for r in rows if np.isfinite(r["R2"])]
    n = np.array([r["n"] for r in v], float)
    r2 = np.array([r["R2"] for r in v], float)
    return {
        "pooled": float(1.0 - ((pooled_preds[0] - pooled_preds[1]) ** 2).sum()
                        / ((pooled_preds[0] - pooled_preds[0].mean()) ** 2).sum()),
        "weighted": float((n * r2).sum() / n.sum()) if len(v) else float("nan"),
        "macro": float(r2.mean()) if len(v) else float("nan"),
        "median": float(np.median(r2)) if len(v) else float("nan"),
        "n_valid_folds": int(len(v)),
        "n_total_folds": int(len(rows)),
        "n_covered": int(n.sum()) if len(v) else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--n-rows", type=int, default=100000)
    ap.add_argument("--trees", type=int, default=120)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--groups", default="", help="comma-separated topology subset for a smoke test")
    args = ap.parse_args()

    from sklearn.ensemble import RandomForestRegressor

    X, y, topo, invalid = build_frame(args.csv, args.n_rows, args.seed)
    print(f"modelled rows={len(y):,} features={X.shape[1]} topologies={topo.nunique()} "
          f"non-physical rows={int(invalid.sum())}")
    archived = pd.read_csv(os.path.join(args.outdir, "loto_per_topology_metrics_100k.csv"))
    archived_agg = pd.read_csv(os.path.join(args.outdir, "loto_aggregates_100k.csv")).iloc[0]

    groups = sorted(topo.unique())
    if args.groups:
        wanted = [g.strip() for g in args.groups.split(",") if g.strip()]
        groups = [g for g in groups if g in wanted]

    def run_fold(g):
        te = (topo == g).to_numpy()
        tr = ~te
        te_legal = te & (~invalid)
        tr_clean = tr & (~invalid)
        model_hist = RandomForestRegressor(n_estimators=args.trees, random_state=args.seed, n_jobs=1)
        model_hist.fit(X.iloc[tr], y.iloc[tr])
        pred_all = model_hist.predict(X.iloc[te])
        pred_hist_legal = model_hist.predict(X.iloc[te_legal])
        model_clean = RandomForestRegressor(n_estimators=args.trees, random_state=args.seed, n_jobs=1)
        model_clean.fit(X.iloc[tr_clean], y.iloc[tr_clean])
        pred_clean = model_clean.predict(X.iloc[te_legal])
        yt_all = y.iloc[te].to_numpy(float)
        yt_legal = y.iloc[te_legal].to_numpy(float)
        return {
            "group": g,
            "n_train_hist": int(tr.sum()), "n_train_clean": int(tr_clean.sum()),
            "n_test_all": int(te.sum()), "n_test_legal": int(te_legal.sum()),
            "n_nonphysical_test": int((te & invalid).sum()),
            "hist_all": metrics(yt_all, pred_all),
            "hist_legal": metrics(yt_legal, pred_hist_legal),
            "clean_legal": metrics(yt_legal, pred_clean),
            "pred_hist_legal": pred_hist_legal, "yt_legal": yt_legal,
            "pred_clean": pred_clean,
        }

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(run_fold, groups))

    # Gate historical-all against Table S8.
    for r in results:
        a = archived[archived.group == r["group"]]
        if len(a) != 1:
            raise SystemExit(f"archived row missing for {r['group']}")
        a = a.iloc[0]
        for col in ("MAE", "RMSE", "R2"):
            if abs(r["hist_all"][col] - float(a[col])) > GATE_TOL:
                raise SystemExit(f"gate failed {r['group']} {col}: {r['hist_all'][col]} vs {a[col]}")
    print("per-fold historical gate: OK")
    print(f"archived aggregates: pooled={archived_agg['pooled']:+.6f} "
          f"weighted={archived_agg['weighted']:+.6f} macro={archived_agg['macro']:+.6f} "
          f"median={archived_agg['median']:+.6f}")

    per_fold = []
    for r in results:
        row = {"seed": args.seed, "group": r["group"],
               "n_train_hist": r["n_train_hist"], "n_train_clean": r["n_train_clean"],
               "n_test_all": r["n_test_all"], "n_test_legal": r["n_test_legal"],
               "n_nonphysical_test": r["n_nonphysical_test"]}
        for label in ("hist_all", "hist_legal", "clean_legal"):
            for k, v in r[label].items():
                row[f"{label}_{k}"] = v
        per_fold.append(row)
    per = pd.DataFrame(per_fold)
    per.to_csv(os.path.join(args.outdir, "loto_cleaned_per_topology_100k.csv"),
               index=False, encoding="utf-8-sig")

    # Aggregates: historical-all (gate), historical-legal, cleaned-legal.
    variants = {}
    for label in ("hist_all", "hist_legal", "clean_legal"):
        rows = [dict(r[label], group=r["group"]) for r in results]
        yt = np.concatenate([r["yt_legal"] for r in results])
        # For hist_all pooled, use all-test predictions; recompute in run_fold would
        # need storing them; use the archived pooled value as the gate and skip a
        # duplicate all-test pooled here.
        if label == "hist_all":
            variants[label] = {"pooled": float(archived_agg["pooled"]),
                               "weighted": float(archived_agg["weighted"]),
                               "macro": float(archived_agg["macro"]),
                               "median": float(archived_agg["median"]),
                               "n_valid_folds": int(archived_agg["n_valid_folds"]),
                               "n_total_folds": int(archived_agg["n_total_folds"]),
                               "n_covered": int(archived_agg["n_covered"])}
            continue
        pred = np.concatenate([r["pred_hist_legal" if label == "hist_legal" else "pred_clean"]
                               for r in results])
        variants[label] = aggregate(rows, (yt, pred))
    agg = pd.DataFrame([dict(seed=args.seed, variant=k, **v) for k, v in variants.items()])
    agg = agg[["seed", "variant", "pooled", "weighted", "macro", "median",
               "n_valid_folds", "n_total_folds", "n_covered"]]
    agg.to_csv(os.path.join(args.outdir, "loto_cleaned_aggregates_100k.csv"),
               index=False, encoding="utf-8-sig")
    print("\naggregates:")
    print(agg.to_string(index=False))
    print("\nwrote loto_cleaned_per_topology_100k.csv and loto_cleaned_aggregates_100k.csv")


if __name__ == "__main__":
    main()
