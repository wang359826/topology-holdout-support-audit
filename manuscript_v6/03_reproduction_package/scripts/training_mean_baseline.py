#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reproduce SI Table S7 without fitting a model.

From the v6 reproduction-package root:
  python scripts/training_mean_baseline.py recompute --csv PATH_TO_HMOF
  python scripts/training_mean_baseline.py verify

recompute checks the original hMOF MD5, samples 50,000 rows with each fixed
seed, applies the production numeric/target missing-value filter, and uses
the original partner-selection rule. verify checks archived arithmetic and
hashes only; it does NOT validate the raw data or establish an author rerun.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parent.parent
SEEDS = [42, 143, 244, 345, 446]
N_SAMPLE = 50000
TARGET = "CO2_uptake_P0.15bar_T298K [mmol/g]"
EXPECTED_MD5 = "81e9c75fcbf17368bce957ea06e7a79f"
NUMERIC = [
    "volume [A^3]", "weight [u]", "surface_area [m^2/g]",
    "void_fraction", "void_volume [cm^3/g]",
    "largest_free_sphere_diameter [A]",
    "largest_included_sphere_along_free_sphere_path_diameter [A]",
    "largest_included_sphere_diameter [A]",
]
KEYS = ["metal_linker", "organic_linker1", "organic_linker2"]
METRICS = ["baseline_MAE", "baseline_RMSE", "baseline_MAE_over_sd"]
PER_SEED = "training_mean_baseline_seeds.csv"
SUMMARY = "training_mean_baseline_summary.csv"
META = "training_mean_baseline_audit.json"


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def digest(path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def row_digest(index):
    # Fingerprint of ordered, zero-based raw CSV data-row positions, not raw data.
    return hashlib.sha256(np.asarray(index, dtype="<i8").tobytes()).hexdigest()


def summarise(rows):
    require(len(rows) == 20, "Expected 20 seed/topology/arm rows.")
    require(not rows.duplicated(["seed", "test_topo", "arm"]).any(),
            "Duplicate seed/topology/arm keys.")
    out = []
    for (topo, arm), g in rows.groupby(["test_topo", "arm"], sort=True):
        require(sorted(g.seed.tolist()) == SEEDS, "Missing or unexpected seeds.")
        require(topo in ["nbo", "pcu"] and arm in ["a", "b"],
                "Unexpected topology or arm.")
        require((g.sd_y_test > 0).all(), "Invalid test standard deviation.")
        np.testing.assert_allclose(g.baseline_MAE / g.sd_y_test,
                                   g.baseline_MAE_over_sd, rtol=1e-12, atol=1e-12)
        row = {"test_topo": topo, "arm": arm, "n_seeds": len(g)}
        for col in METRICS:
            row[col + "_mean"] = float(g[col].mean())
            row[col + "_sd"] = float(g[col].std(ddof=1))
        row["rf_beats_baseline_all_seeds"] = bool(
            (g.rf_MAE_archived < g.baseline_MAE).all())
        out.append(row)
    require(len(out) == 4, "Expected four topology/arm groups.")
    return pd.DataFrame(out)


def compute(csv_path, reference_path):
    require(Path(csv_path).is_file(), "Raw CSV missing; see REPRODUCE.md.")
    require(digest(csv_path, "md5") == EXPECTED_MD5,
            "Input MD5 differs from the original DATA.md manifest; no results written.")
    raw = pd.read_csv(csv_path)
    require(raw.shape == (324426, 42), "Unexpected raw CSV shape.")
    require(set(NUMERIC + KEYS + ["topology", TARGET]).issubset(raw.columns),
            "Missing required raw columns.")
    ref = pd.read_csv(reference_path)
    require(len(ref) == 20 and not ref.duplicated(
        ["seed", "test_topo", "regime"]).any(), "Unexpected reference keys.")
    require(set(ref.seed) == set(SEEDS), "Unexpected reference seeds.")
    ref = ref.set_index(["seed", "test_topo", "regime"])
    rows, samples = [], []
    for seed in SEEDS:
        # Keep raw row indexes for fingerprints; pandas samples in original producer order.
        sampled = raw.sample(n=N_SAMPLE, random_state=seed)
        y = pd.to_numeric(sampled[TARGET], errors="coerce")
        numeric = sampled[NUMERIC].astype(float)
        keep = y.notna() & numeric.notna().all(axis=1)
        # Dummy-encoded categorical values add no missing cells in the original producer.
        d = sampled.loc[keep].copy()
        d[TARGET] = y.loc[keep]
        require(np.isfinite(d[TARGET].to_numpy()).all(), "Non-finite target.")
        require(len(d) == N_SAMPLE,
                "Unexpected dropped rows; audit original key alignment before proceeding.")
        topo = d.topology.astype(str)
        ck = d[KEYS].fillna("NA").astype(str).agg("|".join, axis=1)
        sets = {t: set(ck[topo == t]) for t in topo.unique()}
        samples.append({
            "seed": seed, "sampled_n": len(sampled), "retained_n": len(d),
            "sampled_row_order_sha256": row_digest(sampled.index),
            "retained_row_order_sha256": row_digest(d.index),
        })
        for test_topo in ["nbo", "pcu"]:
            candidates = [(t, len(sets[test_topo] & s))
                          for t, s in sets.items() if t != test_topo]
            candidates.sort(key=lambda pair: -pair[1])
            partner = candidates[0][0]
            require(partner == {"nbo": "pcu", "pcu": "nbo"}[test_topo],
                    "Partner selection differs from the archived contrast.")
            te = topo == test_topo
            yt = d.loc[te, TARGET].to_numpy(float)
            sd_test = float(yt.std(ddof=0))  # matches original production code
            require(len(yt) >= 2 and sd_test > 0, "Undefined test SD.")
            for arm, train in [
                ("a", ~te), ("b", (~te) & (topo != partner))
            ]:
                regime = "with_pair" if arm == "a" else "without_pair"
                archived = ref.loc[(seed, test_topo, regime)]
                require(int(train.sum()) == int(archived.n_train),
                        "Training count differs from archived intervention.")
                np.testing.assert_allclose(
                    sd_test, archived.MAE / archived.MAE_over_sd,
                    rtol=1e-10, atol=1e-12)
                train_mean = float(d.loc[train, TARGET].mean())
                residual = yt - train_mean
                mae = float(np.abs(residual).mean())
                rows.append({
                    "seed": seed, "test_topo": test_topo, "partner_topo": partner,
                    "arm": arm, "n_train": int(train.sum()), "n_test": len(yt),
                    "train_row_order_sha256": row_digest(d.index[train]),
                    "test_row_order_sha256": row_digest(d.index[te]),
                    "train_mean": train_mean, "sd_y_test": sd_test,
                    "baseline_MAE": mae,
                    "baseline_RMSE": float(np.sqrt(np.square(residual).mean())),
                    "baseline_MAE_over_sd": mae / sd_test,
                    # Archived RF values are cross-checks, never baseline predictions.
                    "rf_MAE_archived": float(archived.MAE),
                    "rf_MAE_over_sd_archived": float(archived.MAE_over_sd),
                })
    rows = pd.DataFrame(rows).sort_values(
        ["test_topo", "arm", "seed"]).reset_index(drop=True)
    summary = summarise(rows)
    audit = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {"name": Path(csv_path).name, "bytes": Path(csv_path).stat().st_size,
                  "md5": digest(csv_path, "md5"), "sha256": digest(csv_path),
                  "rows": len(raw), "columns": len(raw.columns)},
        "reference": {"name": Path(reference_path).name, "sha256": digest(reference_path)},
        "producer": {"name": Path(__file__).name, "sha256": digest(__file__)},
        "environment": {"python": platform.python_version(),
                        "numpy": np.__version__, "pandas": pd.__version__},
        "definition": {
            "target": TARGET, "seeds": SEEDS, "sample_size": N_SAMPLE,
            "sampling": "pandas.DataFrame.sample(n=50000, random_state=seed)",
            "filter": "numeric target and all eight numeric descriptors nonmissing",
            "partner": "other topology with largest overlap of coarse composition keys",
            "a": "train on all rows outside the test topology",
            "b": "also remove the partner topology from training",
            "constant": "arithmetic mean of each arm's training targets",
            "metric": "mean(abs(y_test - mean(y_train))) / std(y_test, ddof=0)",
            "summary": "mean and sample SD (ddof=1) of five per-seed metric values",
        },
        "sample_fingerprints": samples,
        "checks": {"raw_md5_matches": True, "all_20_train_counts_match": True,
                   "all_20_test_SDs_match_RF_archive": True},
        "model_training": False,
        "verification_scope": "raw-data recomputation and archived RF alignment checks",
        "human_author_independent_rerun": "not established by automated execution",
    }
    return rows, summary, audit


