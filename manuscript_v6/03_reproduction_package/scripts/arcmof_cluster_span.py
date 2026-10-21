#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ARC-MOF cluster-ID span check (v6 supplement).

Answers one reviewer question: are ARC-MOF's metal/linker/functional cluster IDs
defined *per topology* (which would make the 99.3% single-topology fraction
circular), or are they global chemistry identifiers that can occur in several
topologies?  The script joins the archived ARC metadata table (one row per
structure, with cluster IDs and topology) and reports, per cluster family, how
many distinct IDs occur in more than one topology.

Input: data/arcmof/arcmof_confound.csv from the source package
       (columns: topology, metal_linker, organic_linker1, functional_groups)

Usage:
  python scripts/arcmof_cluster_span.py \
      --csv ../../03_投稿专用包/03_reproduction_package/data/arcmof/arcmof_confound.csv \
      --out outputs/arcmof_cluster_span.csv
"""
import argparse
import collections
import csv


FAMILIES = {
    "metal cluster (metal_linker)": "metal_linker",
    "linker (organic_linker1)": "organic_linker1",
    "functional group (functional_groups)": "functional_groups",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--topology-col", default="topology")
    args = ap.parse_args()

    spans = {name: collections.defaultdict(set) for name in FAMILIES}
    n_rows = 0
    with open(args.csv, encoding="utf-8-sig", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            n_rows += 1
            topology = (row.get(args.topology_col) or "").strip()
            for name, column in FAMILIES.items():
                value = (row.get(column) or "").strip()
                if value and value.lower() != "nan":
                    spans[name][value].add(topology)

    rows = []
    for name, table in spans.items():
        multi = sum(1 for topologies in table.values() if len(topologies) > 1)
        rows.append({
            "cluster_family": name,
            "N_structures": n_rows,
            "distinct_ids": len(table),
            "ids_in_multiple_topologies": multi,
            "fraction": multi / len(table) if table else 0.0,
        })

    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print("%-40s distinct=%6d multi-topology=%6d (%.1f%%)" % (
            row["cluster_family"], row["distinct_ids"],
            row["ids_in_multiple_topologies"], 100 * row["fraction"]))


if __name__ == "__main__":
    main()
