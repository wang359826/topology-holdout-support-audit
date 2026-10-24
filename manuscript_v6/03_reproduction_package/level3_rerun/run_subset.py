"""Level 3: rebuild one representative experiment from the raw input data.

This is the only level that fits models. It reproduces the seed-42, 25,000-row,
random-split, random-forest representation comparison (G / B / I) that underlies
SI-I.1 and Table S19, and compares the result with the archived pooled metrics.

Inputs are not redistributed: pass the hMOF CSV you obtained from the public record
(see ../config/config.json for the record and the expected SHA256).

Usage:
    python run_subset.py --csv /path/all_MOFs_screening_data.csv [--out .] [--n-jobs 1]
Exit code 0 = the rebuilt metrics match the archive within tolerance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold

NUMERIC = ['volume [A^3]', 'weight [u]', 'surface_area [m^2/g]', 'void_fraction',
           'void_volume [cm^3/g]', 'largest_free_sphere_diameter [A]',
           'largest_included_sphere_along_free_sphere_path_diameter [A]',
           'largest_included_sphere_diameter [A]']
REPS = {'G': [], 'B': ['metal_linker', 'functional_groups'],
        'I': ['metal_linker', 'functional_groups', 'organic_linker1', 'organic_linker2']}
SEED = 42
N = 25000
TARGET = 'CO2_uptake_P0.15bar_T298K [mmol/g]'


def norm(v):
    if pd.isna(v):
        return '__MISSING__'
    try:
        x = float(v)
        if np.isfinite(x) and x.is_integer():
            return str(int(x))
    except (ValueError, TypeError):
        pass
    return str(v)


def pooled(y, p):
    e = p - y
    sst = float(((y - y.mean()) ** 2).sum())
    return dict(n=int(len(y)), MAE=float(np.abs(e).mean()),
                R2=float(1 - float((e ** 2).sum()) / sst))



def validate_archive(archive):
    path = Path(archive)
    if not path.is_file():
        raise ValueError(f'missing reference archive: {path}')
    ar = pd.read_csv(path)
    required = {'stage','seed','protocol','model','target','representation','MAE','R2'}
    if not required <= set(ar.columns):
        raise ValueError(f'reference is missing columns: {required-set(ar.columns)}')
    ar = ar[(ar.stage==N)&(ar.seed==SEED)&(ar.protocol=='random')&
            (ar.model=='RF')&(ar.target=='uptake')&ar.representation.isin(REPS)]
    if len(ar)!=3 or set(ar.representation)!=set(REPS) or ar.representation.duplicated().any():
        raise ValueError('reference must contain exactly one G, B and I row for the declared configuration')
    if not np.isfinite(ar[['MAE','R2']].to_numpy(float)).all():
        raise ValueError('reference metrics must be finite')
    return ar


def validate_input(csv_path, config_path):
    cfg = json.loads(Path(config_path).read_text(encoding='utf-8-sig'))['inputs']['hmof']
    h = hashlib.sha256()
    path = Path(csv_path)
    with path.open('rb') as fh:
        for block in iter(lambda:fh.read(1<<20), b''):
            h.update(block)
    sha = h.hexdigest()
    if sha != cfg['sha256'] or path.stat().st_size != int(cfg['bytes']):
        raise ValueError('input SHA256 or byte size differs from config/config.json; refusing rerun')
    return sha, int(cfg['rows'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--out', default=str(Path(__file__).resolve().parent / 'rerun_out'))
    ap.add_argument('--archive', default=str(Path(__file__).resolve().parents[1] / 'outputs' /
                                             'followup_20261023' / 'experiment12' / 'full' /
                                             'pooled_metrics.csv'))
    ap.add_argument('--tol', type=float, default=1e-6)
    ap.add_argument('--n-jobs', type=int, default=1)
    ap.add_argument('--config', default=str(Path(__file__).resolve().parents[1] / 'config' / 'config.json'))
    args = ap.parse_args()
    if args.n_jobs==0 or not np.isfinite(args.tol) or args.tol<0:
        raise ValueError('n-jobs cannot be zero and tol must be finite/non-negative')
    reference = validate_archive(args.archive)
    sha, expected_rows = validate_input(args.csv, args.config)
    t0 = time.time()
    raw = pd.read_csv(args.csv)
    if len(raw)!=expected_rows:
        raise ValueError('input row count differs from config')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sample = raw.sample(N, random_state=SEED).copy()
    sample['raw_row_id'] = sample.index
    scalar = sample[NUMERIC].to_numpy(float)
    ok = np.isfinite(scalar).all(1) & (scalar >= 0).all(1)
    y_all = pd.to_numeric(sample[TARGET], errors='coerce').to_numpy()
    ok &= np.isfinite(y_all)
    d = sample.loc[ok].reset_index(drop=True)
    y = pd.to_numeric(d[TARGET], errors='coerce').to_numpy(float)
    num = d[NUMERIC].to_numpy(np.float32)
    for c in ['metal_linker', 'organic_linker1', 'organic_linker2', 'functional_groups']:
        d[c] = d[c].map(norm)
    splits = list(KFold(5, shuffle=True, random_state=SEED).split(num, y))
    rows = []
    for rep, cats in REPS.items():
        preds, ys = [], []
        for fold, (tr, te) in enumerate(splits):
            a = num[tr]; b = num[te]
            if cats:
                enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.float32)
                a = np.c_[a, enc.fit_transform(d.iloc[tr][cats])]
                b = np.c_[b, enc.transform(d.iloc[te][cats])]
            m = RandomForestRegressor(n_estimators=120, max_features='sqrt',
                                      random_state=SEED, n_jobs=args.n_jobs)
            m.fit(a, y[tr])
            preds.append(m.predict(b)); ys.append(y[te])
        rows.append(dict(representation=rep, **pooled(np.concatenate(ys), np.concatenate(preds))))
    got = pd.DataFrame(rows)
    got.to_csv(out / 'rerun_metrics.csv', index=False)
    res = dict(csv=args.csv, sha256=sha, n_rows=int(len(d)), seed=SEED,
               elapsed_seconds=round(time.time() - t0, 1), metrics=got.to_dict(orient='records'))
    comp = []
    for _, r in reference.iterrows():
        g = got[got.representation==r.representation].iloc[0]
        comp.append(dict(representation=r.representation,
            MAE_rerun=float(g.MAE), MAE_archive=float(r.MAE),
            R2_rerun=float(g.R2), R2_archive=float(r.R2),
            match=abs(float(g.MAE)-float(r.MAE))<=args.tol and
                  abs(float(g.R2)-float(r.R2))<=args.tol))
    pd.DataFrame(comp).to_csv(out/'comparison_archive.csv',index=False)
    res['comparison'] = comp
    res['all_match'] = len(comp)==3 and all(c['match'] for c in comp)
    (out / 'summary.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
    print(json.dumps(res, indent=2))
    return 0 if res['all_match'] else 1


if __name__ == '__main__':
    sys.exit(main())
