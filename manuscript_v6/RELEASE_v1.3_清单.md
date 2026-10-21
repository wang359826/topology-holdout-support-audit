# v1.3 发布清单

> 复审 P1-4：正文原引用的 v1.2 不含 2026-10-19/20 新增脚本与当前稿，故发布 v1.3。
> 状态更新：2026-10-21。**GitHub 侧已完成**；**Zenodo 上传待作者执行**（唯一需要你手动做的一步）。

---

## 1. 已完成（已核）

| 项 | 值 | 来源 |
|---|---|---|
| GitHub 仓库已改名 | `wang359826/topology-holdout-support-audit` | `git ls-remote` 实测（旧名永久重定向，旧链接不断） |
| GitHub tag `v1.3` | 已建并推送，现指向 commit `fd5a7ac` | 本地 `git tag -f` + `git push -f`；远程 `ls-remote` 已核对一致 |
| 远程 `master` HEAD | `fd5a7ac`（与 tag 同 commit） | `git ls-remote origin` |
| 仓库是否 public | **是**（匿名 `git ls-remote` 成功列出 refs） | Zenodo GitHub 集成的前提 |
| `.zenodo.json` | 已加在仓库根，含标题/作者/许可/关键词/描述/关联标识 | 供 GitHub→Zenodo 集成自动导入元数据 |
| 归档 zip（后备） | `_release/v1.3.zip`，50,777,465 B，506 文件，MD5 `7803f6984f5398672751547b87fdf669` | `git archive` 从 tag `v1.3` 生成 |
| zip 不含 | `data/`、`04_cover_letter/`、`__pycache__/`、`_tools/`、`_内部存档_非投稿/` | 逐条目统计 |
| §9 已更新 | tag `v1.3` + 新仓库 URL + concept DOI `10.5281/zenodo.23415179` | `01_manuscript/Manuscript_v6.md:281` |
| 主稿 PDF 已重建 | 732 KB，在 §9 修改之后 | `scripts/build_pdf_v6.py` |
| 一致性检查 | **583/583 通过**（含 PDF 新鲜度） | `scripts/check_v6_consistency.py` |
| **Zenodo 版本 DOI** | **`10.5281/zenodo.23434268`** | Zenodo API `GET /api/records/23434268` |
| **Zenodo concept DOI** | **`10.5281/zenodo.23415179`**（与 §9 现引用**相同**） | 同上，字段 `conceptdoi` |
| Zenodo 归档文件 | `topology-holdout-support-audit-v1.3.zip`，50,830,459 B，MD5 `b8b8504388da5717dd612fb8cec76ae8` | 同上，字段 `files` |
| Zenodo 记录元数据 | 标题/作者/MIT/v1.3/10 关键词/3 关联标识/资源类型 **Software**/公开 | 由仓库根 `.zenodo.json` 自动导入 |

## 2. 已跑通的校验（zip 全新解压目录，2026-10-21，第二轮复核）

**注意 cwd**：v6 的自有脚本（`check_v6_consistency.py`、`singleton_audit.py`、
`component_breakdown.py` 等）在 `manuscript_v6/03_reproduction_package/scripts/`，
**不在**归档根的 `scripts/`（那是 v5 的流水线脚本）。

```text
# ── 在 manuscript_v6/03_reproduction_package/ 下 ──
[1] python scripts/check_v6_consistency.py          → 583/583 通过（含 PDF 新鲜度）
    python scripts/check_v6_consistency.py --no-pdf → 579/579 通过
[2] python scripts/make_md5sums.py --check          → OK，161 文件全部匹配
[3] python scripts/singleton_audit.py verify        → OK（4 行，全部与正文数字一致）
[4] python scripts/singleton_audit.py selftest      → OK（污染副本被拒，归档通过）

# ── 回到归档根 ──
[5] python scripts/make_md5sums.py --check          → OK，126 文件全部匹配（v5 侧）
[6] grep §9 manuscript_v6/01_manuscript/Manuscript_v6.md
                                                   → tag v1.3 / 新仓库 URL / concept DOI 均已在归档内
```

`[1]` 的 583 项是在**解压出的归档内**跑的，说明随包发出的 `Manuscript_v6.pdf`
（749,260 B）确实是 §9 改稿之后重建的那一版，不是旧 PDF。

## 2b. zip 与 tag 的一致性复核（2026-10-21 第二轮）

```text
git archive --format=tar v1.3 | tar -x -C /c/temp/v13_recheck   → 505 个文件
zip 内文件数 505，tag 内文件数 505
仅在 zip：0    仅在 tag：0    内容不一致：0
→ ZIP 与 GitHub tag v1.3 逐文件 MD5 完全一致
→ 应排除条目（__pycache__ / *.pyc / data/ / cover_letter）：0
```

（其后为加入 `.zenodo.json` 又重新 `git archive`，文件数变为 506；
因 zip 直接由同一 tag 导出，一致性由构造保证，无需重跑逐文件比对。）

## 3. Zenodo 发布：**已完成**（2026-10-21 22:18）

走 GitHub→Zenodo 自动归档成功。结果比预期更好：

- **版本 DOI `10.5281/zenodo.23434268`** — v1.3 这个确切版本
- **concept DOI `10.5281/zenodo.23415179`** — 与正文 §9 现在引用的**是同一个**

