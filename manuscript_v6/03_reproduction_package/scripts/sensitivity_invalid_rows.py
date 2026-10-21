#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Does dropping the non-physical descriptor rows change the *performance* results?

Paired design (only the preprocessing changes)
----------------------------------------------
* Sample and folds follow the production settings for the requested seed:
  `mof_leakage_benchmark.load_data` sampling rule, KFold for the random strategy,
  GroupKFold by topology for the grouped one; the *same* folds are used for both
  variants.
* Variant A ("historical") trains on every row of the sample; variant B
  ("cleaned") drops the rows with a negative descriptor from the **training**
  part of the same folds only.
* Both are scored on the **same legal test rows**, so a difference cannot come
  from changing the evaluation set.

Fidelity gate (fails closed)
----------------------------
Variant A scored on all rows is compared with the archived seed-specific
reference (`screening_utility_seed{N}.csv` for screening,
`arm_e_partner_coverage.csv` for the intervention arms). The gate validates the
table before comparing anything: required columns, the requested seed, the
analysis key set, exactly one aggregate row and one row per k for every
analysis x fit population x scoring scope, and finite values. A NaN, a missing
row, a duplicated row, a foreign seed or a missing reference **fails**; it is
never silently skipped. `--allow-missing-reference` downgrades only the
"reference file absent" case to exit code 2 with an explicit UNVERIFIED line,
and never prints a "reproduces" claim.

    # screening, seed 42
    python scripts/sensitivity_invalid_rows.py screening --source-scripts ../../03_投稿专用包/03_reproduction_package/scripts --csv ../../03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv --seed 42 --n-jobs 4 --out outputs/sensitivity_screening_seed42.csv --predictions-out outputs/predictions_screening_seed42.csv
    # arms, seed 42 (a/b/e)
    python scripts/sensitivity_invalid_rows.py arms --source-scripts ../../03_投稿专用包/03_reproduction_package/scripts --csv ../../03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv --seed 42 --n-jobs 4 --with-arm-e --out outputs/sensitivity_arms_seed42.csv --predictions-out outputs/predictions_arms_seed42.csv
    # re-check a finished table, or test the gate itself
    python scripts/sensitivity_invalid_rows.py screening --gate-only --seed 42 --out outputs/sensitivity_screening_seed42.csv
    python scripts/sensitivity_invalid_rows.py selftest

Archives (per mode and seed, so runs cannot overwrite each other):
    outputs/sensitivity_<mode>_seed<N>.csv        metrics (mean_n_train, seed)
    outputs/predictions_<mode>_seed<N>.csv        per-row predictions + fold sizes
    outputs/sensitivity_<mode>_seed<N>.json       provenance (inputs, versions)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parent.parent
