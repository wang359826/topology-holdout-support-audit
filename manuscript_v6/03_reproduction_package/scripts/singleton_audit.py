#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Archive (and verify) the singleton / entropy audit behind Table 3 and SI-B.2.

Why this file exists
--------------------
Two families of numbers in the paper had no machine-readable archive before
2026-10-20: the *non-singleton* single-topology fractions and counts (hMOF fine
79.1%, ARC coarse 97.3%, ARC fine 98.2%), the singleton counts (hMOF coarse 21
of 1,622), the reverse conditional-entropy ratio H(C|T)/H(C) = 0.860 and the
first-order Miller-Madow corrections. They came from a read-only pass that
printed to a console, so a reader following REPRODUCE.md could not find them.

    # full recomputation from the two public databases (needs numpy + pandas)
    python scripts/singleton_audit.py recompute \
        --hmof   ../path/to/all_MOFs_screening_data.csv \
        --arcmof ../path/to/arcmof_confound.csv \
        --out    outputs/singleton_audit.csv \
        --summary-out outputs/arcmof_non_singleton_summary.csv

    # acceptance checks, standard library only
    python scripts/singleton_audit.py verify      # archive vs manuscript
    python scripts/singleton_audit.py selftest    # reject corrupted copies

`--arcmof` expects the assembled per-structure table
`data/arcmof/arcmof_confound.csv` of the source package, which `prep_arcmof.py`
builds from the public Zenodo release; its `topology` column is the Crystalnet
assignment, the same column `confound_arcmof.csv` reports as `topo_col =
Crystalnet`. If the assembly step has not been run, build it first (see
REPRODUCE.md, "Singleton / entropy audit").

Definitions (identical to the support audit of the paper)
---------------------------------------------------------
* coarse key  = metal_linker + organic_linker1 + organic_linker2   (hMOF)
                metal_linker + organic_linker1                     (ARC-MOF)
* fine key    = coarse key + functional_groups
* the two databases treat an unannotated identity differently, and the
  difference is deliberate rather than an oversight:
    - hMOF: a missing identity field is filled with the literal "NA", so the
      row stays in the analysis (main text §2.1: the 1,997 structures with an
      unannotated functional group form one additional fine value);
    - ARC-MOF: rows missing any key component are dropped, because the ARC
      cluster identifiers carry no "unknown" level. The valid-row counts below
      are therefore dropna counts (256,351 / 214,543 of 264,225).
* single-topology fraction = share of distinct compositions occurring in
  exactly one topology; the non-singleton variant restricts to compositions
  with >= 2 structures
* Miller-Madow first-order correction to H(T|C): (K_TC - K_C) / (2 N ln 2),
  reported as a sensitivity check, never as a proof of unbiasedness
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PKG / "outputs" / "singleton_audit.csv"
DEFAULT_SUMMARY = PKG / "outputs" / "arcmof_non_singleton_summary.csv"

# Values quoted in the manuscript. They are a regression reference for the
# archived file, NOT a substitute for recomputation from the raw databases.
EXPECTED = {
    ("hMOF", "coarse"): dict(
        N=324426, M=1622, K_TC=2032, n_singleton=21, n_non_singleton=1601,
        n_single_topology=1212, n_non_singleton_single_topology=1191,
        single_topology_all=0.7472, single_topology_non_singleton=0.7439),
    ("hMOF", "fine"): dict(
        N=324426, M=202481, K_TC=216306, n_singleton=136309,
        n_non_singleton=66172, n_single_topology=188656,
        n_non_singleton_single_topology=52347,
        single_topology_all=0.9317, single_topology_non_singleton=0.7911),
    ("ARC-MOF", "coarse"): dict(
        N=256351, M=180989, K_TC=184978, n_singleton=131120,
        n_non_singleton=49869, n_single_topology=179647,
        n_non_singleton_single_topology=48527,
        single_topology_all=0.9926, single_topology_non_singleton=0.9731),
    ("ARC-MOF", "fine"): dict(
        N=214543, M=177971, K_TC=178834, n_singleton=151591,
        n_non_singleton=26380, n_single_topology=177504,
        n_non_singleton_single_topology=25913,
        single_topology_all=0.9974, single_topology_non_singleton=0.9823),
}
EXPECTED_MM = {
    ("hMOF", "coarse"): 0.000912,
    ("hMOF", "fine"): 0.030739,
    ("ARC-MOF", "coarse"): 0.011225,
    ("ARC-MOF", "fine"): 0.002902,
}
KEY_FIELDS = ("dataset", "granularity")
INT_FIELDS = ("N", "M", "K_TC", "n_singleton", "n_non_singleton",
              "n_single_topology", "n_non_singleton_single_topology")
