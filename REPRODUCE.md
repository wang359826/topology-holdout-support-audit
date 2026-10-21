# Reproduction manual

Everything in this repository exists to let a reader regenerate the results assigned
to each pipeline level, in one command per level. All five levels have been run end to
end — level 5 on 2026-10-14, with its seven per-step logs archived in `outputs/logs/`.
Nothing here depends on a GPU, on a private data source, or on a specific
editor.

Companion documents: `README.md` (claims → sections → scripts, English overview),
`REPORTING_CHECKLIST.md` (portable reporting rules, and why each one exists),
`DATA.md` (dataset URLs, MD5 checksums, two data traps), `LICENSE` (MIT, code only).

> This manual corresponds to the **v5** version of the manuscript
> (*topology hold-out is chemistry hold-out*; earlier prints of this manual said
> "v4", which was the version then current). An earlier v3 direction —
> "quantifying the leakage caused by random splitting" — was abandoned on
> 2026-10-09 after it turned out to be already covered by several 2026 studies.
> Nothing in this repository reproduces v3.

---

## 0. The shortest path

```bash
pip install -r requirements.txt            # 5 packages, CPU only
cd 03_reproduction_package        # 是包根，不是 scripts/
python scripts/run_all.py --level 1                # ~7.5 min  core evidence: Tables 8-11, 17; Figures 2-3
```

Add `--dry-run` to any level to print its commands without executing them.
Each step writes a log to `outputs/logs/`; a failing step stops the run and
prints the last 15 lines of its log, so downstream steps never consume partial output.

---

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.13 (developed on Windows 11; every script is cross-platform) |
| Packages | `pandas`, `numpy`, `scipy`, `scikit-learn`, `matplotlib` (`shap` only for level 5) |
| Hardware | laptop CPU, ≥ 8 GB RAM, **no GPU required** |
| Deep learning | **Not needed.** The deep-learning arm was withdrawn (§3.7); `torch`, `torch_geometric` and `pymatgen` are deliberately absent from `requirements.txt`. |

