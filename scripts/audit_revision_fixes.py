#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
audit_revision_fixes.py —— 只读复算 2026-10-18 修订轮引入/改动的几处数字。

本脚本**不训练任何模型、不写任何结果文件**，只读取归档 CSV 与原数据，重新计算：

  1. pooled R² 在「全部 11 折」与「排除 pcu 评分折」下的值（0.3813680135 /
     0.4628955832）——用于复核 §3.5 的"排除 pcu"表述（附录 B1 口径）。
  2. 一阶 Miller–Madow 修正 ΔH(T|C) = (K_TC − K_C)/(2 N ln 2)：
     hMOF coarse/fine 与 ARC coarse/fine（0.000912 / 0.0307 / 0.0112 / 0.0029 bit）。
  3. ARC-MOF 非单例组成的单拓扑占比（coarse 97.31%、fine 98.23%）——替代旧的上界。
  4. 五种子筛选汇总（random 0.5040±0.0248、topology 0.1928±0.0706、oracle 相对损失
     46.3%、完整排序 4/5）——替代旧单次 47.5%。

用法（从包根 03_reproduction_package 运行）：
    python scripts/audit_revision_fixes.py

输入（均为归档文件，MD5 见 DATA.md / outputs/MD5SUMS.txt）：
    data/all_MOFs_screening_data.csv
    data/arcmof/arcmof_confound.csv         （由 scripts/prep_arcmof.py 组装）
    outputs/loto_per_topology_final.csv
    outputs/screening_utility_seed{42,143,244,345,446}.csv
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")
Y = "CO2_uptake_P0.15bar_T298K [mmol/g]"


def entropy_audit(x: pd.DataFrame, keys, topo: str, label: str) -> dict:
    c = x[keys].fillna("NA").astype(str).agg("|".join, axis=1)
    j = pd.DataFrame({"c": c, "t": x[topo].astype(str)})
    joint = j.groupby(["c", "t"]).size()
    marginal = j.groupby("c").size()
    k = j.groupby("c")["t"].nunique()
    n = len(j)
    h = ((marginal * np.log2(marginal)).sum()
         - (joint * np.log2(joint)).sum()) / n
    mm = (len(joint) - len(marginal)) / (2 * n * np.log(2))
    ns = marginal.gt(1)
    return {"label": label, "N": n, "K_C": len(marginal), "K_TC": len(joint),
            "diff": len(joint) - len(marginal), "H_T_given_C": h, "MM_bit": mm,
            "singleton": int((~ns).sum()), "non_singleton": int(ns.sum()),
            "ns_single_topo": int((k[ns] == 1).sum()),
            "ns_single_topo_frac": float((k[ns] == 1).mean())}