OUT = PKG / "outputs"
NUMERIC = [
    "volume [A^3]", "weight [u]", "surface_area [m^2/g]", "void_fraction",
    "void_volume [cm^3/g]", "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
CHEM_KEYS = ["metal_linker", "organic_linker1", "organic_linker2"]
K_GRID = (0.01, 0.05, 0.10)
GATE_TOL = 5e-4
METRIC_COLS = ["analysis", "fit_population", "scoring_rows", "seed", "n",
               "mean_n_train", "k_frac", "k", "overlap_at_k", "oracle_topk_mean",
               "selected_topk_mean", "regret", "r2", "mae", "sst"]
PRED_COLS = ["mode", "seed", "row_index", "raw_row_index", "fold",
             "n_train_fold", "n_test_fold", "legal", "strategy",
             "fit_population", "y_true", "y_pred"]


# --------------------------------------------------------------------------
# loading and fitting
# --------------------------------------------------------------------------
def load_mb(src: Path, seed: int):
    sys.path.insert(0, str(src))
    import mof_leakage_benchmark as mb  # noqa: PLC0415
    mb.RANDOM_STATE = seed
    mb.N_JOBS_OVERRIDE = 1
    return mb


def load_with_index(csv_path: Path, max_rows: int, seed: int):
    """Replicate mb.load_data but keep the raw CSV row numbers."""
    df = pd.read_csv(csv_path)
    if max_rows and max_rows < len(df):
        df = df.sample(max_rows, random_state=seed)
    raw_index = df.index.to_numpy()
    return df.reset_index(drop=True), raw_index


def legal_mask(dclean: pd.DataFrame) -> np.ndarray:
    bad = np.zeros(len(dclean), dtype=bool)
    for col in NUMERIC:
        bad |= pd.to_numeric(dclean[col], errors="coerce").to_numpy() < 0
    return ~bad


def _fit_predict(X, y, tr, te, seed):
    from sklearn.ensemble import RandomForestRegressor
    mdl = RandomForestRegressor(n_estimators=120, random_state=seed, n_jobs=1)
    mdl.fit(X.iloc[tr], y.iloc[tr])
    return mdl.predict(X.iloc[te])


def metrics(y_true, y_pred, legal, analysis, fit_population, seed, mean_n_train, out):
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    for scope, idx in (("all_rows", np.ones(len(y_true), bool)), ("legal_rows", legal)):
        yt, yp = y_true[idx], y_pred[idx]
        n = len(yt)
        for kf in K_GRID:
            k = max(1, int(round(kf * n)))
            true_top = set(np.argsort(-yt, kind="stable")[:k])
            pred_top = set(np.argsort(-yp, kind="stable")[:k])
            oracle = float(np.mean(yt[list(true_top)]))
            sel = float(np.mean(yt[list(pred_top)]))
            out.append(dict(analysis=analysis, fit_population=fit_population,
                            scoring_rows=scope, seed=seed, n=n,
                            mean_n_train=mean_n_train, k_frac=kf, k=k,
                            overlap_at_k=len(true_top & pred_top) / k,
                            oracle_topk_mean=oracle, selected_topk_mean=sel,
                            regret=oracle - sel))
        ss_res = float(np.sum((yt - yp) ** 2))
        ss_tot = float(np.sum((yt - yt.mean()) ** 2))
        out.append(dict(analysis=analysis, fit_population=fit_population,
                        scoring_rows=scope, seed=seed, n=n,
                        mean_n_train=mean_n_train, k_frac=-1, k="",
                        overlap_at_k="", oracle_topk_mean=yt.mean(),
                        selected_topk_mean=yp.mean(), regret="",
                        r2=1.0 - ss_res / ss_tot if ss_tot else float("nan"),
                        mae=float(np.mean(np.abs(yt - yp))), sst=ss_tot))


def run_screening(mb, csv_path, seed, max_rows, n_jobs, out, pred_rows):
    from concurrent.futures import ThreadPoolExecutor
    from sklearn.model_selection import GroupKFold, KFold

    df, raw_index = load_with_index(csv_path, max_rows, seed)
    X, y, groups, cats, dclean = mb.build_features(df)
    legal = legal_mask(dclean)
    print(f"[screening seed={seed}] n={len(y)}, non-physical rows={int((~legal).sum())}",
          flush=True)

    folds = {
        "random": list(KFold(5, shuffle=True, random_state=seed).split(X)),
        "topology": list(GroupKFold(
            n_splits=max(2, min(5, groups["topology"].nunique()))
        ).split(X, y, groups=groups["topology"].values)),
    }
    every = np.ones(len(y), bool)
    for strategy, fl in folds.items():
        fold_id = np.full(len(y), -1)
        for fid, (tr, te) in enumerate(fl):
            fold_id[te] = fid
        for fit_pop, keep in (("historical", every), ("cleaned", legal)):
            def job(item):
                tr, te = item
                tr_use = tr[keep[tr]]
                return te, _fit_predict(X, y, tr_use, te, seed), len(tr_use), len(te)

            pred = np.full(len(y), np.nan)
            n_train_fold = np.full(len(y), -1)
            n_test_fold = np.full(len(y), -1)
            with ThreadPoolExecutor(max_workers=max(1, n_jobs)) as pool:
                for te, p, ntr, nte in pool.map(job, fl):
                    pred[te] = p
                    n_train_fold[te] = ntr
                    n_test_fold[te] = nte
            assert not np.isnan(pred).any(), "some rows were never predicted"
            # equal weight per fold, not per test row: the topology folds differ
            # in size, so a row-weighted mean would describe a different quantity
            per_fold = [int(n_train_fold[fold_id == f][0]) for f in range(len(fl))]
            mean_n_train = int(round(float(np.mean(per_fold))))
            metrics(y, pred, legal, f"screening::{strategy}", fit_pop, seed,
                    mean_n_train, out)
            for i in range(len(y)):
                pred_rows.append(dict(
                    mode="screening", seed=seed, row_index=i,
                    raw_row_index=int(raw_index[i]), fold=int(fold_id[i]),
                    n_train_fold=int(n_train_fold[i]), n_test_fold=int(n_test_fold[i]),
                    legal=bool(legal[i]), strategy=strategy,
                    fit_population=fit_pop, y_true=float(y.iloc[i]),
                    y_pred=float(pred[i])))
            print(f"  {strategy}/{fit_pop}: mean_n_train={mean_n_train}", flush=True)
    return len(y)


def run_arms(mb, csv_path, seed, max_rows, n_jobs, with_e, out, pred_rows):
    from concurrent.futures import ThreadPoolExecutor

    df, raw_index = load_with_index(csv_path, max_rows, seed)
    X, y, groups, cats, dclean = mb.build_features(df)
    legal = legal_mask(dclean)
    topo = dclean["topology"].astype(str).to_numpy()
    keys = dclean[CHEM_KEYS].astype(str).agg("|".join, axis=1).to_numpy()
    print(f"[arms seed={seed}] n={len(y)}, non-physical rows={int((~legal).sum())}",
          flush=True)

    jobs = []
    for test_topo, partner in (("nbo", "pcu"), ("pcu", "nbo")):
        te = np.where(topo == test_topo)[0]
        shared = set(keys[te])
        arm_masks = {"a": (topo != test_topo),
                     "b": (topo != test_topo) & (topo != partner)}
        if with_e:
            drop_shared = (topo == partner) & np.isin(keys, list(shared))
            arm_masks["e"] = (topo != test_topo) & ~drop_shared
        for arm, keep_rows in arm_masks.items():
            for fit_pop, keep in (("historical", np.ones(len(y), bool)),
                                  ("cleaned", legal)):
                tr = np.where(keep_rows)[0]
                tr = tr[keep[tr]]
                jobs.append((test_topo, arm, fit_pop, tr, te))

    def one(job):
        test_topo, arm, fit_pop, tr, te = job
        return job, _fit_predict(X, y, tr, te, seed)

    with ThreadPoolExecutor(max_workers=max(1, n_jobs)) as pool:
        for (test_topo, arm, fit_pop, tr, te), pred in pool.map(one, jobs):
            metrics(y.iloc[te], pred, legal[te], f"arms::{test_topo}::{arm}",
                    fit_pop, seed, len(tr), out)
            for j, i in enumerate(te):
                pred_rows.append(dict(
                    mode="arms", seed=seed, row_index=int(i),
                    raw_row_index=int(raw_index[i]), fold=-1,
                    n_train_fold=len(tr), n_test_fold=len(te),
                    legal=bool(legal[i]), strategy=f"{test_topo}:{arm}",
                    fit_population=fit_pop, y_true=float(y.iloc[i]),
                    y_pred=float(pred[j])))
            print(f"  arm {test_topo}/{arm}/{fit_pop}: n_train={len(tr)}", flush=True)
    return len(y)


# --------------------------------------------------------------------------
# fidelity gate: fails closed
# --------------------------------------------------------------------------
def _finite(v) -> bool:
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def _validate_table(mode: str, seed: int, frame: pd.DataFrame) -> list[str]:
    problems: list[str] = []
    missing = [c for c in METRIC_COLS if c not in frame.columns]
    if missing:
        return [f"metrics table lacks columns {missing}"]

    seeds = sorted({int(s) for s in frame["seed"].astype(int)})
    if seeds != [seed]:
        problems.append(f"table seed(s) {seeds} != requested {seed}")

    analyses = sorted(set(frame["analysis"].astype(str)))
    if mode == "screening":
        expected = {f"screening::{s}" for s in ("random", "topology")}
        if set(analyses) != expected:
            problems.append(f"analysis set {analyses} != {sorted(expected)}")
    else:
        if not analyses or not all(a.startswith("arms::") for a in analyses):
            problems.append(f"analysis set {analyses} is not an arms table")

    for analysis in analyses:
        for pop in ("historical", "cleaned"):
            sub = frame[(frame["analysis"] == analysis)
                        & (frame["fit_population"] == pop)]
            if sub.empty:
                problems.append(f"{analysis}/{pop}: no rows")
                continue
            for scope in ("all_rows", "legal_rows"):
                s2 = sub[sub["scoring_rows"] == scope]
                if s2.empty:
                    problems.append(f"{analysis}/{pop}/{scope}: no rows")
                    continue
                agg = s2[np.isclose(pd.to_numeric(s2["k_frac"], errors="coerce"), -1)]
                if len(agg) != 1:
                    problems.append(f"{analysis}/{pop}/{scope}: expected exactly one "
                                    f"aggregate row, got {len(agg)}")
                else:
                    for col in ("r2", "mae", "sst"):
                        if not _finite(agg[col].iloc[0]):
                            problems.append(f"{analysis}/{pop}/{scope}: {col} is not finite")
                for kf in K_GRID:
                    rows = s2[np.isclose(pd.to_numeric(s2["k_frac"], errors="coerce"), kf)]
                    if len(rows) != 1:
                        problems.append(f"{analysis}/{pop}/{scope}: expected one row at "
                                        f"k={kf}, got {len(rows)}")
                        continue
                    if not _finite(rows["overlap_at_k"].iloc[0]):
                        problems.append(f"{analysis}/{pop}/{scope}: overlap at k={kf} "
                                        "is not finite")
    keys = frame[["analysis", "fit_population", "scoring_rows", "k_frac"]].astype(str)
    if keys.duplicated().any():
        problems.append("duplicated (analysis, population, scope, k) rows")
    return problems


ALLOWED_ARMS = ("a", "b", "e")


def _arms_in_table(frame: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (arms present, unknown analysis keys)."""
    arms, unknown = set(), []
    for a in frame["analysis"].astype(str):
        m = re.match(r"arms::([^:]+)::(.+)$", a)
        if not m:
            unknown.append(a)
            continue
        if m.group(2) not in ALLOWED_ARMS:
            unknown.append(a)
            continue
        arms.add(m.group(2))
    return sorted(arms), unknown


def gate(mode: str, seed: int, frame: pd.DataFrame, ref_dir: Path,
         allow_missing: bool = False,
         expect_arms: list[str] | None = None) -> tuple[str, list[str]]:
    """Return ('verified' | 'failed' | 'unverified', notes/problems)."""
    problems = _validate_table(mode, seed, frame)
    if problems:
        return "failed", problems

    hist = frame[(frame["fit_population"] == "historical")
                 & (frame["scoring_rows"] == "all_rows")]
    notes: list[str] = []

    if mode == "screening":
        ref_path = ref_dir / f"screening_utility_seed{seed}.csv"
        if not ref_path.exists():
            msg = [f"reference {ref_path.name} is not archived for seed {seed}"]
            return ("unverified", msg) if allow_missing else ("failed", msg)
        ref = pd.read_csv(ref_path)
        for strategy in ("random", "topology"):
            r = ref[ref["strategy"] == strategy]
            if r.empty:
                problems.append(f"reference has no rows for strategy {strategy}")
                continue
            for kf in K_GRID:
                want = r[np.isclose(r["k_frac"], kf)]["overlap_at_k"]
                got = hist[(hist["analysis"] == f"screening::{strategy}")
                           & np.isclose(pd.to_numeric(hist["k_frac"]), kf)]["overlap_at_k"]
                if len(want) != 1:
                    problems.append(f"reference {strategy} k={kf}: {len(want)} rows")
                elif not _finite(want.iloc[0]):
                    problems.append(f"reference {strategy} k={kf}: overlap is not finite")
                elif len(got) != 1:
                    problems.append(f"table {strategy} k={kf}: {len(got)} rows")
                elif abs(float(got.iloc[0]) - float(want.iloc[0])) > GATE_TOL:
                    problems.append(f"{strategy} k={kf}: run {got.iloc[0]:.4f} != "
                                    f"reference {want.iloc[0]:.4f}")
            for ref_col, got_col in (("R2", "r2"), ("MAE", "mae")):
                want = r[np.isclose(r["k_frac"], 0.01)][ref_col]
                got = hist[(hist["analysis"] == f"screening::{strategy}")
                           & (pd.to_numeric(hist["k_frac"]) < 0)][got_col]
                if len(want) != 1:
                    problems.append(f"reference {strategy} {ref_col}: {len(want)} rows")
                elif not _finite(want.iloc[0]):
                    problems.append(f"reference {strategy} {ref_col} is not finite")
                elif len(got) != 1:
                    problems.append(f"table {strategy} {ref_col}: {len(got)} rows")
                elif not _finite(got.iloc[0]):
                    problems.append(f"table {strategy} {ref_col} is not finite")
                elif abs(float(got.iloc[0]) - float(want.iloc[0])) > GATE_TOL:
                    problems.append(f"{strategy} {ref_col}: run {got.iloc[0]:.4f} != "
                                    f"reference {want.iloc[0]:.4f}")
    else:
        ref_path = ref_dir / "arm_e_partner_coverage.csv"
        if not ref_path.exists():
            msg = [f"reference {ref_path.name} is not archived"]
            return ("unverified", msg) if allow_missing else ("failed", msg)
        ref = pd.read_csv(ref_path)
        arms, unknown = _arms_in_table(frame)
        if unknown:
            problems.append(f"unknown arm key(s) in the table: {unknown}")
        if expect_arms is not None:
            if sorted(expect_arms) != arms:
                problems.append(f"arm set {arms} != declared {sorted(expect_arms)}")
        regime = {"a": "a_with_partner", "b": "b_partner_removed",
                  "e": "e_shared_only_removed"}
        notes.append("arms checked: " + ", ".join(arms)
                     + ("" if "e" in arms else " (e not run in this table)"))
        for topo in ("nbo", "pcu"):
            for arm in arms:
                want = ref[(ref["seed"] == seed) & (ref["test_topo"] == topo)
                           & (ref["regime"] == regime[arm])]["MAE"]
                got = hist[(hist["analysis"] == f"arms::{topo}::{arm}")
                           & (pd.to_numeric(hist["k_frac"]) < 0)]["mae"]
                if len(want) != 1:
                    problems.append(f"reference {topo}/{arm}: {len(want)} rows for "
                                    f"seed {seed}")
                elif not _finite(want.iloc[0]):
                    problems.append(f"reference {topo}/{arm}: MAE is not finite")
                elif len(got) != 1:
                    problems.append(f"table {topo}/{arm}: {len(got)} rows")
                elif not _finite(got.iloc[0]):
                    problems.append(f"table {topo}/{arm}: MAE is not finite")
                elif abs(float(got.iloc[0]) - float(want.iloc[0])) > GATE_TOL:
                    problems.append(f"{topo}/{arm}: run {got.iloc[0]:.4f} != "
                                    f"reference {want.iloc[0]:.4f}")
    if problems:
        return "failed", problems + notes
    return "verified", notes


def _report(status: str, problems: list[str]) -> int:
    for p in problems:
        print(("  - " if status == "failed" else "  ") + str(p))
    if status == "verified":
        print("gate: VERIFIED - variant A reproduces the archived reference")
        return 0
    if status == "unverified":
        print("gate: UNVERIFIED - no comparison was performed; this run must not be "
              "described as reproducing the reference")
        return 2
    print("gate: FAILED - this run is not a faithful reproduction of the reference")
    return 1


# --------------------------------------------------------------------------
# in-memory self-test: every corruption must be rejected
# --------------------------------------------------------------------------
def recheck_selftest(mode: str, out: Path, pred: Path,
                     arms: list[str] | None = None) -> int:
    """Corrupted predictions/metrics must make recheck fail."""
    import copy
    base_m = pd.read_csv(out)
    base_p = pd.read_csv(pred)
    fails = 0

    def expect(name, met, prd, want, arms_=None):
        nonlocal fails
        with tempfile_mut(met, prd) as (mp, pp):
            got = recheck(mode, int(prd["seed"].iloc[0]) if len(prd) else 42, mp, pp,
                          arms=arms_ if arms_ is not None else arms)
        got = 0 if got == 0 else 1
        flag = "ok" if got == want else "MISMATCH"
        print(f"{name:<44s} want={want} got={got:<2d} {flag}")
        if got != want:
            fails += 1

    expect("pristine metrics/predictions", base_m, base_p, 0)

    empty = base_p.iloc[0:0]
    expect("predictions table emptied", base_m, empty, 1)
    expect("metrics table emptied", base_m.iloc[0:0], base_p, 1)

    def nan_mae(m):
        m = m.copy()
        # an aggregate row, not a k row: k rows legitimately have a blank MAE
        i = m[np.isclose(pd.to_numeric(m.k_frac), -1)].index[0]
        m.loc[i, "mae"] = np.nan
        return m

    expect("MAE = NaN", nan_mae(base_m), base_p, 1)

    def wrong_seed(m):
        m = m.copy()
        m["seed"] = 143
        return m

    expect("metrics seed = 143", wrong_seed(base_m), base_p, 1)

    def bad_regret(m):
        m = m.copy()
        i = m[np.isclose(pd.to_numeric(m.k_frac), 0.01)].index[0]
        m.loc[i, "regret"] = 999.0
        return m

    expect("regret = 999", bad_regret(base_m), base_p, 1)

    def bad_sst(m):
        m = m.copy()
        i = m[np.isclose(pd.to_numeric(m.k_frac), -1)].index[0]
        m.loc[i, "sst"] = 1.0
        return m

    expect("sst = 1", bad_sst(base_m), base_p, 1)

    def drop_group(m):
        first = m.analysis.iloc[0]
        return m[m.analysis != first]

    expect("metric group deleted", drop_group(base_m), base_p, 1)

    def drop_pred_rows(p):
        g = p[(p.strategy == p.strategy.iloc[0]) & (p.fit_population == "cleaned")]
        return p.drop(index=g.index[:50])

    expect("prediction rows deleted", base_m, drop_pred_rows(base_p), 1)

    if mode == "arms":
        # both sides lose a whole group -> the declared design is not met
        def drop_group_both(m, p):
            keep = "arms::nbo::e"
            m2 = m[m.analysis != keep]
            p2 = p[~((p.strategy == "nbo:e"))]
            return m2, p2

        m2, p2 = drop_group_both(base_m, base_p)
        expect("group deleted on both sides", m2, p2, 1)

        # a metric-only extra group must be rejected
        def add_metric_group(m):
            extra = m[m.analysis == "arms::nbo::a"].copy()
            extra["analysis"] = "arms::nbo::x"
            return pd.concat([m, extra], ignore_index=True)

        expect("metric-only extra group", add_metric_group(base_m), base_p, 1)

        # duplicate metric key
        def duplicate_key(m):
            i = m[(m.analysis == "arms::pcu::b") & (m.scoring_rows == "all_rows")
                  & np.isclose(pd.to_numeric(m.k_frac), 0.05)].index[0]
            return pd.concat([m, m.loc[[i]]], ignore_index=True)

        expect("duplicate metric key", duplicate_key(base_m), base_p, 1)

        # a legitimate a/b design passes when declared
        keep_ab = lambda d, col: d[~d[col].astype(str).str.endswith("e")
                                   & ~d[col].astype(str).str.contains(":e")]
        m_ab = base_m[~base_m.analysis.str.endswith("::e")]
        p_ab = base_p[~base_p.strategy.str.endswith(":e")]
        expect("legitimate a/b design", m_ab, p_ab, 0, arms_=["a", "b"])
        expect("declared a,b,e but only a,b present", m_ab, p_ab, 1,
               arms_=["a", "b", "e"])

        # unknown strategy/arm in the predictions
        def rename_arm(p):
            p = p.copy()
            p["strategy"] = p["strategy"].str.replace("nbo:a", "nbo:z", regex=False)
            return p

        expect("unknown arm in predictions", base_m, rename_arm(base_p), 1)

    print("\nOK - every recheck case behaved as expected (positive cases pass, corrupted copies fail)" if not fails
          else f"\nFAIL - {fails} recheck case(s) behaved incorrectly")
    return 0 if not fails else 1


class tempfile_mut:
    """Write modified copies to the package scratch area (the sandbox denies the
    platform temp directory) and remove them afterwards."""

    def __init__(self, met, prd):
        import pandas as _pd
        self.met, self.prd = met, prd
        self.dir = PKG / "_selftest_recheck_dir_"

    def __enter__(self):
        self.dir.mkdir(exist_ok=True)
        mp = self.dir / "metrics.csv"
        pp = self.dir / "predictions.csv"
        self.met.to_csv(mp, index=False)
        self.prd.to_csv(pp, index=False)
        return mp, pp

    def __exit__(self, *exc):
        for f in self.dir.glob("*.csv"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            self.dir.rmdir()
        except OSError:
            pass
        return False


def selftest(screen_csv: Path, arms_csv: Path, ref_dir: Path) -> int:
    base_s = pd.read_csv(screen_csv)
    base_a = pd.read_csv(arms_csv)
    seed = int(base_s["seed"].iloc[0])
    fails = 0

    def expect(name, mode, frame, want, allow_missing=False, ref=None):
        nonlocal fails
        status, _ = gate(mode, seed, frame, Path(ref or ref_dir),
                         allow_missing=allow_missing)
        got = {"verified": 0, "failed": 1, "unverified": 2}[status]
        flag = "ok" if got == want else "MISMATCH"
        print(f"{name:<44s} want={want} got={got:<2d} {flag}")
        if got != want:
            fails += 1

    expect("pristine screening", "screening", base_s, 0)
    expect("pristine arms", "arms", base_a, 0)

    def mut(frame, fn):
        return fn(frame.copy())

    def nan_overlap(d):
        i = d[(d.fit_population == "historical") & (d.scoring_rows == "all_rows")
              & np.isclose(pd.to_numeric(d.k_frac), 0.01)].index[0]
        d.loc[i, "overlap_at_k"] = np.nan
        return d

    expect("historical overlap = NaN", "screening", mut(base_s, nan_overlap), 1)

    def nan_mae(d):
        i = d[(d.analysis == "screening::topology") & (d.fit_population == "cleaned")
              & (d.scoring_rows == "legal_rows")
              & (pd.to_numeric(d.k_frac) < 0)].index[0]
        d.loc[i, "mae"] = np.nan
        return d

    expect("aggregate MAE = NaN", "screening", mut(base_s, nan_mae), 1)

    def drop_aggregate(d):
        i = d[(d.analysis == "screening::random") & (d.fit_population == "cleaned")
              & (d.scoring_rows == "all_rows")
              & (pd.to_numeric(d.k_frac) < 0)].index
        return d.drop(index=i)

    expect("R2/MAE aggregate row deleted", "screening", mut(base_s, drop_aggregate), 1)

    def wrong_seed(d):
        d["seed"] = 143
        return d

    expect("table seed = 143 (requested 42)", "screening", mut(base_s, wrong_seed), 1)

    def duplicate_aggregate(d):
        i = d[(d.analysis == "screening::random") & (d.fit_population == "historical")
              & (d.scoring_rows == "all_rows")
              & (pd.to_numeric(d.k_frac) < 0)].index[0]
        return pd.concat([d, d.loc[[i]]], ignore_index=True)

    expect("aggregate row duplicated", "screening", mut(base_s, duplicate_aggregate), 1)

    def drop_k_row(d):
        i = d[(d.analysis == "screening::topology") & (d.fit_population == "historical")
              & (d.scoring_rows == "legal_rows")
              & np.isclose(pd.to_numeric(d.k_frac), 0.05)].index
        return d.drop(index=i)

    expect("k=5% row deleted", "screening", mut(base_s, drop_k_row), 1)

    # a plain mkdtemp, not TemporaryDirectory: the sandbox refuses the rmtree
    # performed on context exit, and a failed cleanup must not mask a test result
    # a path that is never created: the gate must fail rather than pass
    # a reference with non-finite values must fail, like any other corruption
    ref_tmp = PKG / "_selftest_bad_reference_dir_"
    ref_tmp.mkdir(exist_ok=True)
    try:
        ref = pd.read_csv(ref_dir / f"screening_utility_seed{seed}.csv")
        for label, col, val in (("overlap NaN", "overlap_at_k", np.nan),
                                ("R2 NaN", "R2", np.nan),
                                ("MAE inf", "MAE", np.inf)):
            bad = ref.copy()
            bad.loc[bad.index[0], col] = val
            bad.to_csv(ref_tmp / f"screening_utility_seed{seed}.csv", index=False)
            status, _ = gate("screening", seed, base_s, ref_tmp)
            got = {"verified": 0, "failed": 1, "unverified": 2}[status]
            print(f"reference {label:<36s} want=1 got={got:<2d} "
                  f"{'ok' if got == 1 else 'MISMATCH'}")
            if got != 1:
                fails += 1
    finally:
        for f in ref_tmp.glob("*.csv"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            ref_tmp.rmdir()
        except OSError:
            pass

    empty = PKG / "_selftest_missing_reference_dir_"
    expect("reference file missing", "screening", base_s, 1, ref=empty)
    expect("reference missing + allow flag", "screening", base_s, 2,
           allow_missing=True, ref=empty)

    arms_ab = base_a[~base_a.analysis.str.endswith("::e")]
    expect("arms table without e (a,b only)", "arms", arms_ab, 0)

    def relabel_arm(d):
        d = d.copy()
        d["analysis"] = d["analysis"].str.replace(r"::a$", "::x", regex=True)
        return d

    expect("arm renamed a -> x (unknown arm)", "arms", relabel_arm(base_a), 1,
           ref=ref_dir)
    # and with an explicitly declared set the missing arm must fail as well
    status, _ = gate("arms", seed, arms_ab, Path(ref_dir), expect_arms=["a", "b", "e"])
    got = {"verified": 0, "failed": 1, "unverified": 2}[status]
    print(f"{'declared a,b,e but table has only a,b':<44s} want=1 got={got:<2d} "
          f"{'ok' if got == 1 else 'MISMATCH'}")
    if got != 1:
        fails += 1

    # the modified reference lives inside the package (the sandbox denies writes
    # to the platform temp directory) and is removed afterwards
    tmp = PKG / "_selftest_ref_dir_"
    tmp.mkdir(exist_ok=True)
    try:
        ref = pd.read_csv(ref_dir / "arm_e_partner_coverage.csv")
        ref[ref.regime == "e_shared_only_removed"].to_csv(
            tmp / "arm_e_partner_coverage.csv", index=False)
        expect("reference lacks e rows", "arms", base_a, 1, ref=tmp)
    finally:
        try:
            (tmp / "arm_e_partner_coverage.csv").unlink(missing_ok=True)
            tmp.rmdir()
        except OSError:
            pass

    print("\n-- gate: " + ("every case behaved as expected"
                             if not fails else f"{fails} case(s) wrong"))
    r1 = recheck_selftest("screening",
                          OUT / "sensitivity_screening_seed42.csv",
                          OUT / "predictions_screening_seed42.csv")
    r2 = recheck_selftest("arms",
                          OUT / "sensitivity_arms_seed42.csv",
                          OUT / "predictions_arms_seed42.csv",
                          arms=["a", "b", "e"])
    fails += (1 if r1 else 0) + (1 if r2 else 0)
    print("\nOK - every gate and recheck case behaved as expected (positive cases pass, corrupted copies fail)"
          if not fails else f"\nFAIL - {fails} case(s) behaved incorrectly")
    return 0 if not fails else 1


# --------------------------------------------------------------------------
def expected_groups(mode: str, arms: list[str]) -> list[tuple[str, str]]:
    """The design the archive is supposed to contain: (strategy, population)."""
    pops = ("historical", "cleaned")
    if mode == "screening":
        return [(s, p) for s in ("random", "topology") for p in pops]
    return [(f"{t}:{a}", p) for t in ("nbo", "pcu") for a in arms for p in pops]


def recheck(mode: str, seed: int, out: Path, pred_path: Path,
            arms: list[str] | None = None) -> int:
    """Recompute every metric cell from the archived per-row predictions.

    The expected design is declared, not inferred from the table under test:
    screening is random/topology x historical/cleaned; arms is nbo/pcu x the
    declared arm set x the two populations. Missing groups, extra groups,
    unknown strategies/arms, duplicate keys and non-finite values all fail.
    """
    problems: list[str] = []
    arms = arms if arms is not None else ["a", "b", "e"]
    met = pd.read_csv(out)
    prd = pd.read_csv(pred_path)
    if prd.empty:
        return _recheck_fail([f"{pred_path.name} has no rows"])
    if met.empty:
        return _recheck_fail([f"{out.name} has no rows"])
    missing_p = [c for c in PRED_COLS if c not in prd.columns]
    missing_m = [c for c in METRIC_COLS if c not in met.columns]
    if missing_p or missing_m:
        return _recheck_fail([f"missing columns: predictions {missing_p}, metrics {missing_m}"])
    if set(int(x) for x in prd["seed"].unique()) != {seed} or \
            set(int(x) for x in met["seed"].unique()) != {seed}:
        problems.append(f"seed column does not match the requested {seed}")
    if sorted(prd["mode"].unique()) != [mode]:
        problems.append(f"prediction mode {sorted(prd['mode'].unique())} != {mode}")
    if prd.duplicated(["strategy", "fit_population", "row_index"]).any():
        problems.append("duplicated (strategy, population, row_index) keys")
    for col in ("y_true", "y_pred", "row_index", "raw_row_index"):
        if not np.isfinite(pd.to_numeric(prd[col], errors="coerce")).all():
            problems.append(f"{col} contains non-finite values")

    # ---- expected groups vs both tables
    want_groups = set(expected_groups(mode, arms))
    prd_groups = set(zip(prd["strategy"].astype(str), prd["fit_population"].astype(str)))
    if prd_groups != want_groups:
        problems.append(f"prediction groups differ from the declared design: "
                        f"missing={sorted(want_groups - prd_groups)} "
                        f"extra={sorted(prd_groups - want_groups)}")
    name = (lambda a: f"screening::{a}") if mode == "screening" else \
           (lambda a: f"arms::{a.replace(':', '::')}")
    want_names = {name(grp[0]): grp[0] for grp in want_groups}
    met_names = set(met["analysis"].astype(str))
    allowed_names = ({"screening::random", "screening::topology"} if mode == "screening"
                     else {f"arms::{t}::{a}" for t in ("nbo", "pcu") for a in arms})
    unknown = sorted(met_names - allowed_names)
    if unknown:
        problems.append(f"unknown metric analysis keys: {unknown}")
    missing_names = sorted(set(want_names) - met_names)
    if missing_names:
        problems.append(f"metric groups missing for the declared design: {missing_names}")
    if met_names - set(want_names) - set(unknown):
        problems.append(f"unexpected metric analysis keys: "
                        f"{sorted(met_names - set(want_names) - set(unknown))}")

    # ---- population pairing
    for strat, g in prd.groupby("strategy"):
        h = g[g["fit_population"] == "historical"].sort_values("row_index")
        c = g[g["fit_population"] == "cleaned"].sort_values("row_index")
        if len(h) == 0 or len(c) == 0:
            problems.append(f"{strat}: a population is empty")
            continue
        if len(h) != len(c) or not (h["row_index"].to_numpy() == c["row_index"].to_numpy()).all():
            problems.append(f"{strat}: historical/cleaned row sets differ")
            continue
        for col in ("y_true", "legal", "fold", "raw_row_index"):
            if not (h[col].to_numpy() == c[col].to_numpy()).all():
                problems.append(f"{strat}: {col} differs between populations")

    # ---- metric keys: exactly one aggregate row and one row per k per group/scope
    key_cols = ["analysis", "fit_population", "scoring_rows", "k_frac"]
    dup = met.duplicated(key_cols)
    if dup.any():
        problems.append(f"duplicated metric keys: {int(dup.sum())} row(s)")

    # ---- recompute every cell
    for (analysis, pop), g in prd.groupby(["strategy", "fit_population"]):
        nm = name(analysis)
        sub = met[(met["analysis"] == nm) & (met["fit_population"] == pop)]
        g = g.sort_values("row_index")
        y = g["y_true"].to_numpy(float)
        p = g["y_pred"].to_numpy(float)
        legal = g["legal"].to_numpy(bool)
        for scope, idx in (("all_rows", np.ones(len(y), bool)), ("legal_rows", legal)):
            yt, yp = y[idx], p[idx]
            n = len(yt)
            ss = float(np.sum((yt - yp) ** 2))
            st = float(np.sum((yt - yt.mean()) ** 2))
            expect = {"n": n, "mae": float(np.mean(np.abs(yt - yp))),
                      "r2": 1.0 - ss / st if st else float("nan"), "sst": st}
            for kf in K_GRID:
                k = max(1, int(round(kf * n)))
                tt = np.argsort(-yt, kind="stable")[:k]
                pt = np.argsort(-yp, kind="stable")[:k]
                expect[f"k={kf}"] = {"k": k,
                                     "overlap_at_k": len(set(tt) & set(pt)) / k,
                                     "oracle_topk_mean": float(np.mean(yt[tt])),
                                     "selected_topk_mean": float(np.mean(yt[pt])),
                                     "regret": float(np.mean(yt[tt]) - np.mean(yt[pt]))}
            block = sub[sub["scoring_rows"] == scope]
            agg = block[np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), -1)]
            if len(agg) != 1:
                problems.append(f"{nm}/{pop}/{scope}: {len(agg)} aggregate rows")
            else:
                row = agg.iloc[0]
                for col in ("n", "mae", "r2", "sst"):
                    if not _finite(row[col]) or abs(float(row[col]) - expect[col]) > 1e-6:
                        problems.append(f"{nm}/{pop}/{scope}/{col}: table {row[col]} "
                                        f"vs recomputed {expect[col]}")
                # training-size metadata: equal-weight mean over folds / single fit
                ntr = pd.to_numeric(g["n_train_fold"], errors="coerce")
                if (ntr < 0).any():
                    problems.append(f"{nm}/{pop}: n_train_fold has negative values")
                else:
                    if mode == "screening":
                        per_fold = g.groupby("fold")["n_train_fold"].agg("first")
                        want_n = int(round(float(per_fold.mean())))
                    else:
                        want_n = int(round(float(ntr.iloc[0])))
                    if int(row["mean_n_train"]) != want_n:
                        problems.append(f"{nm}/{pop}: mean_n_train {row['mean_n_train']} "
                                        f"!= {want_n}")
            for kf in K_GRID:
                rows = block[np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), kf)]
                if len(rows) != 1:
                    problems.append(f"{nm}/{pop}/{scope}: {len(rows)} rows at k={kf}")
                    continue
                row = rows.iloc[0]
                want = expect[f"k={kf}"]
                for col in ("k", "overlap_at_k", "oracle_topk_mean",
                            "selected_topk_mean", "regret"):
                    if not _finite(row[col]) or abs(float(row[col]) - want[col]) > 1e-6:
                        problems.append(f"{nm}/{pop}/{scope} k={kf}/{col}: table "
                                        f"{row[col]} vs recomputed {want[col]}")
            extra = block[~np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), -1)
                          & ~np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), 0.01)
                          & ~np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), 0.05)
                          & ~np.isclose(pd.to_numeric(block["k_frac"], errors="coerce"), 0.10)]
            if not extra.empty:
                problems.append(f"{nm}/{pop}/{scope}: unexpected k rows "
                                f"{sorted(extra['k_frac'].unique())}")
    if problems:
        return _recheck_fail(problems)
    print(f"recheck: OK - {out.name}: declared design {len(want_groups)} groups, "
          f"recomputed overlap/oracle/selected/regret/r2/mae/sst/n/k and "
          f"mean_n_train from {pred_path.name}")
    return 0


def _recheck_fail(problems: list[str]) -> int:
    print("recheck: FAILED")
    for p in problems:
        print("  -", p)
    return 1


# --------------------------------------------------------------------------
def provenance(csv_path: Path, mode: str, seed: int, n_sampled: int, n_raw: int,
               n_pred: int, n_metric: int, hash_note: str,
               n_unique: int | None = None) -> dict:
    def md5(p):
        h = hashlib.md5()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    return {
        "mode": mode,
        "seed": seed,
        "n_rows_sampled": int(n_sampled),
        "n_unique_scored_rows": int(n_unique),
        "n_prediction_records": int(n_pred),
        "n_metric_records": int(n_metric),
        "n_rows_in_input": int(n_raw),
        "input_csv": csv_path.name,
        "input_md5": md5(csv_path),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "script_sha256_note": hash_note,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "sklearn": __import__("sklearn").__version__,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["screening", "arms", "selftest", "recheck"])
    ap.add_argument("--source-scripts", default=None)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--n-jobs", type=int, default=4)
    ap.add_argument("--with-arm-e", action="store_true")
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--gate-only", action="store_true")
    ap.add_argument("--allow-missing-reference", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--predictions-out", default=None)
    ap.add_argument("--ref-dir", default=str(OUT))
    ap.add_argument("--expect-arms", default=None,
                    help="comma-separated arms the table must contain, e.g. a,b,e "
                         "(used by --gate-only and recheck; recheck defaults to a,b,e, "
                         "a run defaults to its computed arms)")
    args = ap.parse_args()
    expect_arms = ([a.strip() for a in args.expect_arms.split(",") if a.strip()]
                   if args.expect_arms else None)

    if args.mode == "selftest":
        return selftest(OUT / "sensitivity_screening_seed42.csv",
                        OUT / "sensitivity_arms_seed42.csv", Path(args.ref_dir))

    if args.mode == "recheck":
        ok = 0
        for m in ("screening", "arms"):
            ok |= recheck(m, args.seed,
                          OUT / f"sensitivity_{m}_seed{args.seed}.csv",
                          OUT / f"predictions_{m}_seed{args.seed}.csv",
                          arms=expect_arms if m == "arms" else None)
        return ok

    if args.gate_only:
        if not args.out:
            raise SystemExit("--gate-only needs --out pointing at the metrics table")
        frame = pd.read_csv(args.out)
        status, problems = gate(args.mode, args.seed, frame, Path(args.ref_dir),
                                allow_missing=args.allow_missing_reference,
                                expect_arms=expect_arms)
        return _report(status, problems)

    if not args.source_scripts or not args.csv:
        raise SystemExit("--source-scripts and --csv are required for a run")

    csv_path = Path(args.csv).resolve()
    max_rows = args.max_rows or (25_000 if args.mode == "screening" else 50_000)
    out_path = Path(args.out) if args.out else OUT / f"sensitivity_{args.mode}_seed{args.seed}.csv"
    pred_path = (Path(args.predictions_out) if args.predictions_out
                 else OUT / f"predictions_{args.mode}_seed{args.seed}.csv")
    prov_path = out_path.with_suffix(".json")

    mb = load_mb(Path(args.source_scripts).resolve(), args.seed)
    rows: list[dict] = []
    pred_rows: list[dict] = []
    if args.mode == "screening":
        n_sampled = run_screening(mb, csv_path, args.seed, max_rows, args.n_jobs,
                                  rows, pred_rows)
    else:
        n_sampled = run_arms(mb, csv_path, args.seed, max_rows, args.n_jobs,
                             args.with_arm_e, rows, pred_rows)

    frame = pd.DataFrame(rows)[METRIC_COLS]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False, float_format="%.10g")
    pd.DataFrame(pred_rows)[PRED_COLS].to_csv(pred_path, index=False,
                                              float_format="%.10g")
    n_raw = int(pd.read_csv(csv_path, usecols=[0]).shape[0])
    n_unique = len({r["raw_row_index"] for r in pred_rows})
    with open(prov_path, "w", encoding="utf-8") as fh:
        json.dump(provenance(
            csv_path, args.mode, args.seed, n_sampled, n_raw,
            len(pred_rows), len(frame),
            "hash of the script that produced this file at archive time; reruns "
            "with the current script are expected to reproduce the fitted values",
            n_unique=n_unique),
            fh, indent=2, sort_keys=True)
    print(f"wrote {out_path.name} ({len(frame)} rows), {pred_path.name} "
          f"({len(pred_rows)} predictions) and {prov_path.name}", flush=True)

    if args.no_gate:
        print("gate: skipped by --no-gate (this run is NOT verified)")
        return 0
    declared = expect_arms or (["a", "b", "e"] if args.with_arm_e else ["a", "b"])
    status, problems = gate(args.mode, args.seed, frame, Path(args.ref_dir),
                            allow_missing=args.allow_missing_reference,
                            expect_arms=declared if args.mode == "arms" else None)
    return _report(status, problems)


if __name__ == "__main__":
    raise SystemExit(main())
