"""Step-4 finish analyses that reuse archived predictions (no model is refitted).

Outputs (under <root>/outputs/finish_20261023/):
  tie_audit.csv                  predicted-score ties at the top-k truncation, OOF screening
  oof_candidate_bootstrap.csv    candidate-population bootstrap of top-1% overlap
  fixed_pool_budget.csv          fixed-candidate-pool recovery / selected mean / oracle loss
  per_topology_direction_counts.csv   per-topology sign counts of the representation contrasts
  summary.json                   numbers quoted in the manuscript and SI

Run with --root pointing at the reproduction package and optionally --expt12 at the
experiment-12 working directory (the per-topology paired table is not in the slim archive).
"""
from pathlib import Path
import sys, json, argparse, csv, math

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P.parents[1] / '_tools/pylibs312'))
import numpy as np
import pandas as pd


def topk_indices(score, k):
    order = np.argsort(-score, kind='stable')
    return order[:k]


def tie_audit(root):
    rows = []
    for seed in (42, 143, 244, 345, 446):
        f = root / 'outputs' / f'predictions_screening_seed{seed}.csv'
        if not f.exists():
            continue
        d = pd.read_csv(f)
        d = d[d.legal.astype(bool)]
        for (strategy, pop), g in d.groupby(['strategy', 'fit_population']):
            s = g.sort_values('row_index', kind='stable')
            y = s.y_pred.to_numpy()
            n = len(y)
            for frac in (0.01, 0.05, 0.10):
                k = int(round(n * frac))
                order = np.argsort(-y, kind='stable')
                b = y[order[k - 1]]
                n_tied_at_boundary = int((y == b).sum())
                # tie straddles the cut when the next score equals the boundary score
                straddle = bool(n < len(order) and y[order[k]] == b)
                # alternative rule: lowest source row id wins among tied scores
                ids = s.raw_row_index.to_numpy()
                alt = np.lexsort((ids[order], -y[order]))[:k]
                sel_main = set(ids[order[:k]].tolist())
                sel_alt = set(ids[order[alt]].tolist())
                churn = int(len(sel_main - sel_alt))
                rows.append(dict(seed=seed, strategy=strategy, fit_population=pop, budget_fraction=frac,
                                 k=k, n=n, boundary_score=b, n_rows_at_boundary_score=n_tied_at_boundary,
                                 tie_straddles_cut=straddle, members_changed_by_rule=churn))
    out = pd.DataFrame(rows)
    out.to_csv(P / 'outputs' / 'finish_20261023' / 'tie_audit.csv', index=False)
    return out


def overlap_at_k(y_true, y_pred, k):
    a = set(topk_indices(y_true, k).tolist())
    b = set(topk_indices(y_pred, k).tolist())
    return len(a & b) / k


def bootstrap(root, n_boot=200, frac=0.01):
    rows = []
    rng = np.random.default_rng(20261023)
    for seed in (42, 143, 244, 345, 446):
        f = root / 'outputs' / f'predictions_screening_seed{seed}.csv'
        if not f.exists():
            continue
        d = pd.read_csv(f)
        d = d[d.legal.astype(bool)]
        for (strategy, pop), g in d.groupby(['strategy', 'fit_population']):
            yt = g.y_true.to_numpy()
            yp = g.y_pred.to_numpy()
            n = len(yt)
            k = int(round(n * frac))
            point = overlap_at_k(yt, yp, k)
            vals = np.empty(n_boot)
            for i in range(n_boot):
                idx = rng.integers(0, n, n)
                vals[i] = overlap_at_k(yt[idx], yp[idx], k)
            rows.append(dict(seed=seed, strategy=strategy, fit_population=pop, k=k,
                             overlap_point=point, boot_mean=float(vals.mean()),
                             boot_sd=float(vals.std(ddof=1)),
                             boot_q025=float(np.quantile(vals, 0.025)),
                             boot_q975=float(np.quantile(vals, 0.975)), n_boot=n_boot))
    out = pd.DataFrame(rows)
    out.to_csv(P / 'outputs' / 'finish_20261023' / 'oof_candidate_bootstrap.csv', index=False)
    return out


