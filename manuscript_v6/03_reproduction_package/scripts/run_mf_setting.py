"""Prespecified feature-subsampling sensitivity for the two representation contrasts.

Frozen before any fit of this sensitivity:
  * scope "mapped" : experiment-12 mapped-common subset (strict 33-ID validated linker mapping)
    contrast I vs T  (2 reps x 2 learners x 2 targets x 5 seeds x [5 random + 8 non-empty LOTO])
  * scope "full"   : experiment-12 full 25,000-row samples
    contrast B vs I  (2 reps x 2 learners x 2 targets x 5 seeds x [5 random + 11 LOTO])
  * max_features = 1.0 is the only changed setting; 120 trees, random_state = sampling seed,
    identical materials, splits, targets and preprocessing as the archived 'sqrt' run.
  * no outer-test-based selection: every seed/target/fold is fitted whatever the direction.

Outputs go to a separate root so the archived sqrt results are never overwritten.
"""
from pathlib import Path
import sys, os, json, time, argparse

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
P = Path(__file__).resolve().parents[1]
ROOT = P.parent
sys.path.insert(0, str(ROOT / '_tools/pylibs312'))
sys.path.insert(0, str(ROOT / '03_投稿专用包/03_reproduction_package/scripts'))
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor


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


def atomic_json(path, obj):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


SEEDS = [42, 143, 244, 345, 446]
TARGETS = ['uptake', 'selectivity']
PROTOCOLS = ['random', 'LOTO']
MAX_FEATURES = 1.0
N_ESTIMATORS = 120
SCOPES = {
    'mapped': dict(src='outputs_mapped_common', reps=['I', 'T'], models=['RF', 'ET'],
                   out='outputs_mf1_sensitivity_mapped',
                   note='strict validated 33-ID linker mapping; I vs T'),
    'full': dict(src='outputs', reps=['B', 'I'], models=['RF', 'ET'],
                 out='outputs_mf1_sensitivity_full',
                 note='full 25k sample; B vs I'),
}