FLOAT_FIELDS = ("single_topology_all", "single_topology_non_singleton",
                "H_T_bit", "H_C_bit", "H_T_given_C_bit", "H_C_given_T_bit",
                "ratio_T_given_C", "ratio_C_given_T", "removed_pct_C",
                "miller_madow_bit", "miller_madow_share_pct")

COLUMNS = (list(KEY_FIELDS) + list(INT_FIELDS) + list(FLOAT_FIELDS))
SUMMARY_COLUMNS = ["topo_col", "key_definition", "population", "N", "M",
                   "non_singleton_count", "single_topology_non_singleton_count",
                   "fraction"]


# --------------------------------------------------------------------------
# recomputation (needs numpy + pandas)
# --------------------------------------------------------------------------
def _entropy(series) -> float:
    counts = series.value_counts()
    total = float(counts.sum())
    return float(-sum((c / total) * math.log2(c / total) for c in counts))


def audit(df, keys, dataset, granularity):
    """One database x granularity row. `df` is a pandas DataFrame."""
    import numpy as np
    import pandas as pd

    comp = df[keys].fillna("NA").astype(str).agg("|".join, axis=1)
    topo = df["topology"].astype(str)
    joint = pd.DataFrame({"c": comp, "t": topo})
    n = len(joint)
    if n == 0:
        raise ValueError(f"no rows for {dataset}/{granularity}")
    cell = joint.groupby(["c", "t"]).size()          # K_TC joint cells
    marginal = joint.groupby("c").size()             # K_C composition cells
    n_topo = joint.groupby("c")["t"].nunique()
    h_cond = ((marginal * np.log2(marginal)).sum()
              - (cell * np.log2(cell)).sum()) / n
    mm = (len(cell) - len(marginal)) / (2 * n * math.log(2))
    non_singleton = marginal.gt(1)
    if not non_singleton.any():
        raise ValueError(f"no non-singleton compositions for {dataset}/{granularity}")
    single = n_topo == 1
    h_c = _entropy(comp)
    h_t = _entropy(topo)
    h_joint = _entropy(comp + "||" + topo)
    h_c_given_t = h_joint - h_t
    return {
        "dataset": dataset,
        "granularity": granularity,
        "N": int(n),
        "M": int(len(marginal)),
        "K_TC": int(len(cell)),
        "n_singleton": int((~non_singleton).sum()),
        "n_non_singleton": int(non_singleton.sum()),
        "n_single_topology": int(single.sum()),
        "n_non_singleton_single_topology": int((single & non_singleton).sum()),
        "single_topology_all": float(single.mean()),
        "single_topology_non_singleton": float(single[non_singleton].mean()),
        "H_T_bit": float(h_t),
        "H_C_bit": float(h_c),
        "H_T_given_C_bit": float(h_cond),
        "H_C_given_T_bit": float(h_c_given_t),
        "ratio_T_given_C": float(h_cond / h_t),
        "ratio_C_given_T": float(h_c_given_t / h_c),
        "removed_pct_C": float(100.0 * (1.0 - h_c_given_t / h_c)),
        "miller_madow_bit": float(mm),
        "miller_madow_share_pct": float(100.0 * mm / h_cond),
    }


def recompute(hmof: Path, arcmof: Path, out: Path, summary_out: Path) -> int:
    import pandas as pd

    hmof_df = pd.read_csv(hmof, usecols=[
        "metal_linker", "organic_linker1", "organic_linker2",
        "functional_groups", "topology"])
    hmof_fine = hmof_df.copy()
    hmof_fine["functional_groups"] = hmof_fine["functional_groups"].fillna("NA")

    arc_df = pd.read_csv(arcmof, usecols=[
        "topology", "metal_linker", "organic_linker1", "functional_groups"])
    arc_coarse = arc_df.dropna(subset=["metal_linker", "organic_linker1"]).copy()
    arc_fine = arc_df.dropna(
        subset=["metal_linker", "organic_linker1", "functional_groups"]).copy()

    rows = [
        audit(hmof_df, ["metal_linker", "organic_linker1", "organic_linker2"],
              "hMOF", "coarse"),
        audit(hmof_fine, ["metal_linker", "organic_linker1", "organic_linker2",
                          "functional_groups"], "hMOF", "fine"),
        audit(arc_coarse, ["metal_linker", "organic_linker1"], "ARC-MOF", "coarse"),
        audit(arc_fine, ["metal_linker", "organic_linker1", "functional_groups"],
              "ARC-MOF", "fine"),
    ]
    frame = pd.DataFrame(rows, columns=COLUMNS)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out, index=False, float_format="%.10g")
    print(frame.to_string(index=False))
    print(f"\nwrote {out}")

    # Figure 4a / Table 3 read this summary instead of hard-coded values
    definitions = {
        "coarse": "metal_linker+organic_linker1",
        "fine": "metal_linker+organic_linker1+functional_groups",
    }
    summary = []
    for r in rows:
        if r["dataset"] != "ARC-MOF":
            continue
        summary.append({
            "topo_col": "Crystalnet",
            "key_definition": definitions[r["granularity"]],
            "population": "valid_rows",
            "N": r["N"],
            "M": r["M"],
            "non_singleton_count": r["n_non_singleton"],
            "single_topology_non_singleton_count":
                r["n_non_singleton_single_topology"],
            "fraction": r["single_topology_non_singleton"],
        })
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary, columns=SUMMARY_COLUMNS).to_csv(
        summary_out, index=False, float_format="%.10g")
    print(f"wrote {summary_out}")
    return verify(frame.to_dict("records"))


