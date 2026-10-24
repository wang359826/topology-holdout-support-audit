"""Level 2: recompute headline metrics from the archived predictions.

This script never fits a model. It reads the row-level prediction files shipped in
../../outputs/predictions_{arms,screening}_seed*.csv (each row carries raw_row_index,
y_true and y_pred) and re-derives the quantities the manuscript quotes, then compares them
with the archived summary tables. It is the evidence for the "prediction review" level.

Usage (plain environment with numpy + pandas):
    python verify_predictions.py [--root ..] [--tol 1e-6]
Exit code 0 = every recomputed value matched the archive within tolerance.
"""
from pathlib import Path
import argparse
import json
import sys

import numpy as np
import pandas as pd

SEEDS = [42, 143, 244, 345, 446]
ARM_REF = {('a', 'historical'): ('isoreticular_control_seeds.csv', 'with_pair'),
           ('b', 'historical'): ('isoreticular_control_seeds.csv', 'without_pair'),
           ('e', 'historical'): ('arm_e_partner_coverage.csv', 'e_shared_only_removed'),
           ('f', 'historical'): ('arm_e_partner_coverage.csv', 'f_size_matched_from_e'),
           ('a', 'cleaned'): ('isoreticular_control_seeds.csv', 'with_pair'),
           ('b', 'cleaned'): ('isoreticular_control_seeds.csv', 'without_pair'),
           ('e', 'cleaned'): ('arm_e_partner_coverage.csv', 'e_shared_only_removed'),
           ('f', 'cleaned'): ('arm_e_partner_coverage.csv', 'f_size_matched_from_e')}


def metrics(y, p):
    e = p - y
    sst = float(((y - y.mean()) ** 2).sum())
    sse = float((e ** 2).sum())
    return dict(n=int(len(y)), MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt((e ** 2).mean())),
                R2=float(1 - sse / sst) if sst > 0 else float('nan'))


def top_overlap(y, p, k):
    a = set(np.argsort(-y, kind='stable')[:k].tolist())
    b = set(np.argsort(-p, kind='stable')[:k].tolist())
    return len(a & b) / k


def check_arms(root, tol):
    rows = []
    summary = pd.read_csv(root / 'outputs' / 'sensitivity_five_seeds_summary.csv').set_index('seed')
    for seed in SEEDS:
        f = root / 'outputs' / f'predictions_arms_seed{seed}.csv'
        if not f.exists() or seed not in summary.index:
            continue
        d = pd.read_csv(f)
        # the archived metrics score every test row; `legal` marks the separate
        # input-validity sensitivity and must not be used to subset here
        for (strategy, pop), g in d.groupby(['strategy', 'fit_population']):
            try:
                topo, arm = strategy.split(':')
            except ValueError:
                continue
            col = f'{topo}_{arm}_{"h" if pop == "historical" else "c"}'
            if col not in summary.columns:
                continue
            m = metrics(g.y_true.to_numpy(), g.y_pred.to_numpy())
            ref = float(summary.loc[seed, col])
            rows.append(dict(seed=seed, strategy=strategy, population=pop, n=m['n'],
                             MAE_recomputed=m['MAE'], MAE_archive=ref,
                             match=abs(m['MAE'] - ref) <= tol))
    return pd.DataFrame(rows)


def check_screening(root):
    rows = []
    for seed in SEEDS:
        f = root / 'outputs' / f'predictions_screening_seed{seed}.csv'
        ref = root / 'outputs' / f'screening_utility_seed{seed}.csv'
        if not f.exists() or not ref.exists():
            continue
        d = pd.read_csv(f)
        arch = pd.read_csv(ref)
        for (strategy, pop), g in d.groupby(['strategy', 'fit_population']):
            if pop != 'historical':
                continue
            y = g.y_true.to_numpy(); p = g.y_pred.to_numpy()
            for _, a in arch[arch.strategy == strategy].iterrows():
                k = int(a.k)
                if k >= len(y):
                    continue
                ov = top_overlap(y, p, k)
                rows.append(dict(seed=seed, strategy=strategy, budget_fraction=float(a.k_frac), k=k,
                                 overlap_recomputed=ov, overlap_archive=float(a.overlap_at_k),
                                 match=abs(ov - float(a.overlap_at_k)) <= 1e-6))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument('--tol', type=float, default=1e-6)
    args = ap.parse_args()
    root = Path(args.root)
    out = root / 'level2_predictions' / 'level2_report'
    out.mkdir(parents=True, exist_ok=True)
    arms = check_arms(root, args.tol)
    scr = check_screening(root)
    arms.to_csv(out / 'arms_recomputed.csv', index=False)
    scr.to_csv(out / 'screening_recomputed.csv', index=False)
    a_ok = bool(arms.match.all()) if len(arms) else False
    s_ok = bool(scr.match.all()) if len(scr) else False
    summary = dict(arms_rows=int(len(arms)), arms_all_match=a_ok,
                   screening_rows=int(len(scr)), screening_all_match=s_ok,
                   note='Recomputed from row-level predictions; no model is fitted here.')
    (out / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return 0 if (a_ok and s_ok) else 1


if __name__ == '__main__':
    sys.exit(main())