def fixed_pool(root):
    f = root / 'outputs/followup_20261023/experiment6/screening_summary.csv'
    d = pd.read_csv(f)
    d['oracle_loss_fraction'] = 1.0 - d.selected_mean_mean / d.oracle_mean_mean
    keep = ['target', 'support', 'representation', 'model', 'budget_fraction', 'k',
            'recovery_mean', 'recovery_std', 'selected_mean_mean', 'oracle_mean_mean',
            'regret_mean', 'oracle_loss_fraction', 'MAE_mean']
    out = d[keep].sort_values(['target', 'support', 'representation', 'model', 'budget_fraction'])
    out.to_csv(P / 'outputs' / 'finish_20261023' / 'fixed_pool_budget.csv', index=False)
    return out


def per_topology(expt12):
    rows, tidy = [], []
    for scope, sub, contrast in (('full', 'outputs', 'I-B'),
                                 ('mapped_common', 'outputs_mapped_common', 'T-I')):
        f = expt12 / sub / 'per_topology_paired_differences.csv'
        if not f.exists():
            continue
        d = pd.read_csv(f)
        d = d[(d.stage == 25000) & (d.protocol == 'LOTO') & (d.contrast == contrast)]
        for (target, model), g in d.groupby(['target', 'model']):
            g = g.dropna(subset=['delta_MAE'])
            per = g.groupby('topology').agg(mean_delta=('delta_MAE', 'mean'),
                                            n_seeds=('seed', 'nunique'),
                                            n_negative=('delta_MAE', lambda x: int((x < 0).sum())))
            for topo, r in per.iterrows():
                tidy.append(dict(scope=scope, contrast=contrast, target=target, model=model,
                                 topology=topo, n_seeds=int(r.n_seeds), mean_delta=float(r.mean_delta),
                                 n_negative=int(r.n_negative)))
            rows.append(dict(scope=scope, contrast=g.contrast.iloc[0], target=target, model=model,
                             n_topologies=int(len(per)),
                             n_mean_MAE_lower=int((per.mean_delta < 0).sum()),
                             n_mean_MAE_higher=int((per.mean_delta > 0).sum()),
                             n_sign_consistent_4of5=int(((per.n_negative >= 4) | (per.n_negative <= 1)).sum()),
                             topologies_mean_higher=','.join(sorted(per.index[per.mean_delta > 0])),
                             min_delta=float(per.mean_delta.min()), max_delta=float(per.mean_delta.max()),
                             median_delta=float(per.mean_delta.median())))
    pd.DataFrame(tidy).to_csv(P / 'outputs' / 'finish_20261023' / 'per_topology_paired_deltas.csv',
                              index=False)
    out = pd.DataFrame(rows)
    out.to_csv(P / 'outputs' / 'finish_20261023' / 'per_topology_direction_counts.csv', index=False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(P))
    ap.add_argument('--expt12', default=str(P.parents[1] / '实验12_化学表示与新颖性'))
    ap.add_argument('--n-boot', type=int, default=200)
    args = ap.parse_args()
    root = Path(args.root)
    (root / 'outputs' / 'finish_20261023').mkdir(parents=True, exist_ok=True)
    tie = tie_audit(root)
    boot = bootstrap(root, n_boot=args.n_boot)
    pool = fixed_pool(root)
    pt = per_topology(Path(args.expt12))
    summary = dict(
        tie_audit=dict(n_rows=int(len(tie)),
                       any_tie_straddles_cut=bool(tie.tie_straddles_cut.any()),
                       max_rows_at_boundary_score=int(tie.n_rows_at_boundary_score.max()),
                       max_members_changed_by_rule=int(tie.members_changed_by_rule.max())),
        bootstrap=dict(n_rows=int(len(boot)),
                       mean_boot_sd=float(boot.boot_sd.mean()),
                       by_strategy={f'{k[0]}|{k[1]}': dict(overlap_point=float(v.overlap_point.iloc[0]),
                                                           boot_sd=float(v.boot_sd.iloc[0]))
                                    for k, v in boot.groupby(['strategy', 'fit_population'])}),
        fixed_pool=dict(n_rows=int(len(pool)),
                        budgets=sorted(pool.budget_fraction.unique().tolist())),
        per_topology=pt.to_dict(orient='records'),
    )
    (root / 'outputs' / 'finish_20261023' / 'summary.json').write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
