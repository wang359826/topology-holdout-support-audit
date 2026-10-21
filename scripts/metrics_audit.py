#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指标口径审计：pooled / macro / weighted / median 一律全报
====================================================

为什么要有这个脚本（2026-10-09）
------------------------------
`mof_leakage_benchmark.py` 的 `evaluate_loto()` 返回的是
**把 11 折预测拼接后算一次的 pooled R²**，而逐折 R² 另存到 CSV。
这两个数不是一回事，而且可以差得非常远：

    留一拓扑（10 万样本）
      pooled   R² = +0.381   ← 把所有折的预测拼起来，一次算完
      weighted R² = -0.059   ← 逐拓扑 R² 按测试集大小加权平均
      macro    R² = -0.541   ← 逐拓扑 R² 简单平均（每种拓扑同等权重）
      median   R² = +0.278   ← 逐拓扑 R² 中位数

pooled 为正、macro 为负，是因为两者用了不同的分母与权重：pooled 把各折预测拼成
一份，对总均值只算一次；macro 是逐折 R² 的等权平均。前者确实受最大组 pcu
（63,447 个样本、R²=+0.298）主导，但**排除 pcu 评分折后 pooled 仍为正（+0.4629）**，
所以「剔除 pcu 后其余 10 组加权 −0.678」是逐组口径的结论，不能当作 pooled 的替代；
pooled 与 macro 的符号分歧来自分母不同，不是「正值完全来自 pcu」。

本脚本从已落盘的 per-group / per-fold CSV 重算四种口径，
输出一份"再也不能拿 pooled 冒充"的对照表（Table 2 修正版）。

用法
----
  python metrics_audit.py --outdir outputs
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass


