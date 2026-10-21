#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
export_final_figures.py —— 把 pubfig 的 600-dpi 栅格复制到 PDF 真正读取的目录。

背景（2026-10-18 补）：`scripts/pubfig/build_*.py` 默认把栅格写到
`scripts/pubfig/_raster/*.png|tiff`，而 `build_pdf.py` 读的是同级的
`../01_manuscript/figures/`。因此“重出图”之后如果不显式导出，重建的 PDF 仍会
嵌入旧图。本脚本把 `_raster/*.png` 复制到 `../01_manuscript/figures/`（15 张），
并把两张 SI 图（figS6、figS7）也复制到 `outputs/`，与存档约定一致。

用法（从包根 03_reproduction_package 运行）：
    python scripts/export_final_figures.py
    python scripts/export_final_figures.py --check   # 校验 15 + 2 是否与 _raster 一致

`--check` 是严格的：15 张主/SI 图缺任何一张、或两张 outputs/ SI 副本不一致，
都以非零码退出。
"""
from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))          # 03_reproduction_package
RASTER = os.path.join(HERE, "pubfig", "_raster")
DEST = os.path.abspath(os.path.join(ROOT, os.pardir, "01_manuscript", "figures"))
OUT = os.path.join(ROOT, "outputs")

# 15 张正式图（正文 Figure 1–8 + SI Figure S1–S7），文件名与 build_pdf.py 的
# FIG_MAP / FIG_MAP_SI 一一对应。
EXPECTED = [
    "fig1_leakage_two_targets.png",
    "fig2_confound_structure.png",
    "fig3_isoreticular_control.png",
    "fig4_nn_distance.png",
    "fig5_pred_vs_actual.png",
    "fig6_penalty_vs_geometry.png",
    "fig7_multitarget_bars.png",
    "fig8_cross_database.png",
    "figS1_shap_family.png",
    "figS2_shap_dependence.png",
    "figS3_within_vs_cross.png",
    "figS4_aggregation_stability.png",
    "figS5_aggregation_rules.png",
    "figS6_source_confound.png",
    "figS7_sg_curve.png",
]

# 两张 SI 图同时进 outputs/（与 FIGURE_MANIFEST / 存档约定一致）
SI_IN_OUTPUTS = ["figS6_source_confound.png", "figS7_sg_curve.png"]


def _missing(directory: str, names) -> list[str]:
    return [n for n in names if not os.path.exists(os.path.join(directory, n))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只校验 ../01_manuscript/figures 的 15 张与 outputs/ 的 2 张 SI 副本")
    args = ap.parse_args()

    if not os.path.isdir(RASTER):
        sys.exit(f"找不到 {RASTER}：先跑 scripts/pubfig/build_*.py 生成 600-dpi 栅格。")

    # 严格：_raster 必须正好含这 15 个文件名（缺=失败；多余=警告）
    miss = _missing(RASTER, EXPECTED)
    if miss:
        print(f"FAIL: _raster 缺 {len(miss)}/{len(EXPECTED)} 张预期 PNG：")
        for f in miss:
            print("  ", f)
        return 1
    extras = sorted(set(f for f in os.listdir(RASTER)
                        if f.endswith(".png") and f not in EXPECTED))
    if extras:
        print(f"WARNING: _raster 有 {len(extras)} 个非预期 PNG（不影响校验）：")
        for f in extras:
            print("  ", f)

    if args.check:
        bad = []
        for f in EXPECTED:
            a = os.path.join(RASTER, f)
            b = os.path.join(DEST, f)
            if not os.path.exists(b) or not filecmp.cmp(a, b, shallow=False):
                bad.append(f)
        # 两张 outputs/ SI 副本也纳入校验
        for f in SI_IN_OUTPUTS:
            a = os.path.join(RASTER, f)
            b = os.path.join(OUT, f)
            if not os.path.exists(b) or not filecmp.cmp(a, b, shallow=False):
                bad.append(os.path.join("outputs", f))
        if bad:
            print(f"FAIL: {len(bad)} 处与 _raster 不一致（{len(EXPECTED)} 张投稿图 + "
                  f"{len(SI_IN_OUTPUTS)} 张 outputs SI 副本）：")
            for f in bad:
                print("  ", f)
            return 1
        print(f"OK: {len(EXPECTED)}/{len(EXPECTED)} 张投稿图与 {len(SI_IN_OUTPUTS)}/"
              f"{len(SI_IN_OUTPUTS)} 张 outputs SI 副本均与 _raster 逐字节一致")
        return 0

    os.makedirs(DEST, exist_ok=True)
    for f in EXPECTED:
        shutil.copy2(os.path.join(RASTER, f), os.path.join(DEST, f))
    os.makedirs(OUT, exist_ok=True)
    for f in SI_IN_OUTPUTS:
        shutil.copy2(os.path.join(RASTER, f), os.path.join(OUT, f))
    print(f"exported {len(EXPECTED)} PNG -> {DEST}")
    print(f"and {len(SI_IN_OUTPUTS)} SI PNG -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
