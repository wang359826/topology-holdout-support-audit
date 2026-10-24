# v1.4 发布清单（version of record）

> **本文件不进归档。** 仓库根 `.gitattributes` 对 `manuscript_v6/RELEASE_v1.4_清单.md`
> 设了 `export-ignore`，所以 `git archive` 生成的 zip 里没有它——它就是"怎么生产这个 zip"
> 的说明书，放进 zip 会让其中的文件数与 MD5 自指。
>
> **2026-10-24 状态：master 与 tag `v1.4` 已推送 GitHub（commit `c30b382`），仅剩“Publish release”一步。**
> v1.3（`10.5281/zenodo.23434268`）只含原始分析；v1.4 是本文所有分析的 version-of-record。
> concept DOI `10.5281/zenodo.23415179` 不变，因此**发布后无需回填任何 DOI 数字**。
>
> **发布入口**：<https://github.com/wang359826/topology-holdout-support-audit/releases/new?tag=v1.4>
> 标题与正文见 `_release/v1.4_release_notes.md`（可直接粘贴）。**必须先 Publish release**，
> 只推 tag 不会触发 Zenodo。
>
> **重发说明（tag 已移动，尚未公开发布，故仍记作 v1.4）**：本轮按 `peer_review_package_v4.md`
> 改了摘要、§3.2/§3.3 的 R² 与训练规模上下文、§3.1 的 rht 措辞、§4.4 限制、§9 复现措辞以及
> SI-H.1 的行数基数与 SI-A.2b 的拆分溯源。文件数与树结构未变（条目 694、文件 646、树 647）。

---

## 1. 本次归档相对 v1.3 新增/更新了什么

| 内容 | 位置 | 为什么必须进 v1.4 |
|---|---|---|
| 六项后续实验（表示、新颖性、CoRE、折叠级诊断、匹配替换、固定池筛选） | `manuscript_v6/03_reproduction_package/outputs/followup_20261023/` | SI-I 与表 S19–S24 的全部来源；v1.3 没有，是审稿指出的复现性缺口 |
| finish 分析（并列审计、候选行 bootstrap、逐拓扑表示差异） | `.../outputs/finish_20261023/` | §2.6、§3.6、SI-F.1、SI-I.1 的来源 |
| `max_features=1.0` 敏感性 | `.../outputs/sensitivity_mf1/` | 表 S25/S25b 的来源 |
| 配对检验归档 | `.../outputs/paired_tests_20261024.csv` | §3.3 的 +70% 百分比区间、§3.4 的配对检验 |
| 三级复现入口与配置 | `.../config/config.json`、`level1_verify/`、`level2_predictions/`、`level3_rerun/` | 让读者能按层级复核，而不是只拿到一堆 CSV |
| 本稿与 SI（含本轮六项修改）、4 主图与 SI 图 | `manuscript_v6/01_manuscript/`、`02_supplementary/` | 与归档结果对应的论文版本 |
| 检查器 604 项（新增 20 项：六项枚举、臂 (g)、图 3 panel (c)、配对区间等） | `.../scripts/check_v6_consistency.py` | 让"归档自洽"可被读者重跑 |

## 2. 生产命令（可复现）

```powershell
cd 03_投稿专用包\03_reproduction_package
git add -A
git commit -m "v1.4: six follow-ups, finish/mf1 analyses, paired tests, v1.4 manuscript"
git tag -f v1.4
git archive --format=zip -o ..\..\_release\v1.4.zip v1.4
```

本次实测：见第 4 节。

## 3. 发布步骤（GitHub → Zenodo 集成）

1. `git push` 与 `git push --tags`（沙箱内 SSH 起不来时，在桌面会话执行）。
2. GitHub → 仓库 → **Releases** → *Draft a new release* → 选 tag `v1.4` → Publish release。
   （触发条件是 **Release**，只推 tag 不会触发 Zenodo。）
3. 等几分钟，Zenodo 的 concept 记录会出现新版本；**concept DOI 不变**。
4. 核对：Zenodo 最新版本为 v1.4，文件数与第 4 节一致；`10.5281/zenodo.23415179` 解析到 v1.4。
5. 若集成失败，走兜底：My dashboard → Upload → 拖 `_release/v1.4.zip` → Publish。

## 4. 本次 zip 的实测值

| 项 | 值 |
|---|---|
| 文件 | `_release/v1.4.zip` |
| 条目数（含目录条目） | 694 |
| zip 内文件数 | 646 |
| `git ls-tree -r --name-only v1.4` 文件数 | 647（多出的一个就是本清单，被 `export-ignore`） |
| 字节数与 MD5 | 见 `_release/v1.4.zip.md5`；本清单不引用自己的 zip 哈希 |
| 未进归档 | `manuscript_v6/04_cover_letter/`、`manuscript_v6/06_ChemRxiv_投稿/`、本文件、`data/`、`_tools/`、历史 `RELEASE_v1.3_清单.md`、`六项证据整合与正文修改记录_20261023.md` |

> **为什么不把 MD5 写进本表**：同一 tag 用 `git archive` 重复导出是字节可复现的
> （实测两次导出 MD5 相同）；但 tag 一旦移动（amend、重打 tag），归档字节随之改变，
> 表里写死的哈希就会过期。因此 zip 的哈希由 sidecar（`_release/v1.4.zip.md5`）记录，
> 表里只写结构性事实（条目数、文件数）。跨打包器的核对以**树内容**为准：文件清单 +
> 逐文件 MD5（`manuscript_v6/03_reproduction_package/outputs/MD5SUMS.txt`，271 文件）。

## 5. 发布后不要做的事

- 不要在 v1.4 上线前对外声称"公开归档包含全部结果"（§9 与投稿信已按"v1.4 为 version of
  record"写；未上线时该句不成立）。
- 不要把 v1.3 的版本 DOI 与 v1.4 的文件混引：版本 DOI 永远指 v1.3。
- 不要再改 `manuscript_v6/` 里的文件却不重新发版；任何改动都会让 `check_v6_consistency.py`
  的 604 项与归档字节脱钩。