也就是说 v1.3 挂在了**原有 concept 记录**下（v1.2 自动保留为历史版本），
**§9 不需要再改**。当初为打破循环依赖而采用的 concept DOI 写法，现在正好指向 v1.3。

## 4. 已完成的后续（2026-10-21）

1. §9 concept DOI **未改**（新记录 concept DOI 与 §9 原引用一致，无需动）。
2. §9 **已补版本 DOI**（见下）：改正文 → 重建 PDF（749,357 B）→ 重跑 **583/583 通过**。
3. **已更新**：`00_提交前必读.md` §2 第 1 条、`05_下一步清单.md` P0-1、本清单、
   `04_cover_letter/Cover_Letter_v6.md`（归档声明由“将要”改为既成事实，并写入实际 DOI）。
4. **待办**：从 Zenodo 公开入口回下载归档，按第 2 节复跑一遍（不训练模型的部分）。

### 4b. §9 钉死版本 DOI（2026-10-21 23:02 已执行）

§9 Data availability 现在同时给出两个 DOI：

> archived at <https://doi.org/10.5281/zenodo.23434268> (version DOI, the version used for
> this manuscript); the concept DOI <https://doi.org/10.5281/zenodo.23415179> resolves to the
> latest version.

**为什么钉死**：只写 concept DOI 的话，将来若发 v1.4（例如修回时补跑 LOTO 或改代码），
concept DOI 会自动转向 v1.4，而 §9 同时写着 `tag v1.3`，两者就会互相矛盾。
版本 DOI 永远指着 v1.3，不管以后发多少版。

**代价（已实测，很小）**：
- 一致性检查器不含任何 DOI 字符串（grep 为空），583 项不受影响；
- 唯一差异是 Zenodo v1.3 归档内的 `manuscript_v6` 仍只有 concept DOI，
  与最终投稿稿差一行 DOI 文本；不影响任何数字或校验，且两种说法今天都成立。

## 5. 路线 A：GitHub→Zenodo 自动归档（已选定）

**原理**：开启集成后，在 GitHub 上发一个 **Release**，Zenodo 自动抓取该 tag 的快照、
套用仓库根 `.zenodo.json` 里的元数据、归档并分配 DOI。文件由 GitHub 与 Zenodo
server-to-server 传输，不走你的网络，也不用你填表。

### 第 1 步：在 Zenodo 开启集成（你做，约 2 分钟）

1. 登录 <https://zenodo.org>
2. 右上角头像 → 菜单里的 **GitHub**
3. 点 **Sync now**（刷新仓库列表）
4. 在列表里找到 `topology-holdout-support-audit`，把开关拨到 **ON**

> 仓库已确认是 public，满足集成前提。若列表里看不到它，先 Sync 再刷新页面。

### 第 2 步：在 GitHub 发一个 Release（你做，约 1 分钟）

1. 打开 <https://github.com/wang359826/topology-holdout-support-audit>
2. 右侧 **Releases** → **Draft a new release**（或 **Create a new release**）
3. **Choose a tag** 选 `v1.3`（已存在，不要新建 tag）
4. Release title 填 `v1.3`，描述随意（可留空）
5. 点 **Publish release**

> 注意：触发条件是 **Release**，不是 tag。只推 tag 不会触发归档。

### 第 3 步：等 Zenodo 处理（几分钟）

回到 Zenodo → **My dashboard** → **Upload**，会看到一条新记录正在处理。
处理完成后记录里会出现 **两个** DOI：

- **DOI**（版本 DOI，形如 `10.5281/zenodo.2341XXXX`）← 发给我
- **Concept DOI**（形如 `10.5281/zenodo.XXXXXXX`）← **也发给我**（这条会是新号，我要改 §9）

### 元数据（已由 `.zenodo.json` 自动填入，你不用管）

| 字段 | 值 |
|---|---|
| Title | `What topology hold-out removes—and what it does not` |
| Upload type | software |
| Creators | Wang, Tao（Nanjing Tech University） |
| License | MIT |
| Version | v1.3 |
| Keywords | 10 个（MOF / carbon capture / machine learning / cross-validation / …） |
| Related identifiers | GitHub 仓库（isSupplementTo）、ARC-MOF v6 DOI、hMOF Materials Cloud 记录 |

### 若集成失败，走兜底路线

- **B（脚本全自动）**：Zenodo → 头像 → Applications → Personal access tokens → New token，
  勾 `deposit:write` + `deposit:actions`，把 token 发我，我用 API 完成上传与发布。
- **C（网页上传）**：My dashboard → **Upload** → 拖
  `C:\Users\汪星人\Desktop\MOF_topholdout_投稿包_v5修订\_release\v1.3.zip`（50.8 MB）→ Publish。

## 6. 不要在发布包里放的东西

`_tools/`（本轮本地绘图环境）、`_内部存档_非投稿/`、任何 `__pycache__/`、旧 PDF、
`data/`、`04_cover_letter/`。当前 zip 已确认不含这些。

## 7. 发布后不要做的事

- 不要在 v1.3 上线前对外声称“公开可复现”。
- Cover Letter 里不要在 DOI 到手前写 “all code/data are released”。