def four_ways(d, r2col="R2", ncol="n_test"):
    """对逐组 R² 计算四种聚合口径。"""
    v = d[r2col].to_numpy(dtype=float)
    n = d[ncol].to_numpy(dtype=float) if ncol in d.columns else np.ones(len(v))
    return {
        "macro": float(v.mean()),          # 每组权重相同
        "weighted": float(np.average(v, weights=n)),  # 按样本量加权
        "median": float(np.median(v)),
        "min": float(v.min()),
        "max": float(v.max()),
        "n_groups": int(len(v)),
        "n_negative": int((v < 0).sum()),
        "frac_negative": float((v < 0).mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="outputs")
    args = ap.parse_args()

    out_rows = []
    reports = []
    complete = True          # False → 归档复核/缺输入，不覆盖归档 CSV

    # ------------------------------------------------------------------
    # 1) 留一拓扑：per-group CSV
    # ------------------------------------------------------------------
    for fn, label, pooled_fn in [
        ("loto_per_topology_final.csv", "LOTO / topology (100k)",
         "loto_results_final.csv"),
        ("loto_per_metal_final.csv", "LOTO / metal (100k)",
         "loto_results_final.csv"),
    ]:
        p = os.path.join(args.outdir, fn)
        if not os.path.exists(p):
            print(f"  [missing] {label}: 缺 {fn}；先跑 "
                  f"mof_leakage_benchmark.py --max-rows 100000 --loto --tag final")
            complete = False
            continue
        d = pd.read_csv(p)
        agg = four_ways(d)
        pooled = None
        pp = os.path.join(args.outdir, pooled_fn)
        if os.path.exists(pp):
            lr = pd.read_csv(pp)
            key = ("留一拓扑" if "topology" in fn else "留一金属中心")
            m = lr[lr["strategy"].astype(str).str.contains(key, na=False)]
            if len(m):
                pooled = float(m["R2"].iloc[0])
        if pooled is None:
            # 归档复核：从现有 metrics_audit.csv 恢复（无需重跑 benchmark）。
            # 一进入该分支就视为“归档复核”模式：即便恢复成功，也不覆盖正式结果。
            complete = False
            old_path = os.path.join(args.outdir, "metrics_audit.csv")
            if os.path.exists(old_path):
                try:
                    old = pd.read_csv(old_path, encoding="utf-8-sig")
                    hit = old[old["result"].astype(str) == label]
                    if len(hit) and pd.notna(hit["pooled_as_reported"].iloc[0]):
                        pooled = float(hit["pooled_as_reported"].iloc[0])
                        print(f"  [archive] {label}: pooled 从现有 metrics_audit.csv 恢复")
                except Exception as exc:  # noqa: BLE001
                    print(f"  [archive] {label}: 读取旧 metrics_audit.csv 失败 ({exc})")
        if pooled is None:
            print(f"  [missing] {label}: 缺 {pooled_fn}（pooled 无法从归档恢复）；"
                  f"先跑 mof_leakage_benchmark.py --max-rows 100000 --loto --tag final")
            complete = False

        # 剔除最大组后再算一次，检验"被大组主导"的程度
        if "topology" in fn:
            big = d.loc[d["n_test"].idxmax()]
            rest = d[d["group"] != big["group"]]
            agg_rest = four_ways(rest)
        else:
            big, agg_rest = None, None

        out_rows.append({
            "result": label,
            "pooled_as_reported": pooled,
            **agg,
        })
        if agg_rest:
            out_rows.append({
                "result": label + f"  [剔除最大组 {big['group']}]",
                "pooled_as_reported": None,
                **agg_rest,
            })

        pooled_txt = f"{pooled:.4f}" if pooled is not None else "n/a (missing input)"
        reports.append(
            f"\n【{label}】\n"
            f"  稿件里报的 pooled R² = {pooled_txt}\n"
            f"  macro(每组等权)      = {agg['macro']:+.4f}\n"
            f"  weighted(按 n 加权)  = {agg['weighted']:+.4f}\n"
            f"  median               = {agg['median']:+.4f}\n"
            f"  范围 {agg['min']:+.3f} ~ {agg['max']:+.3f}   "
            f"负值组 {agg['n_negative']}/{agg['n_groups']} "
            f"({agg['frac_negative'] * 100:.0f}%)\n"
            + (f"  剔除 {big['group']}(n={int(big['n_test'])}) 后："
               f"weighted {agg_rest['weighted']:+.4f}, "
               f"macro {agg_rest['macro']:+.4f}, "
               f"median {agg_rest['median']:+.4f}\n" if agg_rest else "")
        )

    # ------------------------------------------------------------------
    # 2) 拓扑内 vs 跨拓扑（3.10）：只有 6 个拓扑
    # ------------------------------------------------------------------
    p = os.path.join(args.outdir, "within_vs_cross_final.csv")
    if os.path.exists(p):
        d = pd.read_csv(p)
        rep = "\n【3.10 拓扑内 vs 跨拓扑（25k，8 个结构描述符）】\n"
        for col, name in (("R2_within", "within"), ("R2_cross", "cross")):
            a = four_ways(d.rename(columns={col: "R2"}))
            rep += (f"  {name:7s} macro {a['macro']:+.4f}   "
                    f"weighted {a['weighted']:+.4f}   "
                    f"median {a['median']:+.4f}   "
                    f"范围 {a['min']:+.3f} ~ {a['max']:+.3f}   "
                    f"负值 {a['n_negative']}/{a['n_groups']}\n")
            out_rows.append({"result": f"within_vs_cross / {name} (25k)",
                             "pooled_as_reported": None, **a})
        reports.append(rep)

    # The withdrawn CGCNN diagnostic is intentionally not merged into this audit.
    # It used a different row schema and is documented separately in SI Table S2;
    # keeping it out prevents a mixed-schema metrics_audit.csv from being consumed
    # as if every row represented a grouped-split aggregation.

    df = pd.DataFrame(out_rows)
    op = os.path.join(args.outdir, "metrics_audit.csv")
    if complete:
        df.to_csv(op, index=False, encoding="utf-8-sig")
    else:
        # 归档复核 / 缺输入：不覆盖已有 metrics_audit.csv（避免把完整的归档写残），
        # 只把本次可算的部分写到 *review* 文件，便于对照。
        rp = os.path.join(args.outdir, "metrics_audit.review.csv")
        df.to_csv(rp, index=False, encoding="utf-8-sig")

    print("=" * 78)
    print("指标口径审计")
    print("=" * 78)
    for r in reports:
        print(r)
    print("\n" + "=" * 78)
    print("规则（写进 Methods，以后一律遵守）")
    print("=" * 78)
    print("  1. 凡是分组划分，必须同时报告 macro / weighted / median / pooled 四者。")
    print("  2. 正文里用作主结论的，必须是 macro 或 median（每组同等权重的'典型表现'），")
    print("     不能是 pooled（会被最大组主导）。")
    print("  3. 若 pooled 与 macro 符号相反，必须在正文明确说明，并解释原因。")
    print("  4. 比较 R² 时，两侧测试集的目标变量方差必须可比；方差不同则改用")
    print("     RMSE 或标准化后的指标。")
    if complete:
        print(f"\n已保存: {op}")
    else:
        print(f"\n⚠️ 输入不完整（见上方 [missing]/[archive]）——"
              f"未覆盖归档的 metrics_audit.csv；本次复核写入 {rp}")


if __name__ == "__main__":
    main()