```bash
pip install -r requirements.txt
# if the default index is unreachable, pick any working mirror, e.g.
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

All random seeds are fixed (`random_state = 42` unless a script is explicitly
given more seeds).

---

## 2. Data

See `DATA.md` for URLs, sizes, MD5 checksums and download commands. Minimum per level:

| Level | Required files |
|---|---|
| 1, 2, 3, 5 | `data/all_MOFs_screening_data.csv` (hMOF, 148 MB, 324,426 rows) and `data/top_MOFs_screening_data.csv` (elite subset, 5.8 MB, 8,206 rows) |
| 4 | additionally `data/arcmof/{all_topology_lists,mc-clusters,flig-clusters,func-clusters}.csv` (73 MB in total) |

Both datasets are public and free, and this work generates **no new data**.

> Verify every download by MD5 before use. During the first round two files were
> truncated silently while `curl` still exited 0 (§"Known pitfalls", item 7).

---

## 3. The five levels

| Level | What it reproduces | Steps (current) | Wall time | Manuscript pieces |
|---|---|---|---|---|
| **1** | confound structure (full database), **per-held-out-topology chemistry seen/unseen decomposition**, controlled isoreticular contrast with 5 seeds and a size-matched arm, elite subset | **7** | **~7.5 min** *(7.3 min measured on an earlier list, plus 14 s for the full-database step; see below)* | §3.2, §3.4, §3.12; Tables 8–11, 17; Figures 2–3 |
| **2** | baseline comparison (both targets), four aggregation rules, 5-seed stability, mitigation strategies, composition hold-out arm, 415-feature control | **10** | **65.4 min** *(measured 2026-10-13 on a 6-step list; slowest step 34.7 min — see below)* | §3.1, §3.5, §3.9; Tables 7, 12–14, S3; Figures 1, S5, S7 |
| **3** | screening utility on a shared support set; composition-matched control arm; 10 targets in a 2×2 design; **identity-block availability per split (§4.2)**; model-family controls; grouping variants | **12** | **78.5 min** *(measured 2026-10-13 on an 8-step list; see below)* | §3.4, §3.11, §3.13, §3.14, §4.2; Tables 11 (composition-matched panel), 16, 18, 19, 25, 26; Figures 6–7 |
| **4** | replication on ARC-MOF, leave-one-source-out bound, per-source stratification with a valid spread test, sample-size dependence | **8** | **~30 min** *(29.9 min measured for an earlier 6-step form; see below)* | §3.15; Tables 20–24; Figures 8, S4, S6 |
| **5** | mechanism analyses and SHAP (optional), **plus the one-run recomputation of the three refuted explanations (§3.6)** | **7** | **≈5.5 h** *(2026-10-14 session span, retries included; not a clean benchmark — see below)* | §3.6, §3.8, §3.10; Table 15; SI Tables S1–S2, S4–S5; Figures 4–5, S1–S3 |

**Scripts added in revision v6.** Each is listed with where it actually runs — "registered"
means it is a step of `run_all.py` at the level named; **standalone** means the manuscript
uses its output but the script is run by hand (the archived copy is shipped). Do not claim
a standalone step is regenerated by `run_all.py`:

| Script | Registration | Output | Claim it supports |
|---|---|---|---|
| `chemistry_seen.py` | **level 1** | `chemistry_seen.csv`, `chemistry_seen_by_topology.csv`, `topology_pair_overlap.csv` | §3.2 Table 9: the per-held-out-topology seen/unseen decomposition, i.e. "7 of 11 topologies are pure chemistry hold-outs"; also the 61.3% / 44.2% levels |
| `chemistry_seen.py --csv data/arcmof/arcmof_confound.csv --topology-col topology --tag arcmof` | **standalone** (after `prep_arcmof.py`) | `chemistry_seen_arcmof.csv`, `chemistry_seen_by_topology_arcmof.csv`, `topology_pair_overlap_arcmof.csv` | §3.15 ARC-MOF: the same decomposition on the second database |
| `prep_arcmof.py` | **standalone** (not in any level) | `data/arcmof/arcmof_confound.csv` | §3.15: merges ARC-MOF topology and cluster files into the chemistry columns the confound statistics expect |
| `mof_leakage_benchmark.py --loto --tag chemistry` | **level 2** | `leakage_results_chemistry.csv`, `loto_per_chemistry.csv`, `group_stats_chemistry.csv` | §3.1 / §3.5: the composition hold-out arm (R² 0.6738 vs 0.3786; 1,590 chemistry groups) |
| `screening_utility.py --strategies …,chemistry --tag chemistry` | **level 3** | `screening_utility_chemistry.csv` | §3.11 Table 16 supplement: screening utility under composition hold-out |
| `screening_utility.py --seed S --no-figure --tag seedS`（S = 42/143/244/345/446） | **standalone**（五种子循环不在任何 level） | `screening_utility_seed{S}.csv` | §3.11 five-seed block: overlap@1% 0.5040±0.0248 → 0.1928±0.0706, oracle 损失 46.3% |
| `null_model_controls.py` | **standalone** (not in any level) | `null_elite_permutation_row.csv`, `null_elite_permutation_composition.csv`, `null_topology_cardinality.csv`（+ `_fine/`、`common_support/`） | §3.12 / §3.15: row-level vs composition-level permutation null; observed 100.0% vs null 21.4% |
| `partner_coverage_arm_e.py` | **level 3** | `arm_e_partner_coverage.csv` | §3.4 arm (e) / §4.5: 34.9% of the nbo degradation, and a sign reversal on the pcu side |
| `mof_leakage_benchmark.py --model {gb,ridge}` | **level 3** | `leakage_results_{gb,ridge}100k.csv` | §3.1: the gap refitted under gradient boosting and ridge (0.374 / 0.374 / 0.180) |

> `cardinality_correction.py --perm N` controls how many times the 587-column
> one-hot is refit under a shuffled group label (each refit is a full 5-fold RF on
> 25,000 × 587, roughly a minute). The shipped default is `--perm 3`; `--perm 0`
> skips that column entirely and still produces the ω² result, which is the part
> the manuscript quotes.

Times above are honest about their own history, because **all four timed levels** were
run by an earlier version of `run_all.py` than the one shipped here (only level 5 was run
on its current step list):

- **Level 1** was timed before `full_db_confound.py` joined the level — the step
  that computes the headline 93.2% on all 324,426 structures. That step has since
  been timed separately at **14 s**, hence 7.3 → ~7.5 min.
- **Level 2** (65.4 min) was measured on a **6-step** list; the current level 2 has
  **10** steps. The four steps added since (`fig3_fig4_missing.py`, `fig_sg_curve.py`,
  the chemistry hold-out arm, the 415-feature control) are plotting-only or have been
  re-run separately, but the 65.4 min figure is a 6-step measurement, **not** a timing
  of the shipped 10-step list.
- **Level 3** (78.5 min) was measured on an **8-step** list; the current level 3 has
  **12** steps. The four added since (the chemistry screening arm, `derive_multitarget_stats.py`,
  the metal / linker-pair grouping variants) have not been re-timed as a single list.
- **Level 4** was timed when the level still contained the withdrawn
  `granularity_control.py` and did **not** contain `arcmof_overlap.py` (12 s) or
  `sample_size_granularity.py` (39 s); both are now part of the level and both have
  been timed separately. Dropping one script and adding two that together cost
  51 s keeps the total at ~30 min.

Level 5 **has** been run end to end — on 2026-10-14, with its seven per-step logs archived as
`outputs/logs/L01`–`L07`. Its seven steps ran within one session spanning **≈5.5 h**
(16:53 → 22:21 on a 20-core desktop, 16 GB RAM), a span that includes intermediate retries, so we
quote it as a session record rather than as a clean per-level benchmark. **Levels 2 and 3 were
measured on 2026-10-13**, both on step lists shorter than the ones shipped today (see above), and
both came out well above the earlier estimates:

| Level | Earlier estimate | **Measured** | Step list when measured | Slowest step |
|---|---|---|---|---|
| 2 | ~45 min | **65.4 min** | 6 steps (current: 10) | the 100,000-sample baseline with leave-one-topology-out: 34.7 min |
| 3 | ~60 min | **78.5 min** | 8 steps (current: 12) | the composition-matched control arm (120 forests, one core): 45.1 min |

Measured step by step (2026-10-13, Windows 11, 20-core desktop, 16 GB RAM):
level 2 (6 steps) = 34.7 + 17.1 + 0.03 + 0.02 + 8.5 + 5.1 min; level 3 (8 steps) = 2.3 + 21.8 + 0.05 +
0.5 + 45.1 + 5.5 + 2.4 + 0.9 min. Levels 1 (7.3 min) and 4 (29.9 min) were measured on
2026-10-10 on a laptop (8 GB RAM), i.e. on slower hardware — treat all four numbers as
"the order of magnitude on an ordinary machine" on the step list stated, not as a benchmark of
the shipped lists.

**Verification actually performed (not merely intended).**

| Date | What | Result |
|---|---|---|
| 2026-10-10 | level 4, **as that level was defined at the time** (6 steps, including the withdrawn `granularity_control.py` and without `arcmof_overlap.py` / `sample_size_granularity.py`), re-run from scratch | all steps OK, **29.9 min**; `cmp` against the previous run showed **8/8 files byte-identical** (`confound_arcmof.csv`, `jaccard_arcmof.csv`, `exclusivity_across_databases.csv`, `source_confound_granularity.csv`, and the figures) |
| 2026-10-10 | the three steps missing from the timed runs above — `full_db_confound.py --tag full` (14 s), `arcmof_overlap.py` (12 s), `sample_size_granularity.py` (39 s) — re-run into a scratch directory | all exit 0, total 65 s. `cmp` against the archived files: **5/5 byte-identical** — `confound_full.csv` and `jaccard_full.csv` (which carry the headline 93.2% and the Jaccard table of §3.2), `arcmof_overlap.csv`, `confound_arcmof_excl_derived.csv`, `sample_size_granularity.csv` |
| 2026-10-10 | level 2, the second-target arm alone (`... --target selectivity --log-target --tag logsel100k`), re-run into a scratch directory | exit 0, 17 min while other jobs competed for the CPU. All four rows reproduced: random R² `0.8356804520124543` → topology R² `0.7211398375867859`, RMSE identical, MAE agreeing to ~1e-17. The only difference from the archived file is the strategy **label** ("未见拓扑" → "GroupKFold"), which changed after that file was written. `plot_main_figure.py` then reproduced exactly the two numbers quoted in §3.1: uptake 0.7529 → 0.3786 and selectivity 0.8357 → 0.7211. |

---

## 3b. Outside the pipeline: the standalone diagnostic and the checklist

Two files in this repository are deliberately **not** steps in any level, because
their purpose is to be pointed at *someone else's* data:

| File | What it is | How it is checked |
|---|---|---|
| `scripts/confound_diagnostic.py` | model-free diagnostic for **any** CSV with a grouping column and a chemistry definition. Reports, at two granularities, the single-group chemistry fraction, H(group \| chemistry) / H(group), n/M, and the group-pair Jaccard table; then prints a plain-language verdict | On the `hmof` preset at n = 50,000 it reproduces the n = 50,000 view **exactly** — the view the full-database statistics supersede: coarse 0.7533 / 0.1782, fine 0.9797 / 0.0233, pcu–nbo 387 shared / J = 0.358. On synthetic data with a *known* answer it returns "largely independent" (cond_frac 0.957) for chemistry drawn independently of the group, and "relabelling of chemistry" (cond_frac 0.000) for chemistry that deterministically fixes the group |
| `REPORTING_CHECKLIST.md` | the write-up of what to do with the diagnostic's answer, plus 22 reporting rules this study learned by breaking them | every number it cites is cross-checked against the archived outputs in `outputs/` (§3.2, §3.4, §3.5, §3.11, §3.13, §3.14); no figure appears in the checklist that is not also in a CSV here |
| `scripts/null_model_controls.py` | the two null-model controls of §3.12 / §3.15 (SI §S3): a **sample-level** topology permutation for the elite subset (b = 10,000) and a within-source permutation for every ARC-MOF source sub-library (b = 1,000) | reproduces §3.12's elite null (mean **21.4%**, sd 1.0%, against the observed 100.0%) and every source-level null of §3.15 Result 3; writes `null_elite_permutation_row.csv` (default) / `null_elite_permutation_composition.csv` (`--level composition`) and `null_topology_cardinality.csv` in `outputs/` |

```bash
python scripts/confound_diagnostic.py --csv your_data.csv \
    --group-col topology \
    --coarse-cols metal_linker,linker1,linker2 \
    --fine-cols   metal_linker,linker1,linker2,functional_groups \
    --pair-report
