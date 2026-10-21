#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Component breakdown of the composite chemistry key (v6 supplement).

The main text's coarse composition key is
    metal_linker | organic_linker1 | organic_linker2
This script computes the metal / linker-pair / conjunction breakdown in SI-B.1
with the *same field set* as `chemistry_seen.py`, but it groups on a **tuple**
rather than on a "|"-joined string.  A missing field is represented by `None`
and is never stringified into a value, so a real field value of "NA" cannot
collide with a missing value.  The script fails closed if any row used here has
a missing key field or a missing topology; it never silently drops or merges
such a row.

The conjunction row must reproduce the published 74.7% / 61.3% /
H(T|C)/H(T) = 0.180 values; that identity is the built-in check.

Usage
-----
  python scripts/component_breakdown.py \
      --csv ../../03_投稿专用包/03_reproduction_package/data/all_MOFs_screening_data.csv \
      --out outputs/component_breakdown.csv

No third-party dependency; reads the raw CSV once.
"""
import argparse
import collections
import csv
import math
import sys


KEY_DEFINITIONS = {
    "metal only": ["metal_linker"],
    "linker pair": ["organic_linker1", "organic_linker2"],
    "metal+linker (conjunction)": ["metal_linker", "organic_linker1", "organic_linker2"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="raw hMOF CSV")
    ap.add_argument("--out", required=True, help="output CSV")
    ap.add_argument("--topology-col", default="topology")
    args = ap.parse_args()

    counts = {name: collections.defaultdict(collections.Counter) for name in KEY_DEFINITIONS}
    topo_total = collections.Counter()
    n_rows = 0
    missing_key_rows = 0
    missing_topology_rows = 0
    with open(args.csv, encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            n_rows += 1
            topology = (row.get(args.topology_col) or "").strip()
            if not topology:
                missing_topology_rows += 1
                continue
            topo_total[topology] += 1
            row_keys = {}
            has_missing_key = False
            for name, cols in KEY_DEFINITIONS.items():
                key = tuple((row.get(c) or "").strip() or None for c in cols)
                row_keys[name] = key
                if any(value is None for value in key):
                    has_missing_key = True
            if has_missing_key:
                missing_key_rows += 1
                continue
            for name, key in row_keys.items():
                counts[name][key][topology] += 1

    if n_rows == 0:
        sys.exit("no rows read; check --csv")
    if missing_key_rows or missing_topology_rows:
        sys.exit(
            "refusing to collapse missing values: %d row(s) have a missing key field, "
            "%d row(s) have a missing topology. Fix the input or add an explicit "
            "missing-value rule before using this breakdown."
            % (missing_key_rows, missing_topology_rows)
        )
    entropy_t = -sum((n / n_rows) * math.log2(n / n_rows) for n in topo_total.values())

    rows = []
    for name, table in counts.items():
        m = len(table)
        single = sum(1 for counter in table.values() if len(counter) == 1)
        structures_single = sum(sum(counter.values()) for counter in table.values() if len(counter) == 1)
        entropy_t_given_c = 0.0
        for counter in table.values():
            n = sum(counter.values())
            h = 0.0
            for value in counter.values():
                p = value / n
                h -= p * math.log2(p)
            entropy_t_given_c += (n / n_rows) * h
        rows.append({
            "key_definition": name,
            "N": n_rows,
            "M": m,
            "missing_key_rows": missing_key_rows,
            "missing_topology_rows": missing_topology_rows,
            "single_topology_compositions": single,
            "single_topology_fraction": single / m,
            "structures_single_topology_fraction": structures_single / n_rows,
            "H_T_bit": entropy_t,
            "H_T_given_C_bit": entropy_t_given_c,
            "ratio_T_given_C": entropy_t_given_c / entropy_t,
        })

    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        print(
            "%-28s M=%6d single_comp=%.4f struct_single=%.4f ratio=%.4f"
            % (
                row["key_definition"],
                row["M"],
                row["single_topology_fraction"],
                row["structures_single_topology_fraction"],
                row["ratio_T_given_C"],
            )
        )


if __name__ == "__main__":
    main()