def write_results(rows, summary, audit, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    rows.to_csv(outdir / PER_SEED, index=False, encoding="utf-8-sig",
                float_format="%.17g", lineterminator="\n")
    summary.to_csv(outdir / SUMMARY, index=False, encoding="utf-8-sig",
                   float_format="%.17g", lineterminator="\n")
    (outdir / META).write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    lines = [digest(outdir / n) + "  " + n for n in [PER_SEED, SUMMARY, META]]
    (outdir / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify(outdir):
    for line in (outdir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        require(Path(name).name == name, "Invalid manifest filename.")
        require(digest(outdir / name) == expected, "Checksum mismatch: " + name)
    audit = json.loads((outdir / META).read_text(encoding="utf-8"))
    require(digest(__file__) == audit["producer"]["sha256"],
            "Producer differs from the recorded version; retain versioned audit evidence.")
    rows = pd.read_csv(outdir / PER_SEED)
    actual = summarise(rows)
    archived = pd.read_csv(outdir / SUMMARY)
    pd.testing.assert_frame_equal(actual, archived, check_exact=False,
                                  rtol=1e-12, atol=1e-12)
    print("PASS: archived checksums, 20 seed rows, and four summary mean/SD pairs.")
    print("Scope: archived arithmetic only; no raw-data or human-author rerun claim.")
    return archived


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    recompute = sub.add_parser("recompute")
    recompute.add_argument("--csv", type=Path, required=True)
    recompute.add_argument("--reference", type=Path,
                           default=PKG / "outputs/isoreticular_control_seeds.csv")
    recompute.add_argument("--outdir", type=Path, default=PKG / "outputs/baseline")
    check = sub.add_parser("verify")
    check.add_argument("--outdir", type=Path, default=PKG / "outputs/baseline")
    args = parser.parse_args()
    if args.mode == "recompute":
        rows, summary, audit = compute(args.csv, args.reference)
        write_results(rows, summary, audit, args.outdir)
        print("PASS: raw-data recomputation; no model was trained.")
        print(summary.to_string(index=False))
    else:
        print(verify(args.outdir).to_string(index=False))


if __name__ == "__main__":
    main()
