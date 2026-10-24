#!/usr/bin/env python
"""Model-free support audit for grouped validation; no causal or performance verdict.

The CLI accepts the historical options. Pair counts are always computed separately
for each chemistry definition, over all groups unless --top-n-groups explicitly
limits the comparison. --pair-report controls only the detailed pair CSV.
Missing grouping values and entirely missing chemistry keys are excluded and
counted. Partial chemistry missingness is encoded explicitly; literal NA-like
strings remain values. Entropies use bits. Plugin and Miller-Madow estimates are
reported separately, without clipping corrected ratios or threshold verdicts.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from itertools import combinations
import math
from pathlib import Path
import sys
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / 'outputs'
DATA = HERE.parent / 'data'
PRESETS = {'hmof': dict(csv=str(DATA / 'all_MOFs_screening_data.csv'),
    group_col='topology', coarse=['metal_linker', 'organic_linker1', 'organic_linker2'],
    fine=['metal_linker', 'organic_linker1', 'organic_linker2', 'functional_groups'])}
PAIR_COLUMNS = ['group_a', 'group_b', 'shared_chemistries', 'union_chemistries', 'jaccard']
GROUP_COLUMNS = ['group', 'n_test', 'n_train', 'n_test_chemistries',
    'n_unseen_chemistries', 'composition_unseen_rate', 'n_unseen_structures',
    'structure_unseen_rate']
NAN = float('nan')


def _missing(v):
    return bool(pd.isna(v)) or (isinstance(v, str) and not v.strip())


def composition_key(df, cols):
    """Return collision-safe tuples; all-missing rows have no chemistry key."""
    if not cols or len(cols) != len(set(cols)):
        raise ValueError('chemistry columns must be a nonempty, unique list')
    absent = [c for c in cols if c not in df.columns]
    if absent:
        raise KeyError(f'chemistry columns not found: {absent}')
    values = []
    partial = []
    for row in df[cols].itertuples(index=False, name=None):
        missing = [_missing(v) for v in row]
        values.append(None if all(missing) else tuple(
            ('missing',) if m else ('value', str(v)) for v, m in zip(row, missing)))
        partial.append(any(missing) and not all(missing))
    result = pd.Series(values, index=df.index, dtype=object)
    result.attrs['partial_missing'] = partial
    return result


def _entropy_counts(counts):
    total = sum(counts)
    return -sum((n / total) * math.log2(n / total) for n in counts if n) if total else NAN


def _ratio(a, b):
    return a / b if math.isfinite(b) and b > 0 else NAN


def _prepare(chem, group):
    if len(chem) != len(group):
        raise ValueError('chemistry and group vectors have different lengths')
    counts = Counter()
    missing_chem = missing_group = partial_kept = 0
    partial = getattr(chem, 'attrs', {}).get('partial_missing', [False] * len(chem))
    for i, (c, g) in enumerate(zip(chem, group)):
        cm = c is None or (not isinstance(c, tuple) and _missing(c))
        gm = _missing(g)
        missing_chem += cm
        missing_group += gm
        if cm or gm:
            continue
        counts[c, str(g)] += 1
        partial_kept += bool(partial[i])
    return counts, dict(n_input_rows=len(chem), n_missing_chemistry_rows=missing_chem,
        n_missing_group_rows=missing_group, n_partial_chemistry_rows_retained=partial_kept,
        n_rows_excluded=len(chem) - sum(counts.values()))


def analyze(chem, group, label='dataset', granularity='coarse', top_n_groups=None):
    """Return summary, per-held-out-group metrics and pair details, without I/O."""
    if top_n_groups is not None and top_n_groups < 1:
        raise ValueError('top_n_groups must be positive or None (all groups)')
    counts, audit = _prepare(chem, group)
    n = sum(counts.values())
    nc, ng = Counter(), Counter()
    cg, gc = defaultdict(set), defaultdict(set)
    for (c, g), k in counts.items():
        nc[c] += k
        ng[g] += k
        cg[c].add(g)
        gc[g].add(c)
    single = {c for c in nc if len(cg[c]) == 1}
    single_rows = sum(nc[c] for c in single)
    memberships = sum(map(len, cg.values()))
    groups = sorted(ng, key=lambda g: (-ng[g], g))
    selected = groups if top_n_groups is None else groups[:top_n_groups]
    pair_rows = []
    for a, b in combinations(selected, 2):
        shared = len(gc[a] & gc[b])
        union = len(gc[a] | gc[b])
        pair_rows.append(dict(group_a=a, group_b=b, shared_chemistries=shared,
            union_chemistries=union, jaccard=shared / union))
    pair_rows.sort(key=lambda x: (-x['shared_chemistries'], x['group_a'], x['group_b']))
    group_rows = []
    for g in groups:
        unseen = gc[g] & single
        unseen_rows = sum(counts[c, g] for c in unseen)
        group_rows.append(dict(group=g, n_test=ng[g], n_train=n-ng[g],
            n_test_chemistries=len(gc[g]), n_unseen_chemistries=len(unseen),
            composition_unseen_rate=len(unseen) / len(gc[g]),
            n_unseen_structures=unseen_rows, structure_unseen_rate=unseen_rows / ng[g]))
    hg = _entropy_counts(ng.values())
    hc = _entropy_counts(nc.values())
    hj = _entropy_counts(counts.values())
    hg_c, hc_g = hj - hc, hj - hg
    correction = 1 / (2 * n * math.log(2)) if n else NAN
    hg_mm = hg + (len(ng) - 1) * correction
    hc_mm = hc + (len(nc) - 1) * correction
    hj_mm = hj + (len(counts) - 1) * correction
    hg_c_mm, hc_g_mm = hj_mm - hc_mm, hj_mm - hg_mm
    summary = dict(label=label, granularity=granularity,
        status='no_usable_rows' if not n else ('single_group' if len(ng)==1 else 'ok'),
        **audit, n_samples=n, n_groups=len(ng), n_chemistries=len(nc),
        n_chemistry_group_memberships=memberships,
        samples_per_chemistry=n / len(nc) if nc else NAN,
        n_single_group_chemistries=len(single), n_single_group_structures=single_rows,
        composition_weighted_unseen_rate=len(single) / len(nc) if nc else NAN,
        structure_weighted_unseen_rate=single_rows / n if n else NAN,
        membership_weighted_unseen_rate=len(single) / memberships if memberships else NAN,
        frac_single_topology=len(single) / len(nc) if nc else NAN,
        H_group=hg, H_group_given_chem=hg_c, cond_frac=_ratio(hg_c,hg),
        H_group_plugin=hg, H_chem_plugin=hc, H_joint_plugin=hj,
        H_group_given_chem_plugin=hg_c, H_chem_given_group_plugin=hc_g,
        group_residual_ratio_plugin=_ratio(hg_c,hg),
        chemistry_residual_ratio_plugin=_ratio(hc_g,hc),
        H_group_mm=hg_mm, H_chem_mm=hc_mm, H_joint_mm=hj_mm,
        H_group_given_chem_mm=hg_c_mm, H_chem_given_group_mm=hc_g_mm,
        group_residual_ratio_mm=_ratio(hg_c_mm,hg_mm),
        chemistry_residual_ratio_mm=_ratio(hc_g_mm,hc_mm),
        pair_scope='all_groups' if len(selected)==len(groups) else 'largest_groups_subset',
        pair_comparison_complete=len(selected)==len(groups),
        n_groups_compared=len(selected), n_pairs_total=len(groups)*(len(groups)-1)//2,
        n_pairs_compared=len(pair_rows),
        n_shared_pairs=sum(x['shared_chemistries']>0 for x in pair_rows),
        max_jaccard=max((x['jaccard'] for x in pair_rows), default=NAN))
    return (summary, pd.DataFrame(group_rows, columns=GROUP_COLUMNS),
            pd.DataFrame(pair_rows, columns=PAIR_COLUMNS))


def diagnose(chem, group, label, granularity):
    return analyze(chem, group, label, granularity)[0]


def group_pairs(chem, group, top_n=None):
    return analyze(chem, group, top_n_groups=top_n)[2]


def verdict(row, n_shared_pairs=None, total_pairs=None):
    """Describe observed support; do not classify independence or transferability."""
    if row['status']=='no_usable_rows':
        return 'No usable rows; support and entropy statistics are undefined.'
    if row['status']=='single_group':
        return 'Only one observed group; leave-one-group-out has no training group and H(group)=0.'
    return (f"{row['n_shared_pairs']} of {row['n_pairs_compared']} compared pairs share "
        f"chemistry ({row['pair_scope']}). These sample statistics do not establish "
        'causality, independence, model performance or a feasible controlled contrast.')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Audit observed support for grouped validation.')
    ap.add_argument('--csv')
    ap.add_argument('--preset', choices=sorted(PRESETS))
    ap.add_argument('--group-col')
    ap.add_argument('--chem-cols')
    ap.add_argument('--coarse-cols')
    ap.add_argument('--fine-cols')
    ap.add_argument('--label')
    ap.add_argument('--max-rows', type=int)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--pair-report', action='store_true', help='also write pair detail CSV')
    ap.add_argument('--top-n-groups', type=int, default=None,
        help='explicitly restrict pair comparison to largest N groups; default: all groups')
    ap.add_argument('--outdir', default=str(OUT))
    args = ap.parse_args(argv)
    preset = PRESETS.get(args.preset, {})
    csv_path = args.csv or preset.get('csv')
    group_col = args.group_col or preset.get('group_col')
    if not csv_path or not group_col:
        ap.error('--csv and --group-col are required unless --preset supplies them')
    if args.max_rows is not None and args.max_rows < 1:
        ap.error('--max-rows must be positive')
    if args.top_n_groups is not None and args.top_n_groups < 1:
        ap.error('--top-n-groups must be positive')
    parse = lambda s: [x.strip() for x in s.split(',') if x.strip()] if s else None
    coarse = parse(args.coarse_cols) or preset.get('coarse')
    fine = parse(args.fine_cols) or preset.get('fine')
    if args.chem_cols:
        if args.coarse_cols or args.fine_cols:
            ap.error('--chem-cols cannot be combined with --coarse-cols/--fine-cols')
        coarse, fine = parse(args.chem_cols), None
    definitions = [(g,c) for g,c in [('coarse',coarse),('fine',fine)] if c]
    if not definitions:
        ap.error('provide --chem-cols or --coarse-cols/--fine-cols')
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, low_memory=False)
    if group_col not in df:
        ap.error(f'grouping column not found: {group_col}')
    if args.max_rows is not None and args.max_rows < len(df):
        df = df.sample(n=args.max_rows, random_state=args.seed)
    label = args.label or args.preset or Path(csv_path).stem
    rows, per_groups, pairs = [], [], []
    for gran, cols in definitions:
        row, pg, pf = analyze(composition_key(df,cols), df[group_col], label, gran,
                             args.top_n_groups)
        row['chemistry_columns'] = ','.join(cols)
        row['grouping_column'] = group_col
        rows.append(row)
        for frame in (pg,pf):
            frame.insert(0,'granularity',gran)
            frame.insert(0,'label',label)
        per_groups.append(pg)
        pairs.append(pf)
        print(f'[{gran}] n={row["n_samples"]}; excluded={row["n_rows_excluded"]}; '
              f'groups={row["n_groups"]}; chemistries={row["n_chemistries"]}')
        print(f'  unseen composition/structure fractions: '
              f'{row["composition_weighted_unseen_rate"]:.6g} / '
              f'{row["structure_weighted_unseen_rate"]:.6g}')
        print(f'  plugin H(G|C)/H(G)={row["group_residual_ratio_plugin"]:.6g}; '
              f'H(C|G)/H(C)={row["chemistry_residual_ratio_plugin"]:.6g}')
        print('  '+verdict(row))
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'confound_diagnostic.csv',index=False)
    pd.concat(per_groups,ignore_index=True).to_csv(out/'confound_diagnostic_groups.csv',index=False)
    if args.pair_report:
        pd.concat(pairs,ignore_index=True).to_csv(out/'confound_diagnostic_pairs.csv',index=False)
    print('Plugin and Miller-Madow estimates are separate. Undefined ratios are blank/NaN; '
          'partial missing chemistry is retained and counted. All estimates depend on '
          'sample size and the supplied chemistry definition; no threshold verdict is applied.')
    return 2 if any(r['status']=='no_usable_rows' for r in rows) else 0


if __name__=='__main__':
    raise SystemExit(main())
