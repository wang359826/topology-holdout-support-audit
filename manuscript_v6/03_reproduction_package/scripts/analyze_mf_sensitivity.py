"""Compare the prespecified max_features=1.0 sensitivity against the archived 'sqrt' run.

Both sides use the same saved splits and the same test rows; this script asserts that
row-for-row before computing any difference. No model is fitted here.

Outputs (under the sensitivity root):
  mf1_pooled.csv          pooled MAE / R2 per seed-target-representation-model-setting
  mf1_paired.csv          paired difference (1.0 - sqrt) per unit, with five-seed mean/SD
  mf1_per_topology.csv    per-topology paired differences on the LOTO folds
  mf1_summary.json        direction agreement used in the manuscript
"""
from pathlib import Path
import json
import sys
import argparse

P = Path(__file__).resolve().parents[1]
ROOT = P.parent
sys.path.insert(0, str(ROOT / '_tools/pylibs312'))
import numpy as np
import pandas as pd

SEEDS = [42, 143, 244, 345, 446]
SCOPES = {
    'mapped': dict(new='outputs_mf1_sensitivity_mapped', old='outputs_mapped_common', reps=['I', 'T'],
                   models=['RF', 'ET']),
    'full': dict(new='outputs_mf1_sensitivity_full', old='outputs', reps=['B', 'I'],
                 models=['RF', 'ET']),
}


def load_pred(root, folder, fold, rep, model):
    f = root / folder / fold / f'prediction_{rep}_{model}.npz'
    if not f.exists():
        return None
    z = np.load(f, allow_pickle=True)
    return dict(id=z['raw_row_id'], y=z['y_true'], p=z['prediction'],
                topo=z['topology'] if 'topology' in z.files else None)


def pooled_metrics(y, p):
    e = p - y
    sst = float(((y - y.mean()) ** 2).sum())
    sse = float((e ** 2).sum())
    return dict(n=int(len(y)), MAE=float(np.abs(e).mean()), RMSE=float(np.sqrt((e ** 2).mean())),
                R2=float(1 - sse / sst) if sst > 0 else float('nan'),
                bias=float(e.mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scope', choices=list(SCOPES), required=True)
    args = ap.parse_args()
    sc = SCOPES[args.scope]
    newroot = P / sc['new']
    oldroot = P / sc['old']
    rows, per_topo = [], []
    for seed in SEEDS:
        for target in ('uptake', 'selectivity'):
            folder = f'n25000_seed{seed}_{target}'
            for protocol in ('random', 'LOTO'):
                fdir = oldroot / folder
                if not fdir.exists():
                    continue
                folds = sorted([d.name for d in fdir.iterdir()
                                if d.is_dir() and d.name.startswith(protocol + '_fold')])
                # union of rows for pooled scoring, built only from folds present in both runs
                for rep in sc['reps']:
                    for model in sc['models']:
                        ys_new, ps_new, ys_old, ps_old, topos = [], [], [], [], []
                        ok = True
                        for fold in folds:
                            a = load_pred(newroot, folder, fold, rep, model)
                            b = load_pred(oldroot, folder, fold, rep, model)
                            if b is None or len(b['y']) == 0:
                                continue  # empty test fold in the archived run
                            if a is None or len(a['y']) == 0:
                                ok = False  # sensitivity fold not finished yet
                                break
                            if len(a['y']) != len(b['y']) or not np.array_equal(a['id'], b['id']):
                                ok = False
                                break
                            ys_new.append(a['y']); ps_new.append(a['p'])
                            ys_old.append(b['y']); ps_old.append(b['p']); topos.append(a['topo'])
                        if not ok or not ys_new:
                            print('SKIP (row mismatch or missing)', args.scope, seed, target, protocol, rep, model)
                            continue
                        y = np.concatenate(ys_new); pn = np.concatenate(ps_new); po = np.concatenate(ps_old)
                        mn = pooled_metrics(y, pn); mo = pooled_metrics(y, po)
                        rows.append(dict(scope=args.scope, seed=seed, target=target, protocol=protocol,
                                         representation=rep, model=model, n=mn['n'],
                                         MAE_sqrt=mo['MAE'], MAE_mf1=mn['MAE'], dMAE=mn['MAE'] - mo['MAE'],
                                         R2_sqrt=mo['R2'], R2_mf1=mn['R2']))
                        if protocol == 'LOTO':
                            tp = np.concatenate([t if t is not None else np.array(['?'] * len(x)) for t, x in
                                                 zip(topos, ys_new)])
                            for t in np.unique(tp):
                                m = tp == t
                                if m.sum() < 2:
                                    continue
                                per_topo.append(dict(scope=args.scope, seed=seed, target=target,
                                                     representation=rep, model=model, topology=str(t),
                                                     n=int(m.sum()),
                                                     dMAE=float(np.abs(pn[m] - y[m]).mean() -
                                                                np.abs(po[m] - y[m]).mean())))
    pooled = pd.DataFrame(rows)
    paired = (pooled.groupby(['scope', 'target', 'protocol', 'representation', 'model'])
              .agg(n_seeds=('seed', 'nunique'), mean_dMAE=('dMAE', 'mean'), sd_dMAE=('dMAE', 'std'),
                   n_negative=('dMAE', lambda x: int((x < 0).sum())),
                   n_positive=('dMAE', lambda x: int((x > 0).sum())),
                   mean_MAE_sqrt=('MAE_sqrt', 'mean'), mean_MAE_mf1=('MAE_mf1', 'mean'))
              .reset_index())
    pt = pd.DataFrame(per_topo)
    if len(pt):
        pt = (pt.groupby(['scope', 'target', 'representation', 'model', 'topology'])
              .agg(n_seeds=('seed', 'nunique'), mean_dMAE=('dMAE', 'mean'),
                   n_negative=('dMAE', lambda x: int((x < 0).sum())))
              .reset_index())
    pooled.to_csv(newroot / 'mf1_pooled.csv', index=False)
    paired.to_csv(newroot / 'mf1_paired.csv', index=False)
    pt.to_csv(newroot / 'mf1_per_topology.csv', index=False)
    summary = dict(scope=args.scope, n_units=int(len(pooled)),
                   paired=paired.to_dict(orient='records'))
    (newroot / 'mf1_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                              encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