# or, to reproduce this paper's numbers directly:
python scripts/confound_diagnostic.py --preset hmof --max-rows 50000 --pair-report
```

It writes `confound_diagnostic.csv` and `confound_diagnostic_pairs.csv` next to
its output directory. It needs none of this paper's data when given a foreign CSV.

> ⚠️ **Those two filenames are the retired n = 50,000 convention.** The two files
> shipped with the earlier package were moved to `outputs/_deprecated_n50000/`
> (with a README explaining why) because their values (387 shared pcu–nbo
> compositions, J = 0.358, fine single-topology 97.97%) contradict the
> full-database figures the manuscript now reports (408, J = 0.371, 93.17%). The
> script is unchanged and still writes those filenames when you run it; only the
> archived copies were quarantined, so that a reader grepping `outputs/` for
> "pcu–nbo" finds one number rather than two.

The null-model controls need this paper's own data (they are not a foreign-data
tool) and are **not steps in any level**. Run them from `scripts/` with the
downloaded data:

```bash
# row level is the default (the unit the main text uses); add --level composition for
# the composition-level variant (a negative control, single-topology fraction == observed):
python scripts/null_model_controls.py --outdir outputs            --granularity coarse -b 10000 --b-card 1000
python scripts/null_model_controls.py --outdir outputs --granularity coarse --level composition -b 10000 --b-card 1000
python scripts/null_model_controls.py --outdir outputs/_fine      --granularity fine   -b 10000 --b-card 1000
# coarse on the common support set (mc/flig/func all present) — same口径 as the §3.15 table:
python scripts/null_model_controls.py --outdir outputs/common_support --granularity coarse -b 10000 --b-card 1000 --require-cols mc,flig,func
```

The **permutation unit is the sample (row)**: topology labels are reshuffled with
each topology's sample count preserved. Permuting at the *composition* level would
leave the single-topology fraction equal to its observed value by construction, so
the two units answer different questions; the manuscript states which one is used.

---

## 3c. What a fresh run reproduces — and the differences you should expect

On **2026-10-13** levels 2 and 3 were re-run from scratch against the archived
`outputs/`, on **newer library versions than the ones the archive was built with**
(pandas 3.0.6, numpy 2.5.3, scikit-learn 1.9.1, shap 0.52). Every step exited 0. The
result, file by file:

| Result | Status of a fresh run |
|---|---|
| `group_stats_final.csv`, `mitigation_results_mit25k.csv`, `screening_utility.csv`, `chemistry_seen_grouping.csv`, `leakage_results_{gb,ridge}100k.csv` | **byte-identical** |
| `leakage_results_final.csv`, `leakage_results_logsel100k.csv`, `loto_per_topology_final.csv`, `multi_seed_uptake25k_fix.csv`, `arm_e_partner_coverage.csv` | agree to **1×10⁻¹⁶ – 9×10⁻¹⁶** (last-digit floating-point noise), not byte-identical |
| `multitarget_confound.csv` | all 20 shared columns agree; the largest deviation is **5.6×10⁻⁷** in one auxiliary column (`topology_residual_R2`, from the 60-estimator residual ensemble). The fresh file also has **5 extra columns** (`group_col`, `R2_grp_*`, `split_effect_grp`, `identity_effect_grp`): the archived copy predates the `--group-col` option added for Table 25 |
| `composition_matched_control.csv` | numbers identical; 50 **label** strings differ, `diversity_matched_seedN` → `composition_matched_seedN` — the rename of arm (d), applied to the code but not to the archived file |
| `metrics_audit.csv` | **expected row-count difference**: the archived file carries two rows of the **withdrawn CGCNN arm** (§3.7); a fresh run writes only the five rows Table 12 uses |

So: **every number reported in the manuscript is reproduced, but byte-identity is a
property of the original environment, not of the code.** A reviewer on newer libraries
should expect agreement of order 10⁻¹⁵, with the three structural differences listed
above. Byte-for-byte identity was verified for level 4 (2026-10-10, 8/8 files).

---

## 3d. Two archive defects found and fixed on 2026-10-14

Both were found by re-deriving the manuscript's §3.12 numbers from the shipped `data/`
rather than from the archive. **In both cases the manuscript was right and the stored
output was wrong.** Nothing in the text was changed for these two; the scripts and the
stored outputs were.

### (a) `elite_vs_full.py` matched rows on the index (`MOFname` fix)

The script chose its matching path with

```python
if "filename" in full_qual.columns and "filename" in elite.columns:
```

Neither hMOF file has a `filename` column — the key is `MOFname` — so the condition was
always false and the `else` branch ran: `full_qual.index.isin(elite.index)`. Both files
carry a default `RangeIndex` starting at 0, so "retained" became *the first 8,206 rows of
the file in file order* and "lost" the remaining 1,382. Consequences, all of which
contradicted the manuscript:

| quantity | buggy archive | correct (and what the manuscript says) |
|---|---|---|
| pcu lost / sra lost / acs lost | 684 / 292 / 266 | **265 / 825 / 213** |
| bcu / fof / tbo lost | 94 / 42 / 0 | **54 / 24 / 1** |
| excluded-row mean uptake | 2.0460 | **2.6852** |
| retained-row mean uptake | 2.6880 (actually the first 8,206 rows' mean) | **2.5804** |
| `max_uptake_*` | listed acs/bcu/fof/pts — the topologies the elite file **keeps** | **nbo 1.954 / etb 1.949 / rht 0.776 / tbo 2.273**, the four §3.12 argues about |
| multi-topology compositions | 410 (the full-database total) | **131** (the elite subset's), with 410 kept under a separate key |

Fixed by keying on `MOFname`, by adding hard assertions (key present, no duplicate keys,
`retained + lost == qualifying`, neither side empty) so the positional fallback can no
longer run silently, and by splitting the two multi-topology counts into separate keys.
The step is now registered in level 1 of `run_all.py`.

### (b) `partner_coverage_arm_e.py` recorded arm (f)'s `n_train` as 50,000

Arm (f) builds a boolean mask `m2` of length `len(tv)` (= 50,000) and passed *that* to
`fit_eval`, whose helper computes `n_train` as `len(idx)`. So every arm-(f) row recorded
`n_train = 50000`, the pool size, where the manuscript and SI say 10,656 (the five-seed
mean of arm (b)'s training size, which arm (f) matches by construction). Passing the
index array `pick` instead fixes it — `X.iloc[pick]` and `topo.iloc[pick]` select the same
rows — and **changes the order of rows fed to the forest**, so arm (f)'s MAE moved in the
second decimal. The regenerated values, now in §3.4's arm-(e) table and in SI Table S8
supplement, are:

| arm (f) | before | after (5 seeds / seed 42) |
|---|---|---|
| nbo MAE | 0.1256 ± 0.0091 | **0.1250 ± 0.0073** / 0.1211 |
| pcu MAE | 0.2295 ± 0.0045 | **0.2304 ± 0.0045** / 0.2322 |
| nbo `n_train` (seed 42) | 50,000 (wrong) | **10,647** |
| pcu `n_train` (seed 42) | 50,000 (wrong) | **10,647** |

The script now asserts `n_train(f) == n_train(b)` for every (topology, seed), and takes
`--arms {a,b,e,f}` and `--n-jobs N` (default 1, because joblib's process pool cannot
create the named pipes it needs under a confined sandbox, and `n_jobs` does not change a
fit at fixed `random_state`). Re-running one arm alone then merging is a supported path:
`--arms f` writes `arm_e_partner_coverage_f.csv`.

### (c) `elite_subset_confound.py` and the elite fine missing-value convention

Table 17 declares its fine row as "6,214 compositions over the 8,145 annotated rows; the
61 unannotated rows are dropped". The script used the shared `confound_report`, which
does `fillna("NA")`, giving 6,275 over 8,206. The archive now carries **both**: `elite_fine`
(the declared drop convention, 6,214 / 8,145) and `elite_fine_fillna` (6,275 / 8,206). The
full-database fine count of Table 8 (202,481) uses the *fill* convention, and both the
manuscript and this file now say so, because the two fine figures are not interchangeable.

### (d) The checksum manifest is now generated

`outputs/MD5SUMS.txt` was hand-maintained and had drifted: it claimed to cover every file
while listing 65 of 78 (missing, among others, `leakage_results_chemistry.csv` and
`group_stats_chemistry.csv`, which Table 7 names as its source, and
`null_elite_permutation_row.csv`, which SI §S3 names), and its entry for
`arm_e_partner_coverage.csv` carried a hash and a byte count that no longer matched the
file. `scripts/make_md5sums.py` now regenerates it from the archive, `--check` verifies
it, and `run_all.py` calls it at the end of every level. Current state: **78 files, all
matching**.

### (e) Verification of the §3.12 defect in the other direction — two false alarms

Two further "archive vs text" disagreements were checked and resolved **in favour of the
text**, so nothing was changed:

- §3.12's "excluded rows' mean uptake is higher than the retained rows'" (2.69 against
  2.58) is **correct**; the buggy 2.046 figure came from defect (a) above.
- Table 22's ARC-MOF fine row differs from `sample_size_granularity.csv` in **one digit
  only**: the archive gives 99.7489% at n = 200,000, which rounds to 99.7%, and the table
  printed 99.8%. That single cell was corrected in the manuscript; the other three cells
  (99.9 / 99.9 / 99.8) were already right.

---

## 4. Claim / figure / table → producer → verification (the single authoritative mapping)

> **This is the one maintained mapping.** Every effective number and figure in the
> manuscript has a row below. `FIGURE_MANIFEST.md` is responsible for **only** the
> figure-number ↔ PNG-filename correspondence (and the exclusion list of figures that
> must not be embedded); this file is responsible for **how each output is produced and
> verified**. A figure that needs several production steps has several rows (one per
> step); a table with no result file has a "—" row.
>
> **Verification status legend:** **已核查** = recomputed/checked against the archive in
> this round; **历史复跑** = re-run end-to-end on an earlier step list or library set (date
> given); **仅有归档** = the archived CSV/figure is shipped but the step was not re-run
> here; **尚未验证** = not run in a fresh environment (distinguish these — none of them
> means the number is wrong).

### 4.1 Figures — final 600-dpi rasters in `../01_manuscript/figures/` (relative to the package root)

The **final** submission figures are drawn by the `scripts/pubfig/` builders, which read
the archived CSVs and write, by default, **vectors to `figures_pub/*.pdf|svg`** and the
600-dpi **rasters to `scripts/pubfig/_raster/*.png|tiff`** — *not* directly into
`../01_manuscript/figures/`. To update the figures the PDF actually embeds, copy the
`_raster/*.png` files into `../01_manuscript/figures/` (or set `PUBFIG_RASTER` to that
directory when running the builder), then rebuild the PDF; the older `fig_*.py` /
`plot_*.py` scripts write intermediate (200-dpi) versions and must **not** be allowed to
overwrite the final 600-dpi rasters. The pubfig builders are **not** steps of `run_all.py`
and are the authoritative entry for the submitted rasters. All random seeds are 42 unless
a command says otherwise.

| 主张或图表 | 输入及前置步骤 | 完整命令 / 参数 / 种子 | 输出文件 | 自动级别 / 独立 | 验证方式 | 已验证范围 |
|---|---|---|---|---|---|---|
| **Fig 1** data | — | `python scripts/mof_leakage_benchmark.py --max-rows 100000 --loto --tag chemistry`（uptake 四策略 + chemistry）；`python scripts/mof_leakage_benchmark.py --max-rows 100000 --target selectivity --log-target --tag logsel100k` | `leakage_results_chemistry.csv`, `leakage_results_logsel100k.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13，6-step L2；logsel 单独 17 min 复跑一致） |
| **Fig 1** 图 | 上面两个 CSV | `python scripts/pubfig/build_main_1_4.py 1` | `figures_pub/fig1_*.pdf\|svg` + `../01_manuscript/figures/fig1_leakage_two_targets.png` | 独立（pubfig） | 复跑对比 | 仅有归档（2026-10-15 已重建） |
| **Fig 2** data | — | `python scripts/full_db_confound.py --tag full`；`python scripts/elite_subset_confound.py` | `confound_full.csv`, `jaccard_full.csv`, `elite_subset_confound.csv` | level 1 | 复跑对比 | full_db 已核查（14 s 复跑 byte-identical）；elite 仅有归档 |
| **Fig 2** 图 | 上面三个 CSV | `python scripts/pubfig/build_main_1_4.py 2` | `fig2_confound_structure.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig 3** data | — | `python scripts/confound_diagnosis.py --max-rows 50000 --seeds 5`（+ `--size-match`） | `isoreticular_control_seeds.csv`, `isoreticular_control.csv`, `isoreticular_control_sizematched.csv` | level 1 | 复跑对比 | 历史复跑（L1 定时版） |
| **Fig 3** 图 | `isoreticular_control_seeds.csv` | `python scripts/pubfig/build_main_1_4.py 3` | `fig3_isoreticular_control.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig 4** data | — | `python scripts/leakage_mechanism.py --max-rows 25000 --family --tag final`；`python scripts/figures_and_shap.py --max-rows 25000 --shap-samples 200 --tag final` | `fig7_nn_curve_final.csv`, `fig4_predictions_final.csv` | level 5 | 复跑对比 | 历史复跑（2026-10-14 端到端；2026-10-16 部分复跑 ≤1.1×10⁻¹⁶） |
| **Fig 4** 图 | 上面两个 CSV | `python scripts/pubfig/build_main_1_4.py 4` | `fig4_nn_distance.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig 5** data | — | `python scripts/figures_and_shap.py --max-rows 25000 --shap-samples 200 --tag final` | `fig4_predictions_final.csv` | level 5 | 复跑对比 | 历史复跑（2026-10-14） |
| **Fig 5** 图 | `fig4_predictions_final.csv` | `python scripts/pubfig/build_main_5_8.py 5` | `fig5_pred_vs_actual.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig 6/7** data | — | `python scripts/multitarget_confound.py --max-rows 25000 --top-linkers 200 --resid-estimators 60` | `multitarget_confound.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13，8-step L3；≤5.6×10⁻⁷） |
| **Fig 6/7** 图 | `multitarget_confound.csv` | `python scripts/pubfig/build_main_5_8.py 6`；`… 7` | `fig6_penalty_vs_geometry.png`, `fig7_multitarget_bars.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig 8** data | — | `python scripts/arcmof_confound.py --top-n-topo 40 --out-tag arcmof`；`python scripts/source_confound_granularity.py --min-source-n 200 --boot 10`；`python scripts/sample_size_granularity.py` | `confound_arcmof.csv`, `source_confound_granularity.csv`, `sample_size_granularity.csv` | level 4 | 复跑对比 | L4 历史复跑（2026-10-10，6-step 版 byte-identical 8/8）；新增两步单独复跑 byte-identical |
| **Fig 8** 图 | 上面三个 CSV | `python scripts/pubfig/build_main_5_8.py 8` | `fig8_cross_database.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S1** data | — | `python scripts/figures_and_shap.py --max-rows 25000 --shap-samples 200 --tag final` | `fig5_shap_family_final.csv` | level 5 | 复跑对比 | 仅有归档（SHAP 需网络安装；图 S1 已从 CSV 重绘 byte-identical） |
| **Fig S1** 图 | `fig5_shap_family_final.csv` | `python scripts/pubfig/build_si_S1_S7.py S1` | `figS1_shap_family.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S2** data | — | `python scripts/prepare_figS2_pdp_data.py --max-rows 25000 --n-jobs 1` | `pdp_geometry_curves.csv`, `pdp_geometry_meta.csv` | 独立（不在任何 level） | 复跑对比 | 仅有归档 |
| **Fig S2** 图 | 上面两个 PDP CSV | `python scripts/pubfig/build_si_S1_S7.py S2` | `figS2_shap_dependence.png`（PDP 内容，见 SI §S15） | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S3** data | — | `python scripts/omitted_variable.py --max-rows 25000 --within-vs-cross --tag final` | `within_vs_cross_final.csv` | level 5 | 复跑对比 | 历史复跑（2026-10-14） |
| **Fig S3** 图 | `within_vs_cross_final.csv` | `python scripts/pubfig/build_si_S1_S7.py S3` | `figS3_within_vs_cross.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S4** data | — | `python scripts/multi_seed_repeat.py --max-rows 25000 --seeds 5 --skip-group --tag uptake25k_fix` | `multi_seed_uptake25k_fix.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| **Fig S4** 图 | `multi_seed_uptake25k_fix.csv` | `python scripts/pubfig/build_si_S1_S7.py S4` | `figS4_aggregation_stability.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S5** data | — | `python scripts/mof_leakage_benchmark.py --max-rows 100000 --loto --tag final`；`python scripts/metrics_audit.py` | `loto_per_topology_final.csv`, `metrics_audit.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| **Fig S5** 图 | 上面两个 CSV | `python scripts/pubfig/build_si_S1_S7.py S5` | `figS5_aggregation_rules.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |
| **Fig S6** data | 原始 ARC 元数据（`source_confound_granularity.py` 与 `null_model_controls.py` **直接读** `all_topology_lists/mc/flig/func`，不需 `prep_arcmof.py`） | `python scripts/source_confound_granularity.py --min-source-n 200 --boot 10`；`python scripts/null_model_controls.py --outdir outputs/common_support --granularity coarse -b 10000 --b-card 1000 --require-cols mc,flig,func` | `source_confound_granularity.csv`, `common_support/null_topology_cardinality.csv` | level 4 + 独立（null） | 复跑对比 | source_confound 历史复跑；null 仅有归档 |
| **Fig S6** 图 | 上面两个 CSV | `python scripts/pubfig/build_si_S1_S7.py S6` | `figS6_source_confound.png` | 独立（pubfig） | 复跑对比 | 已核查（本修订轮用 common_support + 比例轴重绘） |
| **Fig S7** data | — | `python scripts/s_g_curve.py --max-rows 100000` | `s_g_curve.csv` | 独立（不在任何 level） | 复跑对比 | 仅有归档 |
| **Fig S7** 图 | `s_g_curve.csv` | `python scripts/pubfig/build_si_S1_S7.py S7` | `figS7_sg_curve.png` | 独立（pubfig） | 复跑对比 | 仅有归档 |

### 4.2 Tables

> 编号与题注以主稿正文各表的**内联题注**（Table 1–27）与 SI 分节（Table S1–S9）为唯一权威。Table 1–6 是描述性表（文献、数据、定义、设计、描述符、聚合口径），无结果文件。已撤回的两项（CGCNN 对照、随机压缩粒度对齐）不再占表号。

| 主张或图表 | 输入及前置步骤 | 完整命令 / 参数 / 种子 | 输出文件 | 自动级别 / 独立 | 验证方式 | 已验证范围 |
|---|---|---|---|---|---|---|
| Table 1–6 | —（文献 / 定义 / 设计） | — | — | — | — | 描述性，无结果文件 |
| Table 7 | — | `mof_leakage_benchmark.py --max-rows 100000 --loto --tag final`（random/linker pair/metal/topology 四行）；chemistry 行来自 `--loto --tag chemistry`；415 行另需 `--drop-topology-block --tag notopo100k` | `leakage_results_final.csv`, `group_stats_final.csv`, `leakage_results_chemistry.csv`, `group_stats_chemistry.csv`, `leakage_results_notopo100k.csv`, `group_stats_notopo100k.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| Table 8 / 10 | — | `full_db_confound.py --tag full` | `confound_full.csv`, `jaccard_full.csv` | level 1 | 复跑对比 | 已核查（14 s 复跑 byte-identical） |
| Table 9 | — | `chemistry_seen.py` | `chemistry_seen.csv`, `chemistry_seen_by_topology.csv`, `topology_pair_overlap.csv` | level 1 | 复跑对比 | 历史复跑（L1） |
| Table 11 | — | `confound_diagnosis.py --max-rows 50000 --seeds 5 --size-match` | `isoreticular_control_seeds.csv`（+ `.csv` / `_sizematched.csv`） | level 1 | 复跑对比 | 历史复跑（L1） |
| Table 12 / 13 | 先跑基础 LOTO | `mof_leakage_benchmark.py … --loto --tag final`（Table 13 基础数据）→ `metrics_audit.py`（Table 12 派生统计） | `loto_per_topology_final.csv`, `metrics_audit.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| Table 14 | — | `multi_seed_repeat.py --max-rows 25000 --seeds 5 --skip-group --tag uptake25k_fix` | `multi_seed_uptake25k_fix.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| Table 15 | — | `omitted_variable.py --max-rows 25000 --within-vs-cross --tag final`；`cardinality_correction.py --max-rows 25000 --perm 3` | `omitted_variable_final.csv`, `cardinality_correction.csv` | level 5 | 复跑对比 | 历史复跑（2026-10-14 / 2026-10-16 ≤1.1×10⁻¹⁶） |
| **Table 16（单次 seed 42）** | — | `screening_utility.py --max-rows 25000`；chemistry 行另需 `--strategies random,topology,linker_pair,metal,chemistry --tag chemistry` | `screening_utility.csv`, `screening_utility_chemistry.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13） |
| **Table 16（五种子）** | 五个 seed 各自独立跑一次 | `screening_utility.py --max-rows 25000 --seed 42 --no-figure --tag seed42`（143 / 244 / 345 / 446 同理） | `screening_utility_seed{42,143,244,345,446}.csv` | **独立（不在任何 level）** | 逐文件汇总（正文 §3.11 五种子块） | **已核查**（本修订轮只读重算：random 0.5040±0.0248、topology 0.1928±0.0706、oracle 损失 46.3%） |
| Table 17 | — | `elite_subset_confound.py`；`elite_vs_full.py` | `elite_subset_confound.csv`, `elite_vs_full.csv`, `elite_vs_full_by_topology.csv` | level 1 | 复跑对比 | 历史复跑（2026-10-14 缺陷修复后） |
| Table 18 / 19 | — | `multitarget_confound.py --max-rows 25000 --top-linkers 200 --resid-estimators 60`；`derive_multitarget_stats.py` | `multitarget_confound.csv`, `multitarget_derived_stats.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13） |
| Table 20 | 原始 ARC 元数据（`arcmof_overlap.py` **直接读** `all_topology_lists/mc/flig/func`） | `arcmof_overlap.py` | `arcmof_overlap.csv`, `confound_arcmof_excl_derived.csv` | level 4 | 复跑对比 | 已核查（单独复跑 byte-identical） |
| Table 21 | 原始 ARC 元数据（`arcmof_confound.py` **直接读**） | `arcmof_confound.py --top-n-topo 40 --out-tag arcmof` | `confound_arcmof.csv`, `jaccard_arcmof.csv` | level 4 | 复跑对比 | L4 历史复跑（2026-10-10） |
| Table 22 | — | `sample_size_granularity.py` | `sample_size_granularity.csv` | level 4 | 复跑对比 | 已核查（单独复跑 byte-identical） |
| Table 23 | — | `source_confound_granularity.py --min-source-n 200 --boot 10` | `source_confound_granularity.csv` | level 4 | 复跑对比 | L4 历史复跑 |
| Table 24 | — | `source_spread_test.py` | `source_spread_test.csv` | level 4 | 复跑对比 | L4 历史复跑 |
| Table 25 | — | `multitarget_confound.py … --group-col metal` / `--group-col linker_pair`（topology 为默认） | `multitarget_confound.csv`, `multitarget_confound_metal.csv`, `multitarget_confound_linker_pair.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13） |
| Table 26 | — | `chemistry_seen_grouping.py --max-rows 25000` | `chemistry_seen_grouping.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13） |
| §3.4 arm (d) 组成匹配对照（正文补充表，无表号） | 前置 arm (a)/(b)（`confound_diagnosis.py`） | `diversity_control.py`（默认 5 种子；**脚本内部固定单线程**，无 `--n-jobs` 开关） | `composition_matched_control.csv`, `composition_matched_summary.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13；数值一致，仅 `diversity_matched_seedN`→`composition_matched_seedN` 标签改名） |
| §3.4 arm (e)/(f)（正文补充表，无表号） | 前置 arm (a)/(b)（`confound_diagnosis.py`） | `partner_coverage_arm_e.py`（`--arms {a,b,e,f}`，默认 5 种子；`--n-jobs 1`） | `arm_e_partner_coverage.csv`（+ `_f.csv` 单臂） | level 3 | 复跑对比 | 历史复跑（2026-10-14 缺陷修复后） |
| Table 27（22 条清单） | —（可复用产出） | 计数部分由 `confound_diagnostic.py` 对任意 CSV 计算；设计/报告条目（C/D）为作者自检 | `REPORTING_CHECKLIST.md`, `confound_diagnostic.csv`, `confound_diagnostic_pairs.csv` | 独立（工具） | 自检 | 工具在 hmof 预设 n=50,000 复现一致；非自动核查全部 22 条 |
| **SI Table S1 / S7** | — | `leakage_mechanism.py … --family --tag final`；`full_db_confound.py --tag full` | `fig7_nn_curve_final.csv`, `confound_full.csv` | level 5 / level 1 | 复跑对比 | 历史复跑 |
| **SI Table S2** | — | （已撤回 CGCNN 对照） | 无存档数值（仅诊断） | — | — | 无结果文件，仅有归档例外 |
| **SI Table S3** | — | `mof_leakage_benchmark.py --max-rows 25000 --mitigation --tag mit25k` | `mitigation_results_mit25k.csv` | level 2 | 复跑对比 | 历史复跑（2026-10-13） |
| **SI Table S4 / S5** | — | `omitted_variable.py … --within-vs-cross --tag final` | `within_vs_cross_final.csv` | level 5 | 复跑对比 | 历史复跑（2026-10-14） |
| **SI Table S6** | — | `multitarget_confound.py …` | `multitarget_confound.csv` | level 3 | 复跑对比 | 历史复跑（2026-10-13） |
| **SI Table S8** | — | `confound_diagnosis.py --max-rows 50000 --seeds 5`（seed 42 行） | `isoreticular_control.csv` | level 1 | 复跑对比 | 历史复跑 |
| **SI Table S9** | — | `s_g_curve.py --max-rows 100000` | `s_g_curve.csv` | 独立（不在任何 level） | 复跑对比 | 仅有归档 |

> **Table 12 的 `[剔除最大组 pcu]` pooled 格（0.4629）**：`metrics_audit.py` 只对逐组
> R² 做四口径聚合，不重算「排除 pcu 评分折」的 pooled（它需要拼接预测并重算总体均值）；
> 该格由 `python scripts/audit_revision_fixes.py` 从 `loto_per_topology_final.csv` +
> 原始抽样独立复算后填入（不重训）。
>
> **`metrics_audit.py` 自身的两种运行口径**（2026-10-18 起脚本已区分）：
> * **归档复核**（当前存档可直接跑）：缺 `loto_results_final.csv` / `loto_per_metal_final.csv`
>   时，脚本从现有 `metrics_audit.csv` 恢复 pooled、用 `[missing]` 逐条打印缺失文件与前置
>   命令，并**不覆盖**归档的 `metrics_audit.csv`，只写 `metrics_audit.review.csv`。
> * **先重训再复现**：先跑 `mof_leakage_benchmark.py --max-rows 100000 --loto --tag final`
>   生成上述两个输入，再跑本脚本即整体重建（与 §3c 的「fresh run 行数差异」同属既有边界）。

### 4.3 Steps that are **not** part of any level

These produce results the manuscript uses, but they are run **standalone** (or only the
archived copy is shipped). Keep them independent — do not claim `run_all.py` regenerates
them. All run from the package root `03_reproduction_package`.

| 主张或图表 | 完整命令 / 参数 / 种子 | 输出文件 | 验证方式 | 已验证范围 |
|---|---|---|---|---|
| ARC-MOF 输入组装（§3.15 前置） | `python scripts/prep_arcmof.py --data-dir data/arcmof --out data/arcmof/arcmof_confound.csv` | `data/arcmof/arcmof_confound.csv` | 复跑对比 | 仅有归档（真实下游是 `chemistry_seen.py --csv data/arcmof/arcmof_confound.csv` 的 ARC 逐拓扑分解与 `audit_revision_fixes.py` 的 ARC 熵审计；`confound_arcmof.csv` 由 `arcmof_confound.py` **直接读原始元数据**，不经此表） |
| ARC-MOF 逐拓扑 seen/unseen 分解（§3.15） | `python scripts/chemistry_seen.py --csv data/arcmof/arcmof_confound.csv --topology-col topology --tag arcmof` | `chemistry_seen_arcmof.csv`, `chemistry_seen_by_topology_arcmof.csv`, `topology_pair_overlap_arcmof.csv` | 复跑对比 | 仅有归档 |
| 零模型对照（§3.12 / §3.15 Result 3；SI §S3） | `python scripts/null_model_controls.py --outdir outputs --granularity coarse -b 10000 --b-card 1000`（row，默认）；`--level composition …`（组成级）；`--outdir outputs/_fine --granularity fine …`；`--outdir outputs/common_support --granularity coarse … --require-cols mc,flig,func` | `null_elite_permutation_row.csv`, `null_elite_permutation_composition.csv`, `null_topology_cardinality.csv`（+ `_fine/`、`common_support/`） | 复跑对比 | 仅有归档 |
| Figure S2 的 PDP 数据（§S15） | `python scripts/prepare_figS2_pdp_data.py --max-rows 25000 --n-jobs 1` | `pdp_geometry_curves.csv`, `pdp_geometry_meta.csv` | 复跑对比 | 仅有归档 |
| Figure S7 / SI Table S9 的数据步 | `python scripts/s_g_curve.py --max-rows 100000` | `s_g_curve.csv` | 复跑对比 | 仅有归档 |
| **修订轮新数字的只读复算**（§3.5 pooled 排除 pcu、§2.7/§3.15 Miller–Madow 与非单例率、§3.11 五种子汇总） | `python scripts/audit_revision_fixes.py`（不训练、不写文件） | 无（打印复算值） | 只读重算 | **已核查**（本修订轮运行一致） |

Provenance-only files（在包内但不被正文引用）：`chem_topo_confound.csv`、
`chem_topo_jaccard.csv`（Table 8 之前的 n = 50,000 视角，已被全库视角取代）。
`confound_by_source_arcmof.csv` **不随包发布**：每个来源库当初各用自己的拓扑列，
跨来源不可比，请用 `source_confound_granularity.csv`。未被编号的 `fig9_screening_utility.png`
（§3.11，有效但无图注）与 `leakage_comparison_final.png`（§3.1 中间视图）随包但不入正文；
`loto_per_metal_final.csv` **未随包发货**（需要时由 `mof_leakage_benchmark.py --loto` 生成）。

---

## 5. Full command list (levels **and** the standalone steps, for step-by-step checking)

```bash
cd 03_reproduction_package        # 是包根，不是 scripts/
# ---- level 1: core confound evidence (§3.2 / §3.4 / §3.12)
python scripts/confound_diagnosis.py --max-rows 50000 --size-match   # 50,000 view + controlled contrast + size-matched arm
python scripts/full_db_confound.py --tag full                        # full-database view (the headline numbers)
python scripts/chemistry_seen.py                                     # per-held-out-topology seen/unseen (Table 9)
python scripts/confound_diagnosis.py --max-rows 50000 --seeds 5      # 5-seed version quoted in the abstract
python scripts/elite_subset_confound.py
python scripts/elite_vs_full.py                                      # §3.12 attributions (Table 17)
python scripts/fig_confound_and_control.py

# ---- level 2: results, aggregation rules, seeds (§3.1 / §3.5 / §3.9)
python scripts/mof_leakage_benchmark.py --max-rows 100000 --loto --tag final
python scripts/mof_leakage_benchmark.py --max-rows 100000 --target selectivity --log-target --tag logsel100k
python scripts/plot_main_figure.py --outdir outputs
python scripts/metrics_audit.py
python scripts/multi_seed_repeat.py --max-rows 25000 --seeds 5 --skip-group --tag uptake25k_fix
python scripts/mof_leakage_benchmark.py --max-rows 25000 --mitigation --tag mit25k
python scripts/fig3_fig4_missing.py              # Figure 1 (final redraw) + Figure S5, plotting only
python scripts/fig_sg_curve.py                   # Figure S7, from archived s_g_curve.csv
python scripts/mof_leakage_benchmark.py --max-rows 100000 --loto --tag chemistry   # composition hold-out arm
python scripts/mof_leakage_benchmark.py --max-rows 100000 --drop-topology-block --tag notopo100k   # 415 features; §3.1's 21.5%

# ---- level 3: practical consequences (§3.11 / §3.13 / §3.14 / §4.2)
python scripts/screening_utility.py --max-rows 25000
python scripts/screening_utility.py --max-rows 25000 \
       --strategies random,topology,linker_pair,metal,chemistry --tag chemistry
python scripts/multitarget_confound.py --max-rows 25000 --top-linkers 200 \
       --resid-estimators 60 --outdir outputs
python scripts/fig_multitarget.py
python scripts/derive_multitarget_stats.py
python scripts/chemistry_seen_grouping.py --max-rows 25000
python scripts/diversity_control.py            # arm (d), composition-matched draw (§3.4)
python scripts/partner_coverage_arm_e.py        # arm (e)/(f) (§3.4)
python scripts/mof_leakage_benchmark.py --max-rows 100000 --model gb    --tag gb100k
python scripts/mof_leakage_benchmark.py --max-rows 100000 --model ridge --tag ridge100k

# ---- grouping sensitivity of the identity effect (§4.2; ~25 min each)
# topology is the default and writes multitarget_confound.csv; the other two
# write multitarget_confound_<group>.csv and leave the main table untouched.
python scripts/multitarget_confound.py --max-rows 25000 --top-linkers 200 \
       --resid-estimators 60 --outdir outputs --group-col metal
python scripts/multitarget_confound.py --max-rows 25000 --top-linkers 200 \
       --resid-estimators 60 --outdir outputs --group-col linker_pair

# ---- five-seed screening utility (§3.11 five-seed block; STANDALONE, not a level)
# Each seed re-draws sampling + model; the five CSVs are pooled by hand for the
# mean ± sd reported in the manuscript. Seed 42's run above (Table 16) is the
# favourable end of the topology row; do not mistake it for the five-seed mean.
for S in 42 143 244 345 446; do
  python scripts/screening_utility.py --max-rows 25000 --seed $S --no-figure --tag seed$S
done

# ---- ARC-MOF input prep (§3.15; STANDALONE — not a step of any level)
# Assemble the four metadata files into the columns the confound statistics expect,
# then run the per-held-out-topology decomposition on that assembled input.
python scripts/prep_arcmof.py --data-dir data/arcmof --out data/arcmof/arcmof_confound.csv
python scripts/chemistry_seen.py --csv data/arcmof/arcmof_confound.csv \
       --topology-col topology --tag arcmof

# ---- level 4: cross-database replication (§3.15; needs the ARC-MOF files)
python scripts/arcmof_confound.py --top-n-topo 40 --out-tag arcmof
python scripts/exclusivity_across_databases.py
python scripts/source_confound_granularity.py --min-source-n 200 --boot 10   # --boot, NOT --seeds
python scripts/source_spread_test.py                                          # valid spread test (see note)
python scripts/arcmof_overlap.py
python scripts/sample_size_granularity.py

# ---- null-model controls (§3.12 / §3.15 Result 3; standalone, not part of a level)
# Run BEFORE drawing Figure S6 (its panel b needs common_support/null_topology_cardinality.csv).
python scripts/null_model_controls.py --outdir outputs                --granularity coarse -b 10000 --b-card 1000
python scripts/null_model_controls.py --outdir outputs --granularity coarse --level composition -b 10000 --b-card 1000
python scripts/null_model_controls.py --outdir outputs/_fine          --granularity fine   -b 10000 --b-card 1000
python scripts/null_model_controls.py --outdir outputs/common_support --granularity coarse -b 10000 --b-card 1000 --require-cols mc,flig,func

# ---- S_g data step (§S14 / SI Table S9; standalone) — run before Figure S7
python scripts/s_g_curve.py --max-rows 100000

# ---- intermediate figure versions (200 dpi; NOT the final rasters — do not let these
# overwrite ../01_manuscript/figures/*.png produced by pubfig below)
python scripts/fig_cross_database.py
python scripts/fig_source_confound.py

# ---- level 5: mechanism analyses + SHAP (slow, optional)
# Order and flags match run_all.py --level 5 exactly; this list previously omitted
# refuted_explanations.py and cardinality_correction.py (fixed 2026-10-16).
python scripts/leakage_mechanism.py --max-rows 25000 --family --tag final
python scripts/refuted_explanations.py --max-rows 25000
python scripts/omitted_variable.py --max-rows 25000 --within-vs-cross --tag final
python scripts/cardinality_correction.py --max-rows 25000 --perm 3
python scripts/plot_within_cross.py
python scripts/figures_and_shap.py --max-rows 25000 --shap-samples 200 --tag final
python scripts/plot_shap_family.py --csv outputs/fig5_shap_family_final.csv \
       --out outputs/figS1_shap_family_final.png

# In a sandbox that cannot create named pipes, set n_jobs = 1 for the three
# scripts that fit a random forest. Fixed random_state makes the fitted values
# independent of n_jobs, so the numbers are identical:
#   omitted_variable.py       --n-jobs 1
#   cardinality_correction.py --n-jobs 1
#   leakage_mechanism.py      LEAKAGE_MECH_N_JOBS=1  (environment variable)
#
# Two of the seven steps -- refuted_explanations.py (step 2) and figures_and_shap.py
# (step 6) -- additionally require the optional `shap` package. On a host with no
# outbound network access `pip install shap` cannot complete, and those two steps
# cannot be re-run to completion; the other five can. The published SHAP numbers are
# checked in that situation against the archived `outputs/fig5_shap_family_final.csv`
# (the identity-family share is 17.67% under the random split and 14.86% under the
# topology hold-out, i.e. the 17.7% / 14.9% quoted in section 3.6), and step 7 still
# regenerates Figure S1 from that archived CSV without needing shap.
#
# Normalisation note, because two scripts print different percentages for the same
# effect: the "family overlap explains X% of dR2" figure quoted in the manuscript and
# in SI S1 (16%) comes from refuted_explanations.py, whose denominator is the full
# random-split R2 minus the hold-out R2. leakage_mechanism.py prints its own version of
# the same diagnostic (14%) using the family-SEEN subset R2 as the baseline; that subset
# is only 8.9% of test rows and scores higher than the whole random split (0.7555 vs
# 0.7062), so its denominator is smaller and the percentage lower. Both prints are
# internally consistent; the manuscript quotes the refuted_explanations.py convention.
# Recomputing from leakage_mechanism's own fig7_family_summary_final.csv gives
# 0.054076 / 0.340747 = 15.9%, i.e. the quoted 16%.

# ---- Figure S2 data step (centred partial dependence; STANDALONE, not a level)
# SI Figure S2 was changed from a per-sample SHAP dependence plot to centred partial
# dependence. Its data are produced by this script, and the final figure by pubfig.
python scripts/prepare_figS2_pdp_data.py --max-rows 25000 --n-jobs 1

# ---- FINAL submission figures (600-dpi rasters)
# The pubfig builders read the archived CSVs and write vectors to figures_pub/*.pdf|svg
# and rasters to scripts/pubfig/_raster/*.png|tiff by default — NOT into
# ../01_manuscript/figures/. To update what the PDF embeds, set PUBFIG_RASTER to
# ../01_manuscript/figures when running (or copy _raster/*.png there), then rebuild the PDF.
# They are NOT steps of run_all.py. style.py's alignment gate needs the external
# `audit_panel_alignment` module; without it the gate is skipped (recorded) and the
# figures still export (see FIGURE_QA_PUBLICATION.md).
python scripts/pubfig/build_main_1_4.py   1 2 3 4     # Figures 1-4
python scripts/pubfig/build_main_5_8.py   5 6 7 8     # Figures 5-8
python scripts/pubfig/build_si_S1_S7.py   S1 S2 S3 S4 S5 S6 S7   # Figures S1-S7

# ---- export: copy the 600-dpi rasters into ../01_manuscript/figures (what the PDF embeds)
# Paths here are relative to the package root 03_reproduction_package, so the submission
# figure directory is the SIBLING ../01_manuscript/figures (not ./01_manuscript/figures).
# Run this AFTER the old 200-dpi figure scripts above, so the final rasters are the last
# to touch the directory. The script copies all 15 _raster/*.png into
# ../01_manuscript/figures/ and the two SI PNGs (figS6, figS7) into outputs/, then
# --check confirms byte-identity. (Equivalent one-liners if you prefer not to run it:
#   PowerShell: Copy-Item scripts/pubfig/_raster/*.png ../01_manuscript/figures/ -Force
#   POSIX:      cp scripts/pubfig/_raster/*.png ../01_manuscript/figures/ )
python scripts/export_final_figures.py
python scripts/export_final_figures.py --check

# ---- checksum manifest: regenerate it, then verify it (do this LAST, after ALL outputs)
python scripts/make_md5sums.py            # re-enumerate outputs/ -> outputs/MD5SUMS.txt
python scripts/make_md5sums.py --check    # exit 0 only if manifest == archive

# ---- read-only audit of the revision-fix numbers (§3.5 / §2.7 / §3.15 / §3.11)
# Recomputes pooled excl-pcu = 0.4629, the Miller–Madow corrections, the ARC non-singleton
# rates, and the five-seed screening summary. No model training, writes nothing.
python scripts/audit_revision_fixes.py
```

> Why `--max-rows 50000` and not 25,000 in level 1: several reference numbers in
> §3.2 are quoted at n = 50,000, and the n = 25,000 figure (98.9%) is a different
> number that must not be mixed with them. The headline number of the paper is
> computed on the **full** database by `full_db_confound.py`, precisely because
> the statistic depends on n.

---

## 6. Known pitfalls (each one already handled in the code — do not revert them)

1. **Never use `head()` on either CSV.** Both hMOF files are sorted by topology;
   the first rows contain only a handful of topologies. Sampling goes through
   `df.sample(..., random_state=42)` everywhere. (The CIF bundle is worse: its
   first 35,000 entries are all pcu.)
2. **Take logs of ratio targets.** CO₂/N₂ selectivity has a median of 8.2 and a
   maximum of 31,634; without the log transform R² swings between +0.42 and
   −0.06 depending on the draw.
3. **Always report four aggregation rules.** `pooled` (concatenate every fold's
   predictions, then compute one R²) and `macro` (mean of per-fold R²) use different
   denominators and can disagree in sign: with pcu holding 63% of hMOF, pooled gives
   +0.381 while macro gives −0.541 and median +0.278. Recomputing pooled while dropping
   only the pcu **scoring fold** gives +0.4629 over the remaining 36,553 rows (still
   positive and higher) — the pooled value is **not** produced by the pcu fold alone,
   and "excluding pcu" must always say whether you mean the scoring fold or the training
   data. Per-group aggregates excluding pcu give weighted −0.678 and macro −0.625.
4. **Check target variance before comparing R² across splits.** Our own CGCNN
   experiment failed on exactly this: the two test sets differed by a factor of
   7.7 in target variance, R² looked catastrophic (−0.448) while MAE was in fact
   *better* on the held-out side (0.262 vs 0.396). That arm has been withdrawn.
5. **Changing the support set changes the denominator.** Metrics on different
   subsets cannot be subtracted. §3.11 therefore compares all four splitting
   strategies on out-of-fold predictions for the *same* 25,000 samples, against
   the same oracle.
6. **Fail loudly on empty frames.** `build_features()` one-hot encodes only
   `functional_groups`, `metal_linker` and `topology` — it does **not** emit
   columns with a `linker_pair_` prefix, so a prefix-based selection silently
   returned an empty frame and the check that used it was skipped without error.
   Likewise, ARC-MOF's `all_topology_lists.csv` has its **first two column names
   swapped** (`Name` holds CIF filenames, `filename` holds topology labels), which
   made every merge empty. Both now assert.
7. **Verify MD5 after downloading.** Two files were truncated during a parallel
   download while `curl` still exited 0. Materials Cloud has also served HTTP 503
   for every record, returning a small HTML error page that would otherwise be
   appended straight into a data file. Check the HTTP status and the file tail.
8. **Do not align chemical granularity by random compression.** Random coarsening
   can only make a chemical definition *coarser*, never finer, so the larger
   library is compressed harder and the apparent spread explodes (we measured
   406%). Versions 1 and 2 of `source_confound_granularity.py` failed this way
   and are withdrawn. Version 3 uses two **real** chemical definitions plus
   bootstrap resampling of the *samples* — never of the chemistry.
9. **Align on r = n / M (samples per distinct composition), not on absolute n.**
   The two databases differ by two orders of magnitude in M; aligning on raw
   sample count aligns nothing.
10. **Report the number of valid folds.** When a test fold has zero target
    variance, R² is undefined; silently keeping NaN turns `macro` into NaN. This
    affects 3 of our 5 seeds, so the effective fold count is 10–11, not always 11.
11. **Never test a source-level difference using bootstrap draws as replicates.**
    An earlier version passed the 10 bootstrap replicates *per source* to
    Kruskal–Wallis. Those draws are resamples of one sample, not independent
    observations, so the resulting p-value is pseudo-replicated and has been
    withdrawn. `source_spread_test.py` simulates the correct null instead (one
    common rate; the statistic is the variance of the per-source proportions, and
    `scipy.stats.kruskal` on the *sources* would give the same answer on this data).
    Rule of thumb: if your replicates come from the same underlying sample, they are
    not a sample of sources.
12. **A missing value is not the string `"nan"` — pandas 3.0 changed this.**
    Under pandas < 3, `df[cols].astype(str).agg("|".join, axis=1)` silently turned a
    missing entry into the literal `"nan"`, so rows with no `functional_groups`
    became their own "chemical composition". Under pandas 3.0 the same expression
    keeps `NaN` and raises `TypeError: sequence item N: expected str instance,
    float found`. Build composition keys only after an explicit
    `dropna(subset=cols)` (this is what `null_model_controls.py` does). Concretely:
    61 of the 8,206 elite hMOF rows carry no `functional_groups`, which moves the
    fine-grained composition count M from **6,214** (missing rows dropped) to
    **6,275** (missing counted as a composition); the manuscript quotes the
    dropped-value figure, 6,214.

---

## 7. Analyses deliberately excluded

These scripts remain in the repository for provenance. They are **not** run by
`run_all.py` and their numbers are **not** used anywhere in the manuscript.

| Script | Why it is excluded |
|---|---|
| `cgcnn_mof.py` | Evidence withdrawn on 2026-10-09: the two test sets differed 7.7× in target variance and the held-out side had *smaller* MAE, so the original conclusion pointed the wrong way (§3.7; the arm is represented only by its diagnostic, SI Table S2 — it holds no main-text table number). |
| `granularity_control.py` | The alignment method this paper itself rules out (§4.3 granularity declaration; the withdrawn alignment has **no** table). `outputs/granularity_control.csv` is kept only to trace the history. |
| `chemistry_topology_factorial.py` | Design 2 is void: 387 of the 388 "multi-topology" compositions span only pcu ↔ nbo, and nbo's target variance is 1/29 of pcu's, so any comparison is meaningless (§3.3). |
| `source_confound_granularity.py`, v1 and v2 | v1 filtered topologies with a source-size-dependent threshold (DB0 down to 5 topologies, DB6 to 1, where the statistic is trivially 100%); v2 used the withdrawn random-compression alignment. The current file is v3. Do not revert. |
| `data/fetch_db2.sh`, `data/fix_part6.sh` | Download helpers for a Materials Cloud archive that returned 503 for every record; not needed. |

### One archived model artefact is not redistributed

`figS2_randomforest.joblib` — the fitted random-forest estimator behind the SHAP dependence
panel of Figure S2 — is **not** in `outputs/` and is **not** listed in `MD5SUMS.txt`. It is a
model object, not a result: nothing in the manuscript quotes a number read out of it, and
every figure that depends on it is regenerated from an archived CSV. Rebuild it with

```
python scripts/figures_and_shap.py --max-rows 25000 --shap-samples 200 --tag final
```

(the same command that produces `figS2_shap_dependence.png` and
`fig5_shap_family_final.csv`; `--shap-samples 200` is the value used for the published
figures). Level 5 is otherwise reproduced as documented above; this artefact is excluded
only because it is ~272 MB, not because any step is withheld. An earlier manifest listed
the file with a checksum, which made `make_md5sums.py --check` fail on a file that was
never shipped; the regenerated manifest no longer carries that entry.

---

## 8. What we deliberately do *not* claim

Stated here so that a reader cannot misread the pipeline as evidence for
something larger than it is:

- ARC-MOF is **not** independent of hMOF. It spans all public MOF databases and
  shares authors with hMOF, and its v6 notes mention removing structures from the
  Boyd–Woo database. Level 4 therefore does **not** claim an independent
  replication; `arcmof_overlap.py` bounds the effect of any overlap by removing
  one source sub-library at a time (98.6–99.8%).
- Cross-database magnitudes are **not comparable** unless the target, the
  granularity of "chemistry" and the aggregation rule are declared together.
- The controlled contrast rests on **one** isoreticular pair (pcu ↔ nbo).
- One set of structure-derived scalar descriptors is used; there is no deep-learning
  arm in the current results (withdrawn, §3.7). The random-versus-topology gap was
  refitted under gradient boosting and ridge (§3.1), so it is not an artefact of the
  model family — but model capacity itself remains untested.
