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



def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _validated_predictions(root, mode, seed, strategies):
    path = root / 'outputs' / f'predictions_{mode}_seed{seed}.csv'
    _require(path.is_file(), f'missing prediction file: {path}')
    d = pd.read_csv(path)
    required = {'seed', 'strategy', 'fit_population', 'raw_row_index',
                'y_true', 'y_pred', 'n_test_fold', 'fold', 'legal'}
    _require(required <= set(d.columns), f'{path.name}: missing columns {required-set(d.columns)}')
    _require(len(d)>0 and d[list(required)].notna().all().all(), f'{path.name}: empty/missing values')
    _require(set(d.seed)=={seed}, f'{path.name}: wrong seed')
    expected = {(s,p) for s in strategies for p in ('historical','cleaned')}
    actual = set(zip(d.strategy,d.fit_population))
    _require(actual==expected, f'{path.name}: group set differs; missing={expected-actual}; extra={actual-expected}')
    _require(np.isfinite(d[['y_true','y_pred','raw_row_index','n_test_fold']].to_numpy(float)).all(),
             f'{path.name}: non-finite numbers')
    _require(not d.duplicated(['strategy','fit_population','raw_row_index']).any(),
             f'{path.name}: duplicate material in prediction group')
    for strategy in strategies:
        a = d[(d.strategy==strategy)&(d.fit_population=='historical')].sort_values('raw_row_index')
        b = d[(d.strategy==strategy)&(d.fit_population=='cleaned')].sort_values('raw_row_index')
        for column in ('raw_row_index','y_true','fold','legal'):
            _require(np.array_equal(a[column].to_numpy(),b[column].to_numpy()),
                     f'{path.name}: historical/cleaned {column} differs for {strategy}')
        if mode=='screening':
            _require(len(a)==25000, f'{path.name}: {strategy} must score 25000 rows')
        else:
            for population,g in (('historical',a),('cleaned',b)):
                _require(g.n_test_fold.nunique()==1 and int(g.n_test_fold.iloc[0])==len(g),
                         f'{path.name}: {strategy}/{population} row count differs from test size')
    return d


def check_arms(root, tol):
    rows = []
    summary = pd.read_csv(root / 'outputs' / 'sensitivity_five_seeds_summary.csv')
    _require(not summary.seed.duplicated().any() and set(summary.seed)==set(SEEDS),
             'arm summary must contain each of the five seeds exactly once')
    summary = summary.set_index('seed')
    expected_columns = {f'{t}_{a}_{p}' for t,a in [('nbo','a'),('nbo','b'),('nbo','e'),('pcu','a'),('pcu','e')] for p in ('h','c')}
    _require(expected_columns <= set(summary.columns), 'arm summary is missing required comparison columns')
    for seed in SEEDS:
        d = _validated_predictions(root, 'arms', seed,
            {f'{t}:{a}' for t in ('nbo','pcu') for a in ('a','b','e')})
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
    _require(len(rows)==50, f'expected 50 arm comparisons, got {len(rows)}')
    return pd.DataFrame(rows)


def check_screening(root, tol=1e-6):
    rows = []
    for seed in SEEDS:
        f = root / 'outputs' / f'predictions_screening_seed{seed}.csv'
        ref = root / 'outputs' / f'screening_utility_seed{seed}.csv'
        _require(ref.is_file(), f'missing screening reference: {ref}')
        d = _validated_predictions(root, 'screening', seed, {'random','topology'})
        arch = pd.read_csv(ref)
        selected = arch[arch.strategy.isin(['random','topology'])]
        expected_keys = {(s,k) for s in ('random','topology') for k in (250,1250,2500)}
        _require(len(selected)==6 and not selected.duplicated(['strategy','k']).any() and
                 set(zip(selected.strategy,selected.k))==expected_keys,
                 f'{ref.name}: expected six unique strategy/budget records')
        _require(np.isfinite(selected[['k','k_frac','overlap_at_k']].to_numpy(float)).all(),
                 f'{ref.name}: non-finite reference metrics')
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
                                 match=abs(ov - float(a.overlap_at_k)) <= tol))
    _require(len(rows)==30, f'expected 30 screening comparisons, got {len(rows)}')
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument('--tol', type=float, default=1e-6)
    args = ap.parse_args()
    root = Path(args.root)
    out = root / 'level2_predictions' / 'level2_report'
    _require(np.isfinite(args.tol) and args.tol>=0, 'tol must be finite and non-negative')
    arms = check_arms(root, args.tol)
    scr = check_screening(root, args.tol)
    out.mkdir(parents=True, exist_ok=True)
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
