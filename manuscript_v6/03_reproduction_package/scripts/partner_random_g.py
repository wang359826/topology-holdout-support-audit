#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lightweight random-partner-row control (g) for all five seeds.

Fits only the new g arm (random removal of the same number of partner rows as
arm e) and carries the archived a/e values alongside it.  This is the key
control for the question "is the pcu improvement specific to shared-composition
rows, or does removing any partner rows help?"  A seed-42 e_sub/g_non pilot was
moved to `_内部存档_非投稿/_v6清理_20261021/`; this script is the five-seed
control used in SI-C.4.

Output: outputs/partner_random_g.csv
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "03_投稿专用包", "03_reproduction_package", "scripts"))
DEFAULT_CSV = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "03_投稿专用包", "03_reproduction_package",
    "data", "all_MOFs_screening_data.csv"))
DEFAULT_OUT = os.path.abspath(os.path.join(HERE, "..", "outputs"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-scripts", default=DEFAULT_SRC)
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--n-jobs", type=int, default=1)
    ap.add_argument("--seeds", default="")
    args = ap.parse_args()

    sys.path.insert(0, os.path.abspath(args.source_scripts))
    from diversity_control import (  # noqa: PLC0415
        N_ESTIMATORS, SEED_LIST, CONTROL_TOPOS, load_and_build, diversity_stats,
    )
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    seeds = ([int(s) for s in args.seeds.split(",") if s.strip()]
             if args.seeds else SEED_LIST)
    archived = pd.read_csv(os.path.join(args.outdir, "arm_e_partner_coverage.csv"))
    rows = []

    for seed in seeds:
        X, y, topo, ck, lp, metal = load_and_build(args.csv, seed)
        tv = topo.to_numpy()
        cv = ck.to_numpy()
        print(f"\nseed = {seed}   建模样本 {len(X):,}")
        for target_topo in CONTROL_TOPOS:
            te = np.where(tv == target_topo)[0]
            sets = {t: set(cv[tv == t]) for t in pd.unique(tv)}
            partner = sorted(((t, len(sets[target_topo] & sets[t])) for t in sets if t != target_topo),
                             key=lambda x: -x[1])[0][0]
            te_mask = np.zeros(len(tv), dtype=bool)
            te_mask[te] = True
            test_comps = set(cv[te])
            partner_mask = (tv == partner) & (~te_mask)
            shared = partner_mask & np.isin(cv, np.array(sorted(test_comps), dtype=object))
            n_remove = int(shared.sum())
            partner_idx = np.where(partner_mask)[0]
            shared_idx = np.where(shared)[0]
            rng = np.random.default_rng(seed + 3000)
            g_remove = rng.choice(partner_idx, size=n_remove, replace=False)
            idx_g = np.setdiff1d(np.where(~te_mask)[0], g_remove)

            m = RandomForestRegressor(n_estimators=N_ESTIMATORS, random_state=seed, n_jobs=args.n_jobs)
            m.fit(X.iloc[idx_g], y.iloc[idx_g])
            pred = m.predict(X.iloc[te])
            yt = y.iloc[te].to_numpy()
            rec = {
                "seed": seed, "test_topo": target_topo, "partner": partner,
                "arm": "g_random_partner_removed", "n_train": int(len(idx_g)),
                "n_removed_vs_a": n_remove,
                "n_shared_removed": int(np.isin(g_remove, shared_idx).sum()),
                "R2": float(r2_score(yt, pred)),
                "MAE": float(mean_absolute_error(yt, pred)),
                "RMSE": float(np.sqrt(mean_squared_error(yt, pred))),
            }
            rec.update(diversity_stats(idx_g, topo, ck, lp, metal))
            rows.append(rec)
            a = archived[(archived.seed == seed) & (archived.test_topo == target_topo)
                         & (archived.regime == "a_with_partner")].iloc[0]
            e = archived[(archived.seed == seed) & (archived.test_topo == target_topo)
                         & (archived.regime == "e_shared_only_removed")].iloc[0]
            print(f"  {target_topo}: a={a.MAE:.4f}  e={e.MAE:.4f}  g={rec['MAE']:.4f}"
                  f"  (g removes {rec['n_shared_removed']}/{n_remove} shared rows)")

    out = os.path.join(args.outdir, "partner_random_g.csv")
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n已保存: {out}")


if __name__ == "__main__":
    main()