def build_one(rep, d, tr, te, num, li, bm):
    if rep == 'T':
        enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.float32)
        cats = ['metal_linker', 'functional_groups']
        ac = enc.fit_transform(d.iloc[tr][cats])
        bc = enc.transform(d.iloc[te][cats]) if len(te) else np.empty((0, ac.shape[1]), dtype=np.float32)
        blocks_a, blocks_b = [], []
        for slot in range(2):
            trainbits = bm[li[tr, slot]]
            s = trainbits.sum(0)
            mask = (s > 0) & (s < len(tr))
            blocks_a.append(trainbits[:, mask])
            blocks_b.append(bm[li[te, slot]][:, mask])
        a = np.column_stack([num[tr], ac, *blocks_a]).astype(np.float32)
        b = np.column_stack([num[te], bc, *blocks_b]).astype(np.float32)
        return a, b
    cats = {'B': ['metal_linker', 'functional_groups'],
            'I': ['metal_linker', 'functional_groups', 'organic_linker1', 'organic_linker2']}[rep]
    enc = OneHotEncoder(handle_unknown='ignore', sparse_output=False, dtype=np.float32)
    at = enc.fit_transform(d.iloc[tr][cats])
    bt = enc.transform(d.iloc[te][cats]) if len(te) else np.empty((0, at.shape[1]), dtype=np.float32)
    return np.c_[num[tr], at].astype(np.float32), np.c_[num[te], bt].astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scope', choices=list(SCOPES), required=True)
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--targets', default=','.join(TARGETS))
    ap.add_argument('--reps', default='')
    ap.add_argument('--models', default='')
    ap.add_argument('--protocols', default=','.join(PROTOCOLS))
    ap.add_argument('--max-folds', type=int, default=0, help='debug: only first k folds per protocol')
    ap.add_argument('--n-jobs', type=int, default=1)
    ap.add_argument('--stages', default='25000')
    ap.add_argument('--out-root', default='')
    args = ap.parse_args()
    scope = SCOPES[args.scope]
    reps = (args.reps or ','.join(scope['reps'])).split(',')
    models = (args.models or ','.join(scope['models'])).split(',')
    protos = args.protocols.split(',')
    seeds = [int(s) for s in args.seeds.split(',')]
    targets = args.targets.split(',')
    src = P / scope['src']
    out_root = Path(args.out_root) if args.out_root else P / scope['out']
    out_root.mkdir(parents=True, exist_ok=True)

    cfg = dict(purpose='prespecified max_features sensitivity', scope=args.scope,
               scope_note=scope['note'], source_root=scope['src'],
               representations=reps, models=models, protocols=protos, seeds=seeds,
               targets=targets, n_estimators=N_ESTIMATORS, max_features=MAX_FEATURES,
               n_jobs=args.n_jobs,
               reference_setting="max_features='sqrt' (experiment-12 frozen config)",
               folds='reused byte-for-byte from the archived split.npz; identical materials and splits',
               preprocessing='identical to experiment 12: G numerics + train-fitted one-hot blocks; T adds train-nonconstant Morgan parent-fingerprint bits',
               selection_rule='setting fixed before any fit; all seeds/targets/folds reported regardless of direction; no outer-test tuning',
               freeze_date='2026-10-23')
    cfg_path = out_root / 'frozen_config.json'
    if cfg_path.exists():
        old = json.loads(cfg_path.read_text(encoding='utf-8'))
        for k in ['scope', 'representations', 'max_features']:
            assert old[k] == cfg[k], (k, old[k], cfg[k])
    else:
        atomic_json(cfg_path, cfg)
    atomic_json(out_root / f'run_args_{args.scope}_{"_".join(map(str, seeds))}_{"_".join(targets)}.json', cfg)

    from diversity_control import NUMERIC_FEATURES
    cache = ROOT / '_cache' / 'hmof_meta.pkl'
    if cache.exists():
        raw = pd.read_pickle(cache)
        for c in raw.columns:
            if c not in NUMERIC_FEATURES:
                raw[c] = raw[c].astype(object)
    else:
        raw = pd.read_csv(ROOT / '03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv',
                          usecols=list(NUMERIC_FEATURES) + ['metal_linker', 'organic_linker1',
                                                            'organic_linker2', 'functional_groups',
                                                            'topology'], low_memory=False)
    bm = None
    lookup = None
    if 'T' in reps:
        bits = np.load(P / 'sources/morgan_parent_fingerprints.npz')
        lookup = {v: i for i, v in enumerate(bits['linker_id'].tolist())}
        bm = bits['bits']

    log = open(out_root / 'run.log', 'a', encoding='utf-8')
    t_all = time.monotonic()
    n_done = 0
    for stage in [s.strip() for s in args.stages.split(',')]:
        for seed in seeds:
            for target in targets:
                folder = src / f'n{stage}_seed{seed}_{target}'
                if not (folder / 'sample.csv.gz').exists():
                    print('MISSING', folder, flush=True)
                    continue
                sample = pd.read_csv(folder / 'sample.csv.gz')
                d = raw.iloc[sample.raw_row_id.to_numpy()].copy().reset_index(drop=True)
                for c in ['metal_linker', 'functional_groups', 'organic_linker1', 'organic_linker2', 'topology']:
                    d[c] = d[c].map(norm)
                num = d[NUMERIC_FEATURES].to_numpy(np.float32)
                y = sample.y_true.to_numpy()
                li = None
                if bm is not None:
                    li = np.column_stack([d[c].map(lookup).to_numpy() for c in ['organic_linker1', 'organic_linker2']])
                    assert np.isfinite(li).all()
                for protocol in protos:
                    fdirs = sorted([x for x in folder.iterdir() if x.is_dir() and x.name.startswith(protocol + '_fold')],
                                   key=lambda p: int(p.name.split('fold')[1]))
                    if args.max_folds:
                        fdirs = fdirs[:args.max_folds]
                    for fp in fdirs:
                        sp = np.load(fp / 'split.npz')
                        tr, te = sp['train_index'], sp['test_index']
                        if len(te) == 0:
                            continue
                        outdir = out_root / folder.name / fp.name
                        outdir.mkdir(parents=True, exist_ok=True)
                        todo = [(r, m) for r in reps for m in models
                                if not (outdir / f'prediction_{r}_{m}.npz').exists()]
                        if not todo:
                            continue
                        blocks = {}
                        for rep in reps:
                            blocks[rep] = build_one(rep, d, tr, te, num, li, bm)
                        for rep, mn in todo:
                            a, b = blocks[rep]
                            atomic_json(outdir / f'encoding_{rep}.json',
                                        dict(n_features=int(a.shape[1]), max_features=MAX_FEATURES))
                            start = time.monotonic()
                            cls = RandomForestRegressor if mn == 'RF' else ExtraTreesRegressor
                            mod = cls(n_estimators=N_ESTIMATORS, max_features=MAX_FEATURES,
                                      random_state=seed, n_jobs=args.n_jobs)
                            mod.fit(a, y[tr])
                            pred = mod.predict(b)
                            tmp = outdir / f'prediction_{rep}_{mn}.tmp.npz'
                            np.savez_compressed(tmp, raw_row_id=sample.raw_row_id.to_numpy()[te],
                                                y_true=y[te], prediction=pred,
                                                topology=d.topology.to_numpy()[te])
                            tmp.replace(outdir / f'prediction_{rep}_{mn}.npz')
                            el = time.monotonic() - start
                            atomic_json(outdir / f'model_{rep}_{mn}.json',
                                        dict(parameters=mod.get_params(), elapsed_seconds=el,
                                             n_train=int(len(tr)), n_test=int(len(te)),
                                             n_features=int(a.shape[1])))
                            msg = (f'{args.scope} {stage} {seed} {target} {protocol} {fp.name} {rep} {mn} '
                                   f'p={a.shape[1]} ntr={len(tr)} nte={len(te)} sec={el:.1f}')
                            print(msg, flush=True)
                            log.write(msg + '\n')
                            log.flush()
                            n_done += 1
                            del mod
                        del blocks
    log.write(f'DONE scope={args.scope} fits={n_done} total_sec={time.monotonic()-t_all:.1f}\n')
    log.close()
    print(f'ALL REQUESTED FITS FINISHED scope={args.scope} n={n_done} total_sec={time.monotonic()-t_all:.1f}', flush=True)


if __name__ == '__main__':
    main()
