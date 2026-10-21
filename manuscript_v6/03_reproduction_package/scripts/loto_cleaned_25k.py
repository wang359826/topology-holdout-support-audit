#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Paired 25k five-seed LOTO sensitivity to non-physical descriptor rows.

Mirrors `loto_full_metrics.py recompute25k` (25,000 rows, 100 trees, five seeds,
leave-one-topology-out) but, for each fold, fits:

* historical: all training rows, scored on all test rows (gate against Table S9);
* historical-legal: same model, scored on legal test rows;
* cleaned-legal: training rows with any negative numeric descriptor removed,
  scored on the same legal test rows.

Outputs:
  outputs/loto_cleaned_per_topology_25k.csv
  outputs/loto_cleaned_aggregates_25k.csv

Usage:
  python scripts/loto_cleaned_25k.py \
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
SEEDS = [42, 143, 244, 345, 446]
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


def aggregate(rows, yt, pred):
    v = [r for r in rows if np.isfinite(r["R2"])]
    n = np.array([r["n"] for r in v], float)
    r2 = np.array([r["R2"] for r in v], float)
    yt = np.asarray(yt, float)
    pred = np.asarray(pred, float)
    sst = float(((yt - yt.mean()) ** 2).sum())
    sse = float(((yt - pred) ** 2).sum())
    return {
        "pooled": float(1.0 - sse / sst) if sst > 0 else float("nan"),
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
    ap.add_argument("--n-rows", type=int, default=25000)
    ap.add_argument("--trees", type=int, default=100)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    args = ap.parse_args()

    from sklearn.ensemble import RandomForestRegressor

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    archived = pd.read_csv(os.path.join(args.outdir, "loto_per_topology_metrics_25k.csv"))
    archived_agg = pd.read_csv(os.path.join(args.outdir, "loto_aggregates_25k.csv")).set_index("seed")
    per_all, agg_all = [], []

    for seed in seeds:
        X, y, topo, invalid = build_frame(args.csv, args.n_rows, seed)
        print(f"\nseed={seed}: rows={len(y):,} features={X.shape[1]} "
              f"topologies={topo.nunique()} non-physical={int(invalid.sum())}")
        groups = sorted(topo.unique())
        arch_seed = archived[archived.seed == seed]

        def run_fold(g):
            te = (topo == g).to_numpy()
            tr = ~te
            te_legal = te & (~invalid)
            tr_clean = tr & (~invalid)
            m_hist = RandomForestRegressor(n_estimators=args.trees, random_state=seed, n_jobs=1)
            m_hist.fit(X.iloc[tr], y.iloc[tr])
            pred_all = m_hist.predict(X.iloc[te])
            pred_hist_legal = m_hist.predict(X.iloc[te_legal])
            m_clean = RandomForestRegressor(n_estimators=args.trees, random_state=seed, n_jobs=1)
            m_clean.fit(X.iloc[tr_clean], y.iloc[tr_clean])
            pred_clean = m_clean.predict(X.iloc[te_legal])
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
                "yt_all": yt_all, "pred_all": pred_all,
                "yt_legal": yt_legal,
                "pred_hist_legal": pred_hist_legal, "pred_clean": pred_clean,
            }

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            results = list(pool.map(run_fold, groups))

        for r in results:
            a = arch_seed[arch_seed.group == r["group"]]
            if len(a) != 1:
                raise SystemExit(f"archived row missing seed={seed} group={r['group']}")
            a = a.iloc[0]
            for col in ("MAE", "RMSE"):
                if abs(r["hist_all"][col] - float(a[col])) > GATE_TOL:
                    raise SystemExit(f"gate failed {seed}/{r['group']} {col}")
            if np.isfinite(a["R2"]) and abs(r["hist_all"]["R2"] - float(a["R2"])) > GATE_TOL:
                raise SystemExit(f"gate failed {seed}/{r['group']} R2")
        print(f"  historical per-fold gate: OK")

        for r in results:
            row = {"seed": seed, "group": r["group"],
                   "n_train_hist": r["n_train_hist"], "n_train_clean": r["n_train_clean"],
                   "n_test_all": r["n_test_all"], "n_test_legal": r["n_test_legal"],
                   "n_nonphysical_test": r["n_nonphysical_test"]}
            for label in ("hist_all", "hist_legal", "clean_legal"):
                for k, v in r[label].items():
                    row[f"{label}_{k}"] = v
            per_all.append(row)

        variants = {}
        yt_all = np.concatenate([r["yt_all"] for r in results])
        pred_all = np.concatenate([r["pred_all"] for r in results])
        variants["hist_all"] = aggregate([dict(r["hist_all"], group=r["group"]) for r in results],
                                         yt_all, pred_all)
        for label, pred_key in (("hist_legal", "pred_hist_legal"), ("clean_legal", "pred_clean")):
            yt = np.concatenate([r["yt_legal"] for r in results])
            pred = np.concatenate([r[pred_key] for r in results])
            variants[label] = aggregate([dict(r[label], group=r["group"]) for r in results], yt, pred)

        # Gate the historical-all aggregates against Table S9.
        a = archived_agg.loc[seed]
        for col in ("pooled", "weighted", "macro", "median"):
            if abs(variants["hist_all"][col] - float(a[col])) > GATE_TOL:
                raise SystemExit(f"aggregate gate failed seed={seed} {col}: "
                                 f"{variants['hist_all'][col]} vs {a[col]}")
        print("  historical aggregate gate: OK")
        for k, v in variants.items():
            agg_all.append(dict(seed=seed, variant=k, **v))

    per = pd.DataFrame(per_all)
    per.to_csv(os.path.join(args.outdir, "loto_cleaned_per_topology_25k.csv"),
               index=False, encoding="utf-8-sig")
    agg = pd.DataFrame(agg_all)[[
        "seed", "variant", "pooled", "weighted", "macro", "median",
        "n_valid_folds", "n_total_folds", "n_covered"]]
    agg.to_csv(os.path.join(args.outdir, "loto_cleaned_aggregates_25k.csv"),
               index=False, encoding="utf-8-sig")
    print("\naggregates:")
    print(agg.to_string(index=False))
    print("\nwrote loto_cleaned_per_topology_25k.csv and loto_cleaned_aggregates_25k.csv")


if __name__ == "__main__":
    main()
