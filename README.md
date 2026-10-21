# What does topology hold-out actually test?

### Chemistry–topology confounding in enumerated MOF databases

Reproduction package for the manuscript

> **Version pointer (2026-10-21).** The current manuscript is the **v6 compressed
> submission package** (4 main figures, 18 SI tables), *"What topology hold-out
> removes — and what it does not"*. In the working tree it is the sibling package
> `03_投稿专用包_v6压缩/`; in the v1.3 release it ships inside this archive as
> `manuscript_v6/` (manuscript, SI, figures, cover letter and its own reproduction
> supplement). The analysis record in this file is the v5 full-pipeline record.
> Where the two differ — five-seed headline values replace seed-42 values, and the
> ARC-MOF headline is the coarse 99.3% — **the v6 manuscript is authoritative**.

> **Topology hold-out in the two enumerated MOF databases studied here is largely
> chemistry hold-out: the two variables are structurally entangled, and the field's
> gold-standard protocol therefore does not measure what it is usually read to
> measure**
>
> **Superseded by the v6 manuscript** (see the version pointer above), which reports
> the support loss (74.7% of coarse compositions are single-topology) and a
> descriptive protocol ratio (the chemistry-key hold-out costs 21.1% of the topology
> hold-out's R² decrease), and does **not** attribute the topology penalty to
> chemistry. This boxed summary and the repository name are retained as a historical
> working title, not as the claim of the current manuscript.

Everything here is written for a reader who wants to check the claims, not take
them on trust: one command per level regenerates the results assigned to that level.
All five levels have been run end to end — level 5 on 2026-10-14, with a per-step log
archived for every step in `outputs/logs/`.

| Document | Purpose |
|---|---|
| `README.md` | this file — claims, layout, quick start, honest limits |
| `REPRODUCE.md` | detailed reproduction manual: levels, **the single authoritative claim/figure/table → producer → verification mapping (§4)**, known pitfalls |
| `REPORTING_CHECKLIST.md` | **portable deliverable** — a 22-rule reporting checklist for anyone publishing a grouped-split result, derived from this study's own mistakes (one-page summary table first, evidence below) |
| `DATA.md` | datasets, MD5 checksums, download commands, two data traps, citations |
| `FIGURE_MANIFEST.md` | figure-number ↔ PNG-filename correspondence only (and the exclusion list of figures that must not be embedded); production/verification is in `REPRODUCE.md` §4 |

The two new files under `scripts/` and the root are **not** part of the fixed
L1–L5 pipeline: `confound_diagnostic.py` is a standalone tool you can point at
*any* CSV with a grouping column and a chemistry definition, and
`REPORTING_CHECKLIST.md` is the write-up of what to do with its answer. They
exist because the paper's narrowest, most defensible claim — "report this
diagnostic before reporting a grouped-split score" — is only useful if it ships
with the tool that computes it. The diagnostic reproduces this paper's
n = 50,000 numbers **exactly** (coarse 0.7533 / 0.1782; fine 0.9797 / 0.0233;
pcu–nbo 387 shared, J = 0.358), and on synthetic data with a known answer it
correctly reports "largely independent" for independent chemistry and
"relabelling of chemistry" for deterministic chemistry.

---

## One-sentence summary

In enumerated (hypothetical) MOF databases, holding out a topology is *in practice*
holding out a chemistry — at coarse granularity 74.7% of chemical compositions occur
in a single topology and only 18.0% of the information in the topology label survives
conditioning on chemical composition (7.8% at the fine granularity) — so "topology
hold-out" does **not**
measure what it is widely claimed to measure.

Note the deliberate wording: **"largely", not "identically"**. The confound is a
measured quantity that moves with sample size (98.9% at n = 25,000 → 93.2% at
324,426), not a structural identity. One pair of topologies (pcu ↔ nbo) retains
enough independence to support a controlled experiment, which is exactly what
claim 2 exploits.

---

## Claims, and exactly where each one comes from

> This is a **high-level** claim → section → script overview. The **authoritative**
> claim/figure/table → full command → output → verification mapping (including seeds,
> standalone steps, and the "verified / historical re-run / archive-only / not-verified"
> status of every step) is maintained in **`REPRODUCE.md` §4** — do not edit one without
> the other.
>
> Section numbers in the third column refer to the **v5** manuscript. The v6
> manuscript reorganises the results: support audit §3.1, protocol contrasts §3.2,
> interventions §3.3, screening §3.4, ARC-MOF §3.5.

| # | Claim | Section | Script(s) |
|---|---|---|---|
| 1 | On the **full** hMOF database (324,426 structures) at **coarse** granularity — the granularity §3.2 selects for the headline — **74.7%** of chemical compositions occur in a single topology and H(topology \| chemistry) / H(topology) = **18.0%**; only **2 of 55** topology pairs share any chemistry (pcu ↔ nbo, rht ↔ tbo; every other pair has Jaccard = 0.000). The **fine**-granularity values (**93.2%**, **7.8%**) are **robustness checks, not the headline**: they are inflated by singleton compositions (at least 39.8% of fine compositions occur exactly once, and a singleton is single-topology by construction) and carry a Miller–Madow correction of ≈0.0307 bit, i.e. 22% of the estimate. The statistic is **sample-size dependent** — 98.9% at n = 25,000 — so it is always reported with n. At coarse granularity the observed singleton count is 21 of 1,622 (1.3%), and the single-topology fraction among the remaining 1,601 is 74.4%, so the headline is not a singleton artefact | §3.2 | `full_db_confound.py` |
| 1b | **What a topology hold-out actually removes.** Three nested levels: **74.7%** of *compositions*, **61.3%** of *structures* and **44.2%** of *composition–topology memberships* are single-topology. Decomposed per held-out topology, **7 of the 11 topologies are pure chemistry hold-outs** (sra, etb, acs, bcu, pts, fof, the: 69,224 structures, 21.3% of the database, **100.0% unseen**), against 60.1% (pcu), 12.3% (nbo) and 0.0% (rht, on 14 structures). No composition spans more than two topologies, so the pairwise view is exact | §3.2 (Table 9) | `chemistry_seen.py` |
| 2 | A **controlled isoreticular contrast** (same test set, only the training set changes; pcu ↔ nbo; five outer seeds 42/143/244/345/446; five-seed mean ± SD): removing the matched topology raises nbo-side **MAE +70.0%** (0.1065 ± 0.0032 → 0.1811 ± 0.0136 mmol/g; paired difference +0.0746, 95% t-interval +0.0592 to +0.0900) and RMSE +77.9%, far beyond seed noise; the pcu side does not move (−1.2%). A **size-matched arm (c)** that draws the same number of training rows at random from the full pool (n_train 10,656 against 42,381) leaves MAE essentially unchanged (0.1071 ± 0.0048; five outer seeds × five size-matched draws, averaged within seed before the seed-level SD — the seed-42 repeated-draw auxiliary c gives 0.1030 ± 0.0031, a distinct replication design kept in SI-C), so the degradation tracks **which rows** were removed, not how many. **Arm (d)**, the composition-profile-matched draw, is confined to (b)'s own row set (five-seed means: 42,381 − 31,725 = 10,656; seed 42: 42,329 − 31,682 = 10,647) and its aggregated MAE equals (b)'s by construction (nbo 0.1811 ± 0.0136; pcu 0.2396 ± 0.0010) — a construction-consistency check expected by construction, not independent corroboration. **Arm (e)** removes *only* the partner rows whose composition also occurs in the test set (12,342 rows carrying the 388 shared compositions, 387 at the seed-42 baseline), leaving 1,144 of 1,532 compositions and 30,039 of 42,381 rows: nbo-side MAE 0.1326 ± 0.0082 — more than the full pool but far less than removing the whole partner — while its size-matched draw (f) gives 0.1250 ± 0.0073, essentially unchanged from (e) and still far better than (b). The 34.9% / 65.1% split of the (a)→(b) degradation is an **ordering of magnitudes inside one contrast**, not a decomposition into two independent causal factors. The effect is **direction-dependent**: on the pcu test set arm (e) *improves* MAE to 0.2293 against arm (a)'s 0.2424 (paired (e)−(a) = −0.0131, 95% CI −0.0167 to −0.0096; (f)−(b) = −0.0092, −0.0144 to −0.0040), so the improvement is not a seed artefact. Post hoc, **arm (g)** removes the same number of partner rows at random without conditioning on shared composition and lies between (a) and (e) on both sides (pcu 0.2341; nbo 0.1189), so shared composition is a consistent increment on top of a generic partner-removal effect (SI-C.4). Partner coverage is therefore not uniformly beneficial | v5 §3.4/§4.5; v6 §3.3 | `confound_diagnosis.py --size-match`, `diversity_control.py`, `partner_coverage_arm_e.py`, `partner_random_g.py` |
| 3 | Reporting discipline: the same leave-one-topology-out predictions give pooled R² = **+0.381**, weighted **−0.059**, macro **−0.541** and median **+0.278**. The summaries use different denominators: recomputing pooled while dropping only the pcu **scoring fold** gives +0.4629 (still positive and higher), while the per-group aggregates excluding pcu give weighted **−0.678** and macro **−0.625**. A single pooled number does not disclose the sign and volatility of the per-group view | §3.5 | `metrics_audit.py` |
| 4 | In the currency practitioners care about — one shared support set, ranking metrics that assume nothing about target variance — across **five independently redrawn 25,000-sample support sets** (seeds 42, 143, 244, 345, 446) random-split validation recovered **50.4 ± 2.5%** of the true top 1% and topology-grouped validation **19.3 ± 7.1%** (mean ± SD), a fall of **31.1 percentage points**; the seed-42 baseline gives 50.8% → 13.2%. The intermediate strategies fill the ordering: chemistry key 44.0 ± 2.8%, linker pair 41.1 ± 4.1%, metal 29.2 ± 4.8%. Materials selected under topology-grouped validation averaged 1.742 ± 0.158 mmol/g, **46.3% below** the mean oracle uptake (seed-42: 1.587 against an oracle 3.319). Widening the budget to k = 5% and 10% attenuates but does not erase the gap, and the budget trend is **non-monotonic** (31.1 / 23.5 / 26.6 pp). Recovery stays far above the 1% chance level in every scheme — even the worst strategy selects ~19× the random expectation — but the gap between the best and the worst protocol is the point, not the absolute level. Random performed best and topology worst in all five seeds; the complete five-strategy ordering held in four of five, so the two endpoint rankings are robust while the middle ordering is seed-sensitive | v5 §3.11; v6 §3.4 | `screening_utility.py` |
| 5 | On the elite subset the confound is **not diluted** — and the subset cannot show it strengthening: among hMOF's own elite subset (8,206 MOFs ≥ 2.0 mmol/g) **100.0%** of compositions are single-topology and H(topology \| chemistry) = **0.000 bit**, so the observable difference between "topology hold-out" and "chemistry hold-out" remains zero where screening actually selects. A **sample-level topology permutation null** puts the expected value at **21.4%** (sd 1.0%; 95% interval 19.4–23.4%; b = 10,000, **p < 1/10,000**), so this is not an arithmetic consequence of the subset's size or of its narrower topology pool. The stronger reading — that the coupling *strengthens* with performance — is **not** claimed: the subset contains no nbo, the one topology whose chemistry could overlap pcu's, so the zero rests partly on the selection rule; finer-grained counts are inflated by singletons and are reported only as robustness checks | §3.12 | `elite_subset_confound.py`, `null_model_controls.py` |
| 6 | Across **10 targets** in a 2×2 design the **split** effect spans **0.001–0.571** (median 0.324, positive on 10/10, Wilcoxon p = 0.0020), while the **identity-feature** effect *within* a grouped split is indistinguishable from zero (median −0.011, 8/10 negative, p = 0.28) — the same features are worth **+0.031** under a random split (p = 0.0039). The identity effect is also **grouping-dependent**: zero for topology (−0.011) and metal-centre (+0.001, p = 0.49) groupings, but **+0.032 (p = 0.0039)** for the fine linker-pair grouping — so the "identity features are worthless under a grouped split" advice must **not** be generalised beyond coarse groupings. The mechanism is **measured, not inferred**: the grouping variable's own one-hot block is unavailable by construction (0.000 in every grouped split), and the effect size tracks the availability of the *surviving* identity blocks — 0.827 → −0.011, 0.909 → +0.001, 1.000 → +0.032, 1.000 → +0.031 (Spearman ρ = +0.95 under the tie convention of §4.2; the ρ = +1.00 ordering rests on a 7×10⁻⁶ availability difference and is deliberately not quoted) | §3.13, §3.14, §4.2 (Table 26) | `multitarget_confound.py`, `--group-col {metal,linker_pair}`, `chemistry_seen_grouping.py` |
| 7 | **Replicated on a second database** built by a different pipeline (ARC-MOF v6, 264,225 structures, of which 256,351 carry both metal and linker cluster keys — the other 7,874 lack them and are excluded; 301–486 topologies depending on which of the three topology columns shipped with the dataset is used): the coarse single-topology fraction is **99.3%**, which remains **97.3%** among the 49,869 non-singleton compositions, and the fine key gives **99.7%** (98.2% among its non-singletons) — the coupling does not reduce to a sparse-count artefact. ⚠️ ARC-MOF is **not independent** of hMOF (it spans all public MOF databases and shares two authors with it), so we **do not** claim independence; instead we bound any overlap by removing **any single** source sub-library, at **both** of the paper's chemistry definitions: the worst case (DB0 removed wholesale) leaves **98.57%** at the coarse granularity and **98.96%** at the fine one, and every other single removal leaves 99.22–99.84% | v5 §3.15; v6 §3.5 | `arcmof_confound.py`, `arcmof_overlap.py` |
| 8 | **The confound is not uniform inside one database either.** Across ARC-MOF's source sub-libraries (7 with ≥ 200 samples and > 1 topology) it spans **86.1%–100.0%**, a spread 3,554× larger than a one-common-rate binomial null predicts (parametric bootstrap **p < 1/20,000**; `source_spread_test.py` — an earlier Kruskal–Wallis p was **withdrawn**, it was pseudo-replicated over bootstrap draws). The ordering is **identical at both real granularities** (Spearman ρ = 1.000). Confounding is a property of *how each sub-library was built*, not a constant of the database, and **not** a projection of topology richness: a within-source permutation null (sample-level, b = 1,000 per source) puts every source's observed exclusivity above its own null, with the excess running from **+2.6 pp** (DB15) to **+37.3 pp** (DB12) and no significant correlation with H(T) (Pearson r = +0.67, p = 0.10; Spearman ρ = +0.32, p = 0.48; Figure S6b) | §3.15 | `source_confound_granularity.py`, `null_model_controls.py`, `fig_source_confound.py` |
| 9 | Cross-database magnitudes are **not comparable** unless three things are declared together: the **target**, the **granularity** at which "chemistry" is defined, and the **aggregation rule**. Compare at matched n (this effect alone is 98.9% → 93.2% inside hMOF) and never by randomly compressing the chemistry to a common granularity | §3.13–§3.15 | `sample_size_granularity.py`, `multi_seed_repeat.py` |

Two results we **withdrew ourselves**, stated here so nobody repeats them:
an earlier deep-learning (CGCNN) comparison is void because its two test sets
differed 7.7× in target variance (§3.7), and an earlier cross-database
granularity alignment used the very method this paper rules out (withdrawn
Table 13).

### 2026-10-14: what changed in this package

Three archive defects were found by re-deriving the manuscript's numbers from the
shipped data, and are fixed here. In every case **the manuscript was right and the
archive was wrong**, so the fix was to the scripts and the stored outputs, not to
the text. Details and the file-by-file consequences are in `REPRODUCE.md` §3d.

1. `scripts/elite_vs_full.py` matched rows on the DataFrame **index** instead of on
   the `MOFname` key (it looked for a `filename` column that neither hMOF file has,
   and silently fell back to positional matching). The regenerated
   `outputs/elite_vs_full.csv` and `outputs/elite_vs_full_by_topology.csv` now
   reproduce §3.12 exactly — pcu lost 265, sra lost 825, tbo lost 1, excluded-row
   mean uptake 2.685 against retained 2.580, and the 131 elite compositions that are
   multi-topology in the full database. The script now asserts on the key and on the
   `retained + lost == qualifying` identity instead of degrading silently.
2. `scripts/partner_coverage_arm_e.py` recorded arm (f)'s `n_train` as the 50,000-row
   pool size, because a boolean mask was passed where an index array was expected.
   Arm (f) has been re-run with the corrected code; its MAE moved in the second
   decimal (nbo 0.1256 → 0.1250, pcu 0.2295 → 0.2304), and the manuscript and
   SI Table S8 supplement carry the regenerated values. `n_train` now equals arm
   (b)'s for every seed, and the script asserts that.
3. `scripts/elite_subset_confound.py` used the `fillna("NA")` convention for the
   elite **fine** count, giving 6,275 compositions over 8,206 rows, where Table 17
   declares 6,214 over 8,145. The archive now carries the declared `elite_fine` row
   **and** the `elite_fine_fillna` row, so both conventions are on the record.

The checksum manifest is now generated rather than hand-maintained:
`python scripts/make_md5sums.py` (and `--check` to verify it). It previously claimed
to cover every file in `outputs/` while listing 65 of 78, and one listed entry
(`arm_e_partner_coverage.csv`) carried a stale hash and byte count. Run this step
after any re-run; `run_all.py` now does it automatically.

---

## Repository layout

```
03_reproduction_package/
├── README.md              ← this file
├── REPRODUCE.md           ← detailed reproduction manual (levels, pitfalls, exclusion list)
├── REPORTING_CHECKLIST.md ← portable checklist: what to report with a grouped-split result
├── DATA.md                ← datasets, MD5 checksums, download commands, citations
├── requirements.txt       ← 5 packages (+ shap for level 5); no torch, no GPU
├── .gitignore             ← keeps data and scratch outputs out of the commit
├── LICENSE                ← MIT, code only (data licenses: see DATA.md)
├── scripts/
│   ├── run_all.py                       ← one-command reproduction, 5 levels
│   ├── confound_diagnostic.py           ← standalone tool: run the diagnostic on any CSV
│   ├── confound_diagnosis.py            ← claims 1, 2  (core: confound + controlled contrast)
│   ├── full_db_confound.py              ← claim 1  (headline numbers, no sampling)
│   ├── elite_subset_confound.py         ← claim 5
│   ├── metrics_audit.py                 ← claim 3
│   ├── screening_utility.py             ← claim 4
│   ├── multitarget_confound.py          ← claim 6  (2×2 design, 10 targets)
│   ├── mof_leakage_benchmark.py         ← baselines, leave-one-group-out, mitigation
│   ├── multi_seed_repeat.py             ← claim 9  (aggregation stability, 5 seeds)
│   ├── arcmof_confound.py               ← claim 7  (ARC-MOF)
│   ├── arcmof_overlap.py                ← claim 7  (leave-one-source-out bound)
│   ├── source_confound_granularity.py   ← claim 8  (per-source sub-libraries, v3)
│   ├── sample_size_granularity.py       ← claim 9  (sample-size dependence)
│   ├── cardinality_correction.py        ← Table 15  (ω² + permutation null for the η² caveat)
│   ├── partner_coverage_arm_e.py        ← §3.4 arm (e)/(f): separates composition diversity from matched-partner coverage
│   ├── elite_subset_confound.py         ← claim 5  (elite subset, both missing-value conventions)
│   ├── elite_vs_full.py                 ← §3.12 attributions: per-topology losses, the two mean uptakes, the 131
│   ├── make_md5sums.py                  ← regenerates outputs/MD5SUMS.txt (`--check` to verify)
│   ├── fig_*.py, plot_*.py              ← every figure in the manuscript
│   └── ...                              ← earlier analyses, kept for provenance (see below)
├── data/                  ← not committed; obtain via DATA.md (verify MD5!)
└── outputs/               ← every CSV and figure quoted in the manuscript
```

### v1.3 archive layout

The v1.3 release (GitHub tag `v1.3`, Zenodo archive) merges this reproduction
package with the v6 submission package: this tree stays at the **archive root**
and the v6 package — manuscript, SI, figures, cover letter and its own
reproduction supplement — is added as **`manuscript_v6/`**. Every path in
`DATA.md`, `REPRODUCE.md` and this file therefore stays valid inside the archive;
`manuscript_v6/03_reproduction_package/REPRODUCE.md` maps every v6 claim to its
producer and states what the v6 supplement adds.

Scripts outside the fixed pipeline, kept only so the history can be traced:
`granularity_control.py` (withdrawn) and `chemistry_topology_factorial.py` (design void).
`cgcnn_mof.py` (the withdrawn deep-learning arm) is **not** in this package — it was moved
out of the submission package on 2026-10-13 and is represented here only by its diagnostic
(SI Table S2) and by the exclusion note in `REPRODUCE.md` §7. Reasons are given in
`REPRODUCE.md`, section "Analyses deliberately excluded".

---

## Quick start

```bash
# 1. environment — five packages (+ shap for level 5), CPU only
pip install -r requirements.txt

# 2. data — see DATA.md for URLs and MD5 checksums
#    hMOF    -> data/all_MOFs_screening_data.csv, data/top_MOFs_screening_data.csv
#    ARC-MOF -> data/arcmof/*.csv          (needed only for level 4)

# 3. reproduce
cd scripts
python run_all.py --level 1        # 7.3 min   core evidence: claims 1, 2, 5
python run_all.py --level 2        # 65.4 min  baselines, aggregation rules, seeds
python run_all.py --level 3        # 78.5 min  practical consequences, 10 targets
python run_all.py --level 4        # 29.9 min  cross-database replication, claims 7, 8
python run_all.py --level 5        # ≈5.5 h*   mechanism analyses + SHAP
# * level 5's ≈5.5 h is a session span (2026-10-14, 16:53-22:21, retries included), not a clean
#   benchmark; levels 1-4 are measured (see REPRODUCE.md section 3)
python run_all.py --level 4 --dry-run     # print the commands without running them
```

### Run the diagnostic on your own dataset

You do not need this repository's data for the diagnostic — it takes a CSV.
The two questions it answers are *"does a chemical composition occur in only one
group?"* and *"how much of the group label survives conditioning on chemistry?"*:

```bash
python scripts/confound_diagnostic.py --csv your_data.csv \
    --group-col topology \
    --coarse-cols metal_linker,linker1,linker2 \
    --fine-cols   metal_linker,linker1,linker2,functional_groups \
    --pair-report --top-n-groups 15
```

It prints both granularities, the group-pair Jaccard table and a plain-language
verdict, and writes `confound_diagnostic.csv` and `confound_diagnostic_pairs.csv`.
The `hmof` preset (`--preset hmof`) reproduces this paper's numbers. What to do
with the answer — and the reporting rules that follow from it — is in
`REPORTING_CHECKLIST.md`.

Levels 1 and 4 have been timed end-to-end for the pipeline as it stood when they
were run (7.3 and 29.9 minutes). Both **predate** changes to their own step lists,
so read them as approximations rather than as measurements of the scripts shipped
today: level 1 was timed without `full_db_confound.py` (later timed separately at
14 s), and level 4 without `arcmof_overlap.py` and `sample_size_granularity.py`
(12 s and 39 s), while still containing the since-withdrawn `granularity_control.py`.
What each run actually covered is listed in `REPRODUCE.md` §3; levels 2 and 3 are now
measured, and level 5 has also been run end to end (2026-10-14) with its ≈5.5 h session
span quoted as a span rather than a benchmark. All seeds are fixed (42 by default).

**What has actually been verified, not merely intended:** on 2026-10-10, level 4
(in the 6-step form described above) was re-run from scratch and produced 8/8
outputs byte-identical to the previous run; level 1 likewise reproduced
`chem_topo_confound.csv` and `chem_topo_jaccard.csv` byte-for-byte; and the three
steps absent from those two runs were re-run afterwards into a scratch directory,
giving **5/5 outputs byte-identical**, among them `confound_full.csv`, which is the
file the headline 93.2% comes from. Details in `REPRODUCE.md`, section 3.

---

## Five things a reader should know before re-running anything

1. **Report four aggregation rules, always.** `pooled` is dominated by the
   largest group; with pcu holding 63% of hMOF, pooled = +0.381 while
   macro = −0.541. Choose the headline by the intended deployment population
   (macro/median for per-group performance, pooled for whole-database deployment)
   and publish all four.
2. **Check target variance before comparing R² across splits.** Our own withdrawn
   CGCNN comparison is the cautionary example (R² = −0.448 while MAE was actually
   better). Because R² is not robust here, §3.11 also reports hit rate and regret.
3. **Declare the granularity of "chemistry" and the sample size.** The same
   database gives 98.9% at n = 25,000 and 93.2% at n = 324,426. Random-compression
   alignment is not a fix — it is the pitfall.
4. **Changing the support set changes the denominator.** All four splitting
   strategies in §3.11 are scored on out-of-fold predictions for the *same*
   25,000 samples against one oracle.
5. **Never `head()` the CSVs.** Both hMOF files are sorted by topology; use
   `df.sample(..., random_state=42)`, which every script does.

---

## Known limitations (also stated in the manuscript)

- The controlled contrast rests on a **single** isoreticular pair (pcu ↔ nbo) and
  does not generalise to all 11 hMOF topologies.
- One set of structure-derived scalar descriptors is used. The deep-learning arm was
  withdrawn (§3.7); the random-versus-topology gap is not specific to the model
  family — gradient boosting and ridge were refit as single untuned fits (gaps
  0.3742 and 0.180 against the forest's 0.3743; normalised by each family's own
  random-split R²: 51.1% and 40.9% against 49.7%, so the normalisation does not
  bring the families together and no equivalence is claimed) — and the gap is
  **target-dependent** (log-selectivity 0.8357 → 0.7211 against uptake
  0.7529 → 0.3786), so no single magnitude should be quoted without its target.
- The cross-database replication uses ARC-MOF **metadata only** (chemical clusters
  plus topology); no adsorption property enters §3.15.
- **ARC-MOF is not independent of hMOF.** We say so explicitly and bound it by
  leave-one-source-out rather than claiming independence.
- The 2×2 design uses 25,000 samples, one model and one feature set, so
  "indistinguishable from zero" means *not detected here*, not *proven zero*.
- The official `DB<n>` → database mapping is unavailable, so we make **no** claim
  about which ARC-MOF source is experimental and compute no "experimental
  fraction" variable.

---

## Citation

Please cite the two datasets given in `DATA.md`. A preprint DOI will appear here
on submission.

## Licence

Code: MIT (see `LICENSE`). Data: bound by the licences stated on the Materials
Cloud and Zenodo record pages; the MIT licence does not extend to the datasets.