def main() -> int:
    print("=" * 78)
    print("audit_revision_fixes.py — read-only recomputation (no model training)")
    print("=" * 78)

    # ---- (1) pooled R², all folds vs excluding the pcu scoring fold ----
    h = pd.read_csv(os.path.join(DATA, "all_MOFs_screening_data.csv"))
    d = h.sample(100_000, random_state=42)
    a = pd.read_csv(os.path.join(OUT, "loto_per_topology_final.csv")).set_index("group")
    z = d.groupby("topology")[Y].agg(["size", "var"])
    assert z["size"].eq(a.loc[z.index, "n_test"]).all(), "n_test mismatch"
    z["SSE"] = (1 - a.loc[z.index, "R2"]) * (z["size"] - 1) * z["var"]
    print("\n[1] pooled R² (Appendix B1):")
    for label, q in [("all 11 folds", d), ("exclude pcu scoring fold", d[d.topology != "pcu"])]:
        sse = z.loc[q.topology.unique(), "SSE"].sum()
        sst = ((q[Y] - q[Y].mean()) ** 2).sum()
        print(f"    {label:28s} n={len(q):7d}  pooled R² = {1 - sse / sst:.10f}")

    # ---- (2) Miller–Madow + (3) ARC non-singleton rates ----
    print("\n[2] first-order Miller–Madow correction ΔH(T|C) = (K_TC − K_C)/(2 N ln 2):")
    h_fine = h.copy()
    h_fine["functional_groups"] = h_fine["functional_groups"].fillna("NA")
    for x, keys, topo, lab in [
        (h, ["metal_linker", "organic_linker1", "organic_linker2"], "topology", "hMOF coarse"),
        (h_fine, ["metal_linker", "organic_linker1", "organic_linker2", "functional_groups"], "topology", "hMOF fine"),
    ]:
        r = entropy_audit(x, keys, topo, lab)
        print(f"    {r['label']:14s} N={r['N']:,} K_C={r['K_C']:,} K_TC={r['K_TC']:,} "
              f"diff={r['diff']:,}  MM={r['MM_bit']:.8f} bit  H(T|C)={r['H_T_given_C']:.6f} bit")

    arc = pd.read_csv(os.path.join(DATA, "arcmof", "arcmof_confound.csv"))
    arc_coarse = arc.dropna(subset=["metal_linker", "organic_linker1"]).copy()
    arc_fine = arc.dropna(subset=["metal_linker", "organic_linker1", "functional_groups"]).copy()
    print("\n[3] ARC-MOF non-singleton single-topology fractions (actual counts, not a bound):")
    for x, keys, lab in [
        (arc_coarse, ["metal_linker", "organic_linker1"], "ARC coarse"),
        (arc_fine, ["metal_linker", "organic_linker1", "functional_groups"], "ARC fine"),
    ]:
        r = entropy_audit(x, keys, "topology", lab)
        print(f"    {r['label']:14s} N={r['N']:,} K_C={r['K_C']:,} K_TC={r['K_TC']:,} "
              f"diff={r['diff']:,}  MM={r['MM_bit']:.8f} bit  H(T|C)={r['H_T_given_C']:.6f} bit")
        print(f"      singleton={r['singleton']:,}  non_singleton={r['non_singleton']:,}  "
              f"non_singleton single-topo={r['ns_single_topo']:,}  "
              f"fraction={r['ns_single_topo_frac']:.6%}")

    # ---- (4) five-seed screening ----
    print("\n[4] five-seed screening (k = 1%):")
    seeds = [42, 143, 244, 345, 446]
    rows = []
    for seed in seeds:
        x = pd.read_csv(os.path.join(OUT, f"screening_utility_seed{seed}.csv"))
        x = x[x.k_frac.eq(0.01)].copy()
        x["seed"] = seed
        rows.append(x)
    s = pd.concat(rows, ignore_index=True)
    rt = s[s.strategy.eq("random")]["overlap_at_k"]
    tt = s[s.strategy.eq("topology")]["overlap_at_k"]
    print(f"    random  = {rt.mean():.4f} ± {rt.std(ddof=1):.4f}")
    print(f"    topology= {tt.mean():.4f} ± {tt.std(ddof=1):.4f}")
    t = s[s.strategy.eq("topology")]
    sel, ora = t.topk_true_mean, t.oracle_topk_mean
    # 两种口径的定义（此前标签写反了，2026-10-18 修正）：
    #   ratio-of-means  = 1 - mean(selected) / mean(oracle)   ← 论文 §3.11 采用这个
    #   mean-of-ratios  = mean(1 - selected_i / oracle_i)
    print(f"    oracle shortfall (ratio-of-means, paper §3.11) = "
          f"{1 - sel.mean() / ora.mean():.6%}")
    print(f"    oracle shortfall (mean-of-ratios)             = "
          f"{(1 - sel / ora).mean():.6%}")
    piv = s.pivot(index="seed", columns="strategy", values="overlap_at_k")
    order = [c for c in ["random", "chemistry", "linker_pair", "metal", "topology"] if c in piv.columns]
    full_ok = 0
    for seed in seeds:
        row = piv.loc[seed, order]
        if row.is_monotonic_decreasing:
            full_ok += 1
    print(f"    full five-way ordering (random>chemistry>linker_pair>metal>topology) "
          f"holds in {full_ok}/5 seeds")

    print("\nDone. These recomputed values are the audit behind §3.5 / §2.7 / §3.15 / §3.11.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