# --------------------------------------------------------------------------
# verification (standard library only)
# --------------------------------------------------------------------------
def _is_finite(v: float) -> bool:
    return isinstance(v, float) and math.isfinite(v)


def verify(rows, quiet: bool = False) -> int:
    """Strict internal-consistency check of an archived audit table.

    Fails on: a missing or duplicated (dataset, granularity) key, an unexpected
    row, a non-finite or negative value, an integer field that is not an
    integer, and any violation of the arithmetic identities the file implies
    (M = singleton + non-singleton, fraction = count / denominator, the two
    entropy directions, the Miller-Madow formula). Values are compared with
    `EXPECTED` as a version regression check only.
    """
    problems = []

    def bad(msg):
        problems.append(msg)

    rows = list(rows)
    seen = {}
    for r in rows:
        key = (r.get("dataset"), r.get("granularity"))
        if key in seen:
            bad(f"duplicate key {key}")
        seen[key] = r
    missing = sorted(set(EXPECTED) - set(seen))
    extra = sorted(set(seen) - set(EXPECTED))
    if missing:
        bad(f"missing rows {missing}")
    if extra:
        bad(f"unexpected rows {extra}")

    for key, r in seen.items():
        ints, floats = {}, {}
        for f in INT_FIELDS:
            try:
                v = float(r[f])
            except (KeyError, TypeError, ValueError):
                bad(f"{key} {f}: not numeric")
                continue
            if not _is_finite(v):
                bad(f"{key} {f}: not finite")
                continue
            if v != int(v) or v < 0:
                bad(f"{key} {f}: not a non-negative integer ({r[f]})")
            ints[f] = int(v)
        for f in FLOAT_FIELDS:
            try:
                v = float(r[f])
            except (KeyError, TypeError, ValueError):
                bad(f"{key} {f}: not numeric")
                continue
            if not _is_finite(v):
                bad(f"{key} {f}: not finite")
                continue
            floats[f] = v
        if len(ints) != len(INT_FIELDS) or len(floats) != len(FLOAT_FIELDS):
            continue

        if ints["M"] != ints["n_singleton"] + ints["n_non_singleton"]:
            bad(f"{key}: M != singletons + non-singletons")
        if ints["K_TC"] < ints["M"]:
            bad(f"{key}: K_TC < M")
        if ints["n_non_singleton_single_topology"] > ints["n_non_singleton"]:
            bad(f"{key}: non-singleton single-topology count exceeds denominator")
        if ints["n_single_topology"] > ints["M"]:
            bad(f"{key}: single-topology count exceeds M")

        def ratio(num, den):
            return num / den if den else float("nan")

        for f, num, den in (
                ("single_topology_all", ints["n_single_topology"], ints["M"]),
                ("single_topology_non_singleton",
                 ints["n_non_singleton_single_topology"], ints["n_non_singleton"])):
            want = ratio(num, den)
            if not _is_finite(want) or abs(floats[f] - want) > 1e-6:
                bad(f"{key} {f}: {r[f]} != {num}/{den} = {want:.10g}")
            if not (0.0 <= floats[f] <= 1.0):
                bad(f"{key} {f}: outside [0, 1]")

        if (abs((floats["H_T_given_C_bit"] - floats["H_C_given_T_bit"])
                - (floats["H_T_bit"] - floats["H_C_bit"])) > 1e-6):
            bad(f"{key}: entropy identities inconsistent")
        for f, num, den in (
                ("ratio_T_given_C", "H_T_given_C_bit", "H_T_bit"),
                ("ratio_C_given_T", "H_C_given_T_bit", "H_C_bit")):
            want = floats[num] / floats[den] if floats[den] else float("nan")
            if not _is_finite(want) or abs(floats[f] - want) > 1e-6:
                bad(f"{key} {f}: {r[f]} != {floats[num]:.10g}/{floats[den]:.10g}")
            if not (0.0 <= floats[f] <= 1.0):
                bad(f"{key} {f}: outside [0, 1]")
        if abs(floats["removed_pct_C"] - 100.0 * (1.0 - floats["ratio_C_given_T"])) > 1e-6:
            bad(f"{key}: removed_pct_C inconsistent with ratio_C_given_T")

        want_mm = (ints["K_TC"] - ints["M"]) / (2 * ints["N"] * math.log(2))
        if abs(floats["miller_madow_bit"] - want_mm) > 1e-9:
            bad(f"{key} miller_madow_bit: {r['miller_madow_bit']} != {want_mm:.10g}")
        want_share = 100.0 * want_mm / floats["H_T_given_C_bit"]
        if abs(floats["miller_madow_share_pct"] - want_share) > 1e-6:
            bad(f"{key} miller_madow_share_pct: inconsistent with the MM formula")

        exp = EXPECTED.get(key, {})
        for f, want in exp.items():
            got = ints.get(f, floats.get(f))
            if got is None:
                continue
            tol = 5e-4 if isinstance(want, float) else 0
            if abs(got - want) > tol:
                bad(f"{key} {f}: archive {got} != manuscript {want}")
        want_mm_exp = EXPECTED_MM.get(key)
        if want_mm_exp is not None and abs(floats["miller_madow_bit"] - want_mm_exp) > 5e-5:
            bad(f"{key} miller_madow_bit: {floats['miller_madow_bit']:.6f} != {want_mm_exp}")

    if problems:
        if not quiet:
            print("\nFAIL - archive fails verification:")
            for p in problems:
                print("  -", p)
        return 1
    if not quiet:
        print("\nOK - 4 rows, unique keys, all identities hold, and every value matches "
              "the number quoted in the manuscript")
    return 0


