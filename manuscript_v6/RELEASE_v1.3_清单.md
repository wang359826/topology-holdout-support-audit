# v1.3 发布清单（待作者执行）

> 复审 P1-4：当前正文引用的 v1.2 不含 2026-10-19/20 新增的脚本与当前稿。
> 本文件是"发布什么、怎么验"的清单；**没有替你上传任何东西**。

## 1. 现状（已核）

| 项 | 值 | 来源 |
|---|---|---|
| GitHub tag | `v1.2` | 正文 §9 |
| Zenodo 版本 DOI | `10.5281/zenodo.23433981` | Zenodo API，2026-10-17 发布 |
| Zenodo concept DOI | `10.5281/zenodo.23415179` | 同上（`conceptrecid` 字段） |
| 归档 zip | 16,489,323 B，MD5 `2268764a025a3904d660c6247f8dbef2` | 同上 |
| v1.2 是否含新脚本 | **否**（缺 `singleton_audit.py`、`input_validity_audit.py`、`check_v6_consistency.py`、`build_main_v6.py`、`build_toc_v6.py`、`loto_full_metrics.py`、`verify_regression.py`、`training_mean_baseline.py` 与 `Manuscript_v6.md`） | 复审递归文件树 + 本地比对 |

> 注：根目录 `README_入口.md` 曾写 `10.5281/zenodo.23415181`，该记录与本仓库的
> concept 记录（…179）不同号，已改为 concept DOI，避免三个号混用。

## 2. 待发布内容（建议 v1.3）

1. `03_投稿专用包_v6压缩/` 全量（主稿、SI、图件、`03_reproduction_package/`）
2. 源包 `03_投稿专用包/03_reproduction_package/` 的脚本与 `data/` 获取说明（原始库不随包分发）
3. 本清单第 3 节的校验清单（`outputs/MD5SUMS.txt` 已覆盖 161 个归档文件）

**不要**把以下内容放进发布包：`_tools/`（本轮本地绘图环境）、`_内部存档_非投稿/`、
任何 `__pycache__/`、旧 PDF。

## 3. 发布前检查（在干净解压目录执行）

```text
python scripts/make_md5sums.py --check
python scripts/singleton_audit.py verify
python scripts/singleton_audit.py selftest
python scripts/check_v6_consistency.py --no-pdf
python scripts/build_main_v6.py            # 需 matplotlib
python scripts/build_toc_v6.py             # 需 matplotlib
```

`check_v6_consistency.py` 现在应 **583/583 全通过**（2026-10-21 已重建 PDF）；若 PDF 过期，先重建再跑。

## 4. 发布后

1. 新建 release/tag `v1.3`，保留 `v1.2` 历史版本；记录新版本 DOI。
2. 更新正文 §9 的 tag 与版本 DOI（concept DOI 不变）。
3. 从公开入口重新下载，按第 3 节复跑一遍（不训练模型的部分），确认新脚本在包内。
4. 在 `REPRODUCE.md` 的 "Verification status" 写入实际检查日期、对象与范围；未下载核验前不要写"公开包端到端已复现"。