def read_rows(path: Path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def selftest(path: Path) -> int:
    """Corrupted copies must fail; prints a 7-row table and returns 1 on any miss."""
    base = read_rows(path)
    if not base:
        print("FAIL - archive is empty")
        return 1
    cases = [("pristine", None, 0)]
    cases.append(("drop one row", lambda r: r[:-1], 1))
    cases.append(("duplicate one row", lambda r: r + [dict(r[0])], 1))
    cases.append(("H_T_given_C = 999", _mut("H_T_given_C_bit", "999"), 1))
    cases.append(("n_non_singleton = 1", _mut("n_non_singleton", "1"), 1))
    cases.append(("fraction = NaN", _mut("single_topology_non_singleton", "nan"), 1))
    cases.append(("M = 999999", _mut("M", "999999"), 1))
    failures = 0
    print(f"{'case':28s} {'expected':8s} {'actual':8s}")
    for name, fn, want in cases:
        rows = base if fn is None else fn(base)
        got = verify(rows, quiet=True)
        status = "ok" if got == want else "MISMATCH"
        if got != want:
            failures += 1
        print(f"{name:28s} {want:<8d} {got:<8d} {status}")
    print("\nOK - corrupted copies are rejected and the archive passes"
          if not failures else f"\nFAIL - {failures} self-test case(s) behaved incorrectly")
    return 0 if not failures else 1


def _mut(field, value):
    def apply(rows):
        rows = [dict(r) for r in rows]
        rows[0][field] = value
        return rows
    return apply


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    rc = sub.add_parser("recompute", help="read the raw databases and write both archives")
    rc.add_argument("--hmof", required=True, help="all_MOFs_screening_data.csv")
    rc.add_argument("--arcmof", required=True,
                    help="arcmof_confound.csv (source package data/arcmof)")
    rc.add_argument("--out", default=str(DEFAULT_OUT))
    rc.add_argument("--summary-out", default=str(DEFAULT_SUMMARY))

    vf = sub.add_parser("verify", help="check the archived audit against the manuscript")
    vf.add_argument("--csv", default=str(DEFAULT_OUT))

    st = sub.add_parser("selftest", help="reject deliberately corrupted copies")
    st.add_argument("--csv", default=str(DEFAULT_OUT))

    args = ap.parse_args()
    if args.cmd == "recompute":
        return recompute(Path(args.hmof), Path(args.arcmof),
                         Path(args.out), Path(args.summary_out))
    if args.cmd == "selftest":
        return selftest(Path(args.csv))
    rows = read_rows(Path(args.csv))
    if not rows:
        print(f"FAIL - {args.csv} is empty")
        return 1
    absent = [c for c in COLUMNS if c not in rows[0]]
    if absent:
        print(f"FAIL - {args.csv} lacks columns {absent}")
        return 1
    return verify(rows)


if __name__ == "__main__":
    raise SystemExit(main())
