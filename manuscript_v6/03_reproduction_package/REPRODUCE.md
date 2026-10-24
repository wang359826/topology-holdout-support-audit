# Reproduction mapping — v6 compressed package

This package ships the compressed manuscript (`../01_manuscript/Manuscript_v6.md`) and
Supporting Information (`../02_supplementary/SI_v6.md`). The authoritative mapping from
every claim, table and figure to its input and producer is below. Rebuilding the figures
from archived outputs does not train a model. Table S7 also has a standalone raw-data
generator that uses training-target means only; its seed-level outputs are archived.

## Release status

Published v1.4 has fixed DOI **10.5281/zenodo.23618746**. This local submission revision adds corrections and is **not yet archived as a new public version**. Those changes cannot be attributed retroactively to the fixed deposit. The concept DOI identifies the latest public version, not this working tree.

## Three reproduction levels (2026-10-24)

The package is organised as three levels, each with an executable entry point and an explicit
statement of what it does **not** cover. `config/config.json` records the input records,
checksums and the environment used.

| Level | Entry point | What it does | What it does not do |
|---|---|---|---|
| 1 — numeric | `level1_verify/run_level1.ps1` (or `.sh`) | Verifies explicitly covered table cells and headline values, numbering, cross-references, citations and figure-file existence from outputs/; verifies archive checksums; does not rebuild figures or inspect PDF layout | No model is fitted; no raw data are read |
| 2 — predictions | `level2_predictions/verify_predictions.py` | Recomputes arm MAE and screening top-k overlap from the archived row-level predictions (`predictions_arms_seed*.csv`, `predictions_screening_seed*.csv`) and compares them with the archived summaries | No model; the experiment-12 `.npz` predictions and the fixed-pool full score vectors are not in this slim archive |
| 3 — rerun | `level3_rerun/run_subset.py --csv PATH` | Rebuilds the seed-42, 25,000-row, random-split RF G/B/I comparison from the public hMOF CSV and compares it with the archive | One representative subset; not a full-paper retrain |

Verification status of each level in this revision:

| Level | Status | Evidence |
|---|---|---|
| 1 | PASS | `scripts/check_v6_consistency.py` (assertion count printed by the checker; PDF freshness is a separate check), `scripts/verify_followup_tables.py`, `scripts/singleton_audit.py verify`, `scripts/make_md5sums.py --check` |
| 2 | PASS | 50 arm MAE comparisons and 30 screening-overlap comparisons recomputed from predictions, all within 1e-6 (`level2_predictions/level2_report/summary.json`) |
| 3 | PASS | G/B/I rebuilt from the 324,426-row CSV in 81.0 s during the 2026-10-24 recheck; MAE and R² match the archive to < 1e-15 (`level3_rerun/rerun_out/summary.json`) |

**Do not describe levels 1–2 as "reproducing the paper"**: they verify archived numbers and
archived predictions. Only level 3 fits a model, and only on one subset.

### Where each result lives

| Provenance | Directory | In published v1.4? |
|---|---|---|
| Original analyses (support audit, protocols, arms, ARC-MOF, screening) | `outputs/` | Yes |
| Six follow-ups (representation, novelty, CoRE, diagnostics, replacement, fixed pool) | `outputs/followup_20261023/` | Yes — added in v1.4 |
| Finish analyses (tie audit, candidate bootstrap, per-topology representation deltas) | `outputs/finish_20261023/` | Yes |
| `max_features=1.0` representation sensitivity | `outputs/sensitivity_mf1/` (produced by `scripts/analyze_mf_sensitivity.py` from the experiment-12 sensitivity runs) | Yes |
| Paired-seed tests quoted in 3.3/3.4 (screening gap, nbo percentage interval) | `outputs/paired_tests_20261024.csv` (produced by `scripts/screening_paired_tests.py`) | Yes |

### Fixed-pool and representation limits of this archive

The slim archive stores the summary metrics for these experiments, not the full prediction
vectors. Consequently:

* Table S24 (fixed candidate pool) is verifiable at level 1 (arithmetic on archived metrics)
  but not at level 2;
* Table S19/S20 and the per-topology deltas are verifiable at level 1; the `.npz` predictions
  stay in the experiment-12 working directory and are listed in
  `outputs/followup_20261023/archive_provenance.json`.


## Dependency on the source package

Most analysis scripts, `DATA.md`, dependency pins and `run_all.py` are **not duplicated**
here; in the combined public release they live at the **root of this archive**, beside the
`manuscript_v6/` subtree that holds this package (in the pre-release working tree they
are the sibling package `03_投稿专用包/03_reproduction_package/`, v5). This
v6 package contains archived outputs and local verification/build helpers, including
`scripts/build_main_v6.py` (figures), `scripts/build_toc_v6.py` (TOC graphic),
`scripts/build_pdf_v6.py` (submission PDF), the four
`pubfig` helpers, the standalone `scripts/training_mean_baseline.py` generator,
`scripts/loto_full_metrics.py` (per-fold LOTO metrics for Table S8 and the five-seed
`weighted` for Table S9), `scripts/loto_cleaned_sensitivity.py` (the cleaned 100k LOTO
sensitivity in SI-A.4), `scripts/loto_cleaned_25k.py` (the cleaned 25k five-seed LOTO
sensitivity in SI-A.4), `scripts/singleton_audit.py` (the singleton / entropy / Miller–Madow
audit behind Table 3, §3.1, §3.5 and SI-B.2), `scripts/input_validity_audit.py` (the eight-field
validity counts), `scripts/sensitivity_invalid_rows.py` (the paired invalid-row
performance sensitivity), `scripts/summarize_sensitivity.py` (the five-seed summary in
SI-A.4), `scripts/partner_random_g.py` (the post hoc random-partner control in SI-C.4),
`scripts/component_breakdown.py` (the metal / linker / conjunction
support breakdown in SI-B.1), `scripts/arcmof_cluster_span.py` (the cluster-ID span check in
SI-H.1), `scripts/check_v6_consistency.py` (pre-submission
invariant check, below) and `scripts/make_md5sums.py` (archive manifest). The root `run_all.py` covers the historical pipeline, not every later follow-up. Consult the per-result mapping and source-snapshot requirements for additional raw-data reruns.

Path convention for the commands below: `../../scripts` and `../../data/` refer to the
archive root under the **merged archive layout used by v1.3/v1.4** (this package at
`manuscript_v6/03_reproduction_package/`). In the pre-release working tree — the two
packages as siblings under `MOF_topholdout_投稿包_v5修订/` — the same paths are
`../../03_投稿专用包/03_reproduction_package/{scripts,data}`. The `data/` tree is
**not shipped** in the archive: fetch it with the commands in the root `DATA.md`
(verify the MD5s), or point `--csv` at your own copy.

## Pre-submission checks

Two commands must pass before submission, and both are read-only:

```text
python scripts/check_v6_consistency.py     # numbering, citations, figure map, PDF freshness,
                                           # and every table/inline number re-derived from outputs/
python scripts/make_md5sums.py --check     # outputs/MD5SUMS.txt covers the archive exactly
```

What `check_v6_consistency.py` checks, stated narrowly so it is not over-read: it
re-derives (i) every cell of Tables 1–3, (ii) every cell of SI Tables S1–S9, S12, S15–S25b,
(iii) a named list of headline claims (74.7%, 61.3%, 82.0%, 18.0%, 0.860, 69,224, 21.3%,
408, 21.1%, 21.5%, 0.3603, −0.0065, +70.0%, −1.2%, the (e)/(f) arm means, 50.4%, 19.3%,
31.1 pp, the two paired intervals and their t/p values, 46.3%, 99.3/97.3/99.7/98.2,
98.57/98.96, 3,554, 0.4629, the model-family gaps), (v) the six-follow-up enumeration in the
abstract, Methods 2.7, conclusion and cover letter, and (vi) numbering, cross-reference and
figure-file existence. It does **not** validate
that a number is attached to the right claim in every sentence: the headline checks search
the text for the expected value, so a value repeated elsewhere can satisfy a check whose
own sentence is wrong. It is not a scientific-interpretation review. SI Tables S10, S11,
S13, S14 and all prose not in the named list are outside its coverage and are listed as
not automatically verified in the pre-submission note. It exists because a review found a
stale table cell (Table 1 quoted 0.6720 where the archive holds 0.6674) that no other
check would have caught. `--no-pdf` skips the PDF-freshness test when the PDFs have
deliberately not been rebuilt yet; that test compares modification times and file size
only, so passing it is not a visual or layout acceptance of the PDFs.

## Mapping (main text → source)

| Claim / table / figure | Source CSV | Producer (source package unless marked v6-local) |
|---|---|---|
| 74.7% / 61.3% / 7-of-11 / per-topology unseen | `outputs/confound_full.csv`, `outputs/chemistry_seen_by_topology.csv` | `full_db_confound.py`, `chemistry_seen.py` |
| Component breakdown (metal / linker pair / conjunction) | `outputs/component_breakdown.csv` | `scripts/component_breakdown.py` (v6-local; raw hMOF CSV) |
| ARC cluster-ID span (non-circularity check) | `outputs/arcmof_cluster_span.csv` | `scripts/arcmof_cluster_span.py` (v6-local; `data/arcmof/arcmof_confound.csv`) |
| H(T\|C)/H(T) = 18.0% (0.860 reverse) | `outputs/confound_full.csv` | `full_db_confound.py` |
| Table 1 Panel A (five splits, 426/415) | `outputs/leakage_results_final.csv`, `_chemistry.csv`, `_notopo100k.csv` | `mof_leakage_benchmark.py` |
| Table 1 Panel B (LOTO four aggregates) | pooled/weighted/macro/median: `outputs/metrics_audit.csv` (`pooled_as_reported`); per-fold R²: `outputs/loto_per_topology_final.csv` | `metrics_audit.py` derives the aggregates from the LOTO output; per-fold R² from `mof_leakage_benchmark.py --loto` |
| excl-pcu pooled +0.4629 (audit) | `outputs/metrics_audit.csv` | `metrics_audit.py` (derived audit of the LOTO output) |
| Table 2 (intervention arms a–f) | `outputs/isoreticular_control_seeds.csv`, `outputs/composition_matched_control.csv`, `outputs/arm_e_partner_coverage.csv` | `diversity_control.py`, `confound_diagnosis.py`, `partner_coverage_arm_e.py` |
| Table S6 (full per-seed MAE, arms a/b/c/e/f) | a/b: `outputs/isoreticular_control_seeds.csv`; c: `outputs/composition_matched_control.csv` (mean of the five `size_matched_seed*` draws per outer seed); e/f: `outputs/arm_e_partner_coverage.csv` | a/b: `confound_diagnosis.py --seeds 5 --control-topos pcu,nbo`; c: `diversity_control.py` (nested 5×5 size-matched draws); e/f: `partner_coverage_arm_e.py` |
| Table S7 (training-mean baseline) | outputs/baseline/training_mean_baseline_seeds.csv; training_mean_baseline_summary.csv; audit JSON and SHA256 manifest | v6-local scripts/training_mean_baseline.py recompute --csv PATH; full command and verification scope below |
| 34.9% / 65.1% split, pcu reversal | `outputs/arm_e_partner_coverage.csv` | `partner_coverage_arm_e.py` |
| Random-partner control (post hoc arm g) | `outputs/partner_random_g.csv`; a/e from `outputs/arm_e_partner_coverage.csv` | `scripts/partner_random_g.py` (v6-local; five seeds) |
| Table 3 (ARC-MOF) | `outputs/confound_arcmof.csv` (marginals), `outputs/singleton_audit.csv` (single-topology values, non-singleton subsets, singleton counts, Miller–Madow corrections) | `arcmof_confound.py`; `scripts/singleton_audit.py recompute` (v6-local) |
| Both entropy-ratio directions (0.180 / 0.860) and §3.1 singleton counts | `outputs/singleton_audit.csv`, `outputs/confound_full.csv` | `scripts/singleton_audit.py recompute` (v6-local), `full_db_confound.py` |
| Source-removal 98.57–99.84% | `outputs/confound_arcmof_excl_derived.csv`, `outputs/arcmof_overlap.csv` | `arcmof_overlap.py` |
| Within-source null (+2.6…+37.3 pp) | `outputs/common_support/null_topology_cardinality.csv` | `null_model_controls.py` |
| Between-source spread (3,554× fine, ~2,000× coarse) | `outputs/source_spread_test.csv`, `outputs/source_confound_granularity.csv` | `source_spread_test.py` |
| Screening (50.4% → 19.3%, k=1/5/10%; paired gap interval) | `outputs/screening_utility_seed{42,143,244,345,446}.csv`, `outputs/screening_utility.csv`; paired test in `outputs/paired_tests_20261024.csv` | `screening_utility.py`; `scripts/screening_paired_tests.py` |
| Five-seed cleaning sensitivity summary | `outputs/sensitivity_five_seeds_summary.csv` | `scripts/summarize_sensitivity.py` (reads the five `sensitivity_{screening,arms}_seed*.csv`) |
| Elite subset null (21.4% row-level) | `outputs/null_elite_permutation_row.csv` | `null_model_controls.py` |
| Ten-target panel | `outputs/multitarget_confound.csv` | `multitarget_confound.py`, `derive_multitarget_stats.py` |
| Omitted-variable η² (topology/metal/linker pair) | `outputs/omitted_variable_final.csv`, `outputs/cardinality_correction.csv` | `omitted_variable.py`, `cardinality_correction.py` |
| Mitigation comparison | `outputs/mitigation_results_mit25k.csv` | `mof_leakage_benchmark.py` |
| Within/cross-topology R² | `outputs/within_vs_cross_final.csv` | `omitted_variable.py --within-vs-cross` |
| Distance-bin diagnostic (SI Table S12) | `outputs/fig7_nn_curve_final.csv` (`bin`, `bin_mid`, `scheme`, `n`, `R2`) | `leakage_mechanism.py` |
| Input-validity audit (SI-A, SI-E) | `outputs/input_validity_audit.csv` | `scripts/input_validity_audit.py` (v6-local) |
| ARC-MOF non-singleton counts (Figure S8a, Table 3, SI-H) | `outputs/arcmof_non_singleton_summary.csv` | `scripts/singleton_audit.py recompute` (v6-local) |
| Table S9 (25k multi-seed LOTO, 100 trees) | `outputs/loto_aggregates_25k.csv` (all four rules incl. weighted), `outputs/multi_seed_uptake25k_fix.csv` (archived pooled/macro/median) | `scripts/loto_full_metrics.py recompute25k` |
| Table S8 (100k LOTO, per-fold metrics) | `outputs/loto_per_topology_metrics_100k.csv` (MAE, RMSE, R², SSE, SST, valid flag), `outputs/loto_aggregates_100k.csv` (four rules) | `scripts/loto_full_metrics.py recompute` |
| LOTO cleaned sensitivity (100k) | `outputs/loto_cleaned_per_topology_100k.csv`, `outputs/loto_cleaned_aggregates_100k.csv` | `scripts/loto_cleaned_sensitivity.py` (v6-local; paired historical-all gate + cleaned-legal) |
| LOTO cleaned sensitivity (25k, five seeds) | `outputs/loto_cleaned_per_topology_25k.csv`, `outputs/loto_cleaned_aggregates_25k.csv` | `scripts/loto_cleaned_25k.py` (v6-local; gate against Table S9) |
| Figure S2 (PDP) | `outputs/pdp_geometry_curves.csv`, `pdp_geometry_meta.csv` (offset 0.519784 = `baseline_mean_of_tree_means`, with python/numpy/pandas/sklearn versions, input MD5 and the script SHA256), `pdp_geometry_grids.csv` (valid grid range and per-field invalid counts) | `prepare_figS2_pdp_data.py --outdir <v6>/outputs` (data; image built by the v6-local `scripts/pubfig/build_si_S1_S7.py S2`) |

## Feature-subsampling sensitivity (SI-I.7 / Table S25)

Prespecified `max_features=1.0` re-run of the two representation contrasts, with every other
setting fixed and the archived `split.npz` reused row for row.

| Item | Archive | Producer |
|---|---|---|
| Mapped I/T, 520 fits (2 reps × 2 learners × 2 targets × 5 seeds × 13 folds) | `outputs/sensitivity_mf1/mapped/{mf1_pooled,mf1_paired,mf1_per_topology}.csv` | `scripts/run_mf_setting.py` (driven by `scripts/run_matrix.py`), analysed by `scripts/analyze_mf_sensitivity.py` |
| Full-sample B/I, 220 fits (RF only; 2 reps × 2 targets × 5 seeds × 11 LOTO folds) | `outputs/sensitivity_mf1/full/{mf1_pooled,mf1_paired,mf1_per_topology}.csv` | same |
| Per-topology MAE under both settings | `outputs/sensitivity_mf1/mapped/per_topology_setting_metrics.csv` | analysis helper in the sensitivity run (see SI-I.7 note) |
| Frozen settings | `outputs/sensitivity_mf1/{mapped,full}/frozen_config.json` | written before any fit; asserts scope/reps/models/max_features |

Level-2 note: these rows are recomputed by `analyze_mf_sensitivity.py` from the experiment-12
`.npz` predictions (not shipped in this slim archive), so the archived CSVs are level-1
evidence; the script is included so a reader holding the experiment directories can redo the
arithmetic.

## Former gaps, now closed

The two SI tables that previously carried only part of their intended metrics are now
complete. The filling step trains random forests, so it is the one reproduction step that
fits models; it does not use new data.

- **Table S8** (100,000-sample LOTO): per-fold MAE, RMSE, R², SSE and SST are now archived in
  `outputs/loto_per_topology_metrics_100k.csv`, together with the four aggregates in
  `outputs/loto_aggregates_100k.csv`. The earlier archive held only per-fold R².
- **Table S9** (25,000-sample five-seed LOTO): `weighted` is now archived for all five seeds
  in `outputs/loto_aggregates_25k.csv`, with the number of covered rows per seed.

Reproduction command (from `03_reproduction_package/`; `--n-jobs -1` uses all cores, use
`--n-jobs 1` in a sandbox that denies named pipes):

```text
python scripts/loto_full_metrics.py recompute    --csv PATH_TO_HMOF --outdir outputs
python scripts/loto_full_metrics.py recompute25k --csv PATH_TO_HMOF --outdir outputs
python scripts/loto_full_metrics.py verify       --outdir outputs
```

`verify` is read-only. Its scope is stated narrowly so it is not over-read: the verifier
reconstructs **weighted, macro and median R², valid-fold counts and covered sample counts**
from the per-fold tables. **Pooled R² is compared with the historical archive**; it is not
recomputed from per-sample predictions, and per-fold MAE is not recomputed from predictions
either. Within that scope it checks key uniqueness and fold sizes, `RMSE² × n_test == SSE`,
`R2 == 1 − SSE/SST` on valid folds, `MAE ≤ RMSE`, non-negative error metrics and sums of
squares, that the `valid_R2` flag matches its own definition (`n_test ≥ 2` and `SST > 0`), and
that every upstream flag is preserved rather than overwritten by a later check. It then
compares the 100k per-fold R² and `n_test` with `loto_per_topology_final.csv`, the four 100k
aggregates with `metrics_audit.csv`, and the five-seed pooled/macro/median/valid-fold counts
with `multi_seed_uptake25k_fix.csv`.

The corrected verifier passed on the archived data and rejected deliberately corrupted copies
(a 100k MAE or R² set to 999, a 25k `weighted` set to 999, a valid fold flagged invalid, a
negative MAE). That both-directions test is shipped as `scripts/verify_regression.py` and can
be re-run; it works on scratch copies and never modifies the archive. Outputs are archived in
`outputs/logs/loto_verify_20261020.log` and
`outputs/logs/loto_verify_regression_20261020.log`.

Evidence scope: the author reports completing the 100k and five-seed 25k LOTO runs on
2026-10-20. The resulting per-fold and aggregate CSVs are archived; the successful training
console output was not retained. The archived failed and interrupted attempts are not
evidence of successful completion. The read-only verifier checks internal arithmetic
consistency and agreement with historical results. It does not independently establish the
provenance of the training outputs.

Definitions used, stated so they can be checked: MAE = mean(|y − ŷ|); RMSE =
sqrt(mean((y − ŷ)²)); per-fold R² is valid only when n_test ≥ 2 and SST > 0; `pooled` is R²
over all predictions against the global mean; `weighted` = Σ(nᵢR²ᵢ)/Σnᵢ over valid folds;
`macro` = mean of valid-fold R²; `median` = median of valid-fold R².

## Figure pipeline

This is the single authoritative figure mapping; `FIGURE_MANIFEST.md` is an index of
number ↔ filename only. All commands run from `03_reproduction_package/`; final files go to
`../01_manuscript/figures/`.

| ID | Figure | Input data (`outputs/`) | Final plotting command | Output |
|---|---|---|---|---|
| F1 | Fig. 1 | `chemistry_seen_by_topology.csv`, `topology_pair_overlap.csv` | `scripts/build_main_v6.py` (`figure1`) | `Fig1_support_structure.png/.pdf` |
| F2 | Fig. 2 | panel (a): `leakage_results_final.csv`, `leakage_results_chemistry.csv`, `leakage_results_notopo100k.csv`; panel (b): `loto_aggregates_100k.csv`, `loto_per_topology_metrics_100k.csv`; panels (c)/(d): `finish_20261023/per_topology_paired_deltas.csv` | `scripts/build_main_v6.py` (`figure2`) | `Fig2_protocol_support.png/.pdf` |
| F3 | Fig. 3 | panels (a)/(b): `isoreticular_control_seeds.csv`, `composition_matched_control.csv`, `arm_e_partner_coverage.csv`; panel (c): `followup_20261023/experiment5/paired_endpoints.csv`, `cleaned_endpoint_summary.csv` | `scripts/build_main_v6.py` (`figure3`) | `Fig3_intervention.png/.pdf` |
| F4 | Fig. 4 | panels (a)/(b): `screening_utility_seed{42,143,244,345,446}.csv`; panel (c): `followup_20261023/experiment6/screening_summary.csv` | `scripts/build_main_v6.py` (`figure4`) | `Fig4_screening.png/.pdf` |
| FS8 | Fig. S8 | panel (a): `singleton_audit.csv` + `arcmof_non_singleton_summary.csv` (read at plot time, no hard-coded values); panels (b)/(c): `confound_arcmof_excl_derived.csv`, `common_support/null_topology_cardinality.csv` | `scripts/build_main_v6.py` (`figureS8`) | `figS8_arcmof.png/.pdf` |
| FS1 | Fig. S1 | `fig5_shap_family_final.csv` | v6-local `scripts/pubfig/build_si_S1_S7.py S1` | `figS1_shap_family.png/.pdf/.svg/.tiff` |
| FS2 | Fig. S2 | `pdp_geometry_curves.csv`, `pdp_geometry_meta.csv`, `pdp_geometry_grids.csv` | v6-local `scripts/pubfig/build_si_S1_S7.py S2`, after `prepare_figS2_pdp_data.py --outdir <v6>/outputs` | `figS2_pdp_geometry.png/.pdf/.svg/.tiff` |
| FS3 | Fig. S3 | `within_vs_cross_final.csv` | `scripts/build_main_v6.py` (`figureS3`) | `figS3_within_vs_cross.png/.pdf` |
| FS4 | Fig. S4 | `multi_seed_uptake25k_fix.csv` | `scripts/build_main_v6.py` (`figureS4`) | `figS4_aggregation_stability.png/.pdf` |
| FS5 | Fig. S5 | `metrics_audit.csv`, `loto_per_topology_final.csv` | v6-local `scripts/pubfig/build_si_S1_S7.py S5` | `figS5_aggregation_rules.png/.pdf/.svg/.tiff` |
| FS6 | Fig. S6 | `source_confound_granularity.csv`, `common_support/null_topology_cardinality.csv` | v6-local `scripts/pubfig/build_si_S1_S7.py S6` | `figS6_source_confound.png/.pdf/.svg/.tiff` |
| FS7 | Fig. S7 | `s_g_curve.csv` | `scripts/build_main_v6.py` (`figureS7`) | `figS7_sg_curve.png/.pdf` |
| TOC | TOC graphic | `confound_full.csv` (74.7%), `screening_utility_seed{42,143,244,345,446}.csv` (50.4% / 19.3%); the script asserts both values before drawing | `scripts/build_toc_v6.py` | `TOC_graphic.png` (975 × 525 px, 300 dpi) |

**Distance-bin definition (SI Table S12; this is the neighbour diagnostic, not Figure S7,
which is the S_g curve).** The bins are not
chosen in `refuted_explanations.py`. `leakage_mechanism.py` pools the nearest-neighbour
distances of the two schemes, cuts them at 12 quantiles, sets the first and last edges to
±infinity, merges duplicate edges, and skips a scheme/bin cell with fewer than 150 rows.
`bin_mid` is the within-scheme median distance of that bin, so the two schemes have
different `bin_mid` values in the same bin; rows are keyed by `bin`, never by `bin_mid`.
The archived file retains all 12 bins for both schemes (each scheme sums to 25,000 rows),
so no cell was dropped in the run that the table reports.

Two roles that are easy to confuse:

- `prepare_figS2_pdp_data.py` (source package) **generates the PDP data**
  (`pdp_geometry_curves.csv`, `pdp_geometry_meta.csv`); it is not the image builder. The
  image builder for Figure S2 is `build_si_S1_S7.py S2`.
- The source-package `build_si_S1_S7.py` still contains legacy S3/S4/S7 producers, but they
  emit superseded annotations (S4 "artefact", S7 "pcu largest variance"). The script now
  skips them by default and warns if they are requested explicitly; final S3/S4/S7 come from
  `build_main_v6.py`.
- `pubfig/build_main_1_4.py` and `pubfig/build_main_5_8.py` are the producers of the
  **superseded** eight-figure main-text set. They are retained for provenance only: the
  current four-figure paper uses `build_main_v6.py` for the main figures, and of the pubfig
  helpers only `style.py` and `build_si_S1_S7.py` are exercised (for S1, S2, S5, S6).

Build commands (PowerShell, from `03_reproduction_package/`). The figure scripts need
matplotlib, and the S1/S2/S5/S6 builder additionally needs scipy; `build_toc_v6.py` needs
matplotlib only. Nothing here trains a model except `prepare_figS2_pdp_data.py`, which
refits the 25,000-row PDP forest (about 80 s on one core).

```powershell
python scripts/build_main_v6.py
python scripts/build_toc_v6.py

$env:PUBFIG_OUT = (Join-Path (Get-Location).Path '../01_manuscript/figures')
$env:PUBFIG_RASTER = $env:PUBFIG_OUT
python scripts/pubfig/build_si_S1_S7.py S1 S2 S5 S6
```

Both output variables must be set: the pubfig builder writes vector and raster outputs to
separate destinations, so setting only `PUBFIG_OUT` does not place the PNGs in the final
directory. Restore or clear the two variables after the build if they had prior values.
Do not disable the layout check to force a build; fix the specific overlap or font problem
and rebuild the affected figure.

The manuscript/SI Markdown is rendered to submission PDF by `scripts/build_pdf_v6.py`
(headless Edge print-to-pdf, which needs a local Edge install; this is a document-build
dependency, not an analysis dependency): `python scripts/build_pdf_v6.py` builds
`../01_manuscript/Manuscript_v6.pdf`; `python scripts/build_pdf_v6.py --si` builds
`../02_supplementary/SI_v6.pdf`.

## Singleton / entropy audit and input-validity audit

Both scripts are v6-local and read the public databases directly. The ARC-MOF input is the
assembled per-structure table of the source package; if it is absent, assemble it first:

```text
python scripts/prep_arcmof.py                 # (source package) writes data/arcmof/arcmof_confound.csv
```

Then, from this package:

```text
python scripts/singleton_audit.py recompute ^
    --hmof   PATH_TO_HMOF/all_MOFs_screening_data.csv ^
    --arcmof PATH_TO_SOURCE/data/arcmof/arcmof_confound.csv ^
    --out    outputs/singleton_audit.csv ^
    --summary-out outputs/arcmof_non_singleton_summary.csv
python scripts/singleton_audit.py verify       # 4 rows, identities, manuscript values
python scripts/singleton_audit.py selftest     # rejects 6 deliberately corrupted copies

python scripts/input_validity_audit.py --hmof PATH_TO_HMOF/all_MOFs_screening_data.csv ^
    --out outputs/input_validity_audit.csv
```

`singleton_audit.py recompute` needs numpy and pandas; `verify`, `selftest` and
`input_validity_audit.py` need numpy/pandas as well for the measurement step, while the two
acceptance commands of the audit (`verify`, `selftest`) run on the standard library alone.
The audit treats the hMOF identity fields differently from ARC-MOF on purpose: hMOF fills a
missing identity with the literal `NA` (no row is dropped), whereas ARC-MOF drops rows with
an incomplete key, because its cluster identifiers have no "unknown" level. The valid-row
counts in the summary table (256,351 coarse / 214,543 fine) are those dropna counts.

## Invalid-row performance sensitivity

`scripts/sensitivity_invalid_rows.py` is, together with the S2 PDP step, one of the two
*new* model-fitting steps in this v6 increment (the LOTO scripts `loto_full_metrics.py` and
the source package's analysis scripts also fit models). It answers the review question "do the performance endpoints move when the rows with
a negative descriptor are dropped from training?" with a paired design: the sample and the
folds are the production ones (seed 42; KFold for the random strategy, GroupKFold by
topology), the same folds are used for both variants, variant A trains on every row and
variant B on the same folds with the non-physical rows removed from the training part only,
and both are scored on the **same legal test rows**. Variant A scored on all rows is
compared with the archived seed-42 values as a fidelity gate; if the gate fails the run is
reported as not faithful rather than as a sensitivity result.

```text
python scripts/sensitivity_invalid_rows.py screening --source-scripts ../../scripts --csv ../../data/all_MOFs_screening_data.csv --seed 42 --n-jobs 4 --out outputs/sensitivity_screening_seed42.csv --predictions-out outputs/predictions_screening_seed42.csv
python scripts/sensitivity_invalid_rows.py arms --source-scripts ../../scripts --csv ../../data/all_MOFs_screening_data.csv --seed 42 --n-jobs 4 --with-arm-e --out outputs/sensitivity_arms_seed42.csv --predictions-out outputs/predictions_arms_seed42.csv
```

Outputs are written per mode and seed, so runs cannot overwrite each other:
`outputs/sensitivity_<mode>_seed<seed>.csv` (metrics),
`outputs/predictions_<mode>_seed<seed>.csv` and
`outputs/sensitivity_<mode>_seed<seed>.json` (provenance).

The provenance file separates four counts that are easy to confuse: `n_rows_sampled` (the
analysis pool: 25,000 screening / 50,000 arms), `n_unique_scored_rows` (distinct
`raw_row_index` in the predictions table — 25,000 for screening, but **39,353** for the arms,
because only the nbo and pcu test rows are scored while the rest of the 50,000-row pool is
training material), `n_prediction_records` (rows in the predictions file, which repeats the
scored rows across strategies and arms: 100,000 and 236,118 at seed 42) and
`n_metric_records` (32 and 96).
It also records the input MD5, the python/numpy/pandas/sklearn versions and the script
SHA256. That hash belongs to the **script snapshot archived at `generated_utc`**
(2026-10-20T15:34:33Z): it is **neither** the hash of the earlier fitting script (which was
not recorded) **nor** the hash of the current 2026-10-21 script
(`15a725965928147a06b2cc38fe9427b73230fdf7432e3915b4a085c9a47fb3a6`). The per-fold sizes
and counts were reconstructed afterwards from the archived `fold`/`legal` columns without
refitting.

The predictions table has one row per prediction record: `mode`, `seed`, `row_index`
(position in the sampled frame), `raw_row_index` (the row number in the source CSV),
`fold`, `n_train_fold`, `n_test_fold`, `legal`, `strategy`, `fit_population`, `y_true`,
`y_pred`. `n_train_fold` is the size of the model that predicted that row, so it already
accounts for the rows removed in the cleaned variant; it is not the mean.

The metrics table has one row per analysis x fit population x scoring rows x k, records
`seed` and `mean_n_train` — the **equal-weight mean of the per-fold training sizes** for
screening (20,000 historical / 19,988 cleaned at seed 42) and the single fit size for the
intervention arms. A row-weighted mean would differ for the topology strategy, whose folds
are very uneven, so the per-fold sizes live in the predictions table instead of being
averaged into that column. The `k_frac = -1` rows carry `r2`, `mae` and `sst` (with
`regret` blank); the k rows carry `overlap_at_k`, the oracle/selected means and `regret`.

Three read-only checks accompany a run and are part of the acceptance:

* `--gate-only --out <table>` re-runs the fidelity gate. The gate validates before it
  compares anything: required columns, the requested seed, the analysis key set, exactly one
  aggregate row and one row per k for every analysis x population x scope, finite values,
  and — for the arms table — the exact arm set declared with `--expect-arms` (default
  `a,b`, or `a,b,e` for a run with `--with-arm-e`); an unknown, extra or missing arm fails.
  A missing reference file fails unless `--allow-missing-reference` is passed, in which case
  the gate returns exit code 2 and prints UNVERIFIED instead of any "reproduces" claim.
* `recheck --seed 42` recomputes every metric field it claims to cover — overlap at each k,
  oracle and selected means, regret, R2, MAE, SST, n and k, plus `mean_n_train` — from the
  archived predictions. The expected design is *declared*, not inferred from the table under
  test: screening is random/topology x two populations, and the arms design is nbo/pcu x the
  declared arm set (`--expect-arms`, default `a,b,e`; pass `a,b` for a design without arm e).
  Prediction groups, metric groups and metric keys must match that design exactly, so a
  group deleted from both tables, a metric-only extra group, an unknown arm, a duplicate key
  and a non-finite value all fail. It also checks that the table is non-empty, carries the
  expected columns and seed, and that the two populations cover the same rows with the same
  targets, folds and legal flags. End-to-end check: on an a/b-only table,
  `recheck --expect-arms a,b` exits 0, while `recheck` with the default `a,b,e` exits 1
  because the e groups are missing — the declaration is actually consumed.
* `selftest` feeds corrupted copies through both checks (empty tables, NaN overlap, NaN
  aggregate MAE, deleted aggregate row, deleted k row, duplicated row, wrong seed, missing
  reference, missing reference with the allow flag, arms without e, reference without e
  rows, deleted prediction rows, wrong regret, wrong SST) and requires every one to be
  rejected; the pristine tables must pass.

The script uses a thread pool rather than joblib, because
loky's resource tracker cannot handle a non-ASCII workspace path or the sandbox's named-pipe
restriction; the forest fit itself releases the GIL.

## Three new archive checks (2026-10-21)

The first two read the raw source-package data and write a small CSV under `outputs/`;
the third reads the five per-seed sensitivity tables. None trains a model.

```text
python scripts/component_breakdown.py \
  --csv ../../data/all_MOFs_screening_data.csv \
  --out outputs/component_breakdown.csv

python scripts/arcmof_cluster_span.py \
  --csv ../../data/arcmof/arcmof_confound.csv \
  --out outputs/arcmof_cluster_span.csv

python scripts/summarize_sensitivity.py --outdir outputs
```

`component_breakdown.py` reproduces the metal / linker-pair / conjunction rows in SI-B.1;
its conjunction row must reproduce 74.7%, 61.3% and H(T|C)/H(T) = 0.180, which is the
built-in identity check. It groups on tuple keys and fails closed if a key field or the
topology is missing; on the released hMOF CSV the three key fields have 0 missing values
and 0 literal `NA` values, so the three rows are unchanged by the tuple-key check.
`arcmof_cluster_span.py` reproduces the cluster-ID span counts in SI-H.1.
`summarize_sensitivity.py` reproduces the five-seed summary in SI-A.4 from the five
`sensitivity_{screening,arms}_seed*.csv` tables; it fails if a seed file is missing or an
aggregate row is not unique.

## Post hoc random-partner control (arm g)

```text
python scripts/partner_random_g.py --n-jobs 1
```

This fits one new forest per seed and test side (10 fits), removes the same number of
partner rows as arm (e) but at random (not conditioned on shared composition), and carries
the archived a/e values alongside the new g values. It writes
`outputs/partner_random_g.csv`, which is the source for SI-C.4; the a/e values remain
`outputs/arm_e_partner_coverage.csv`. The seed-42 e_sub/g_non pilot was moved to
`_内部存档_非投稿/_v6清理_20261021/` and is not part of the submission package.

## LOTO cleaned sensitivity (100k and 25k five seeds)

```text
python scripts/loto_cleaned_sensitivity.py \
  --csv ../../data/all_MOFs_screening_data.csv \
  --outdir outputs --workers 4

python scripts/loto_cleaned_25k.py \
  --csv ../../data/all_MOFs_screening_data.csv \
  --outdir outputs --workers 4
```

For each held-out topology the 100k script fits the historical model on all training rows,
scores it on all test rows (gate against Table S8), then scores the same model on the legal
test rows and fits the cleaned model on the legal training rows. The 25k script does the same
for the five seeds and gates against Table S9. Both fail closed if the historical values
differ from the archived per-fold table. They write
`loto_cleaned_per_topology_{100k,25k}.csv` and `loto_cleaned_aggregates_{100k,25k}.csv`.
Single-threaded fitting is about 7–10 min per 100k fold (roughly 1–2 min per 25k fold);
`--workers` parallelizes folds, not the forest, so memory scales with the worker count.

## Archive manifest

`outputs/MD5SUMS.txt` was regenerated from the archive on 2026-10-24 with
`python scripts/make_md5sums.py`; it now covers every file under `outputs/`
(including `component_breakdown.csv`, `arcmof_cluster_span.csv`,
`sensitivity_*_seed*.csv`, `sensitivity_five_seeds_summary.csv`, `singleton_audit.csv`,
`loto_*`, `baseline_rerun/`, `followup_20261023/`, `finish_20261023/`,
`sensitivity_mf1/` and `paired_tests_20261024.csv`) and `--check` passes for 271 files.
The earlier copy had been carried over from v5 and did not describe this archive.
Table S7's own SHA256 manifest under `outputs/baseline/` is separate and unchanged.

## Verification status (four states)
- **Checked:** comparisons to archived CSVs are local checks, not a blanket claim that
  every result has been independently replicated. Table S7 was regenerated from the
  checksum-matched raw input during the AI-assisted check on 2026-10-19; the author reran
  the same commands on 2026-10-20 (logs in `outputs/baseline_rerun/`; see the Table S7
  section below for the role of each directory).
- **Historically re-run:** the dated step lists in the source package's `REPRODUCE.md`
  (levels 1–5). These do not automatically cover the new aggregations or the new figures.
- **Archive-only:** values reported from a run log with no archived output file (the
  withdrawn deep-learning arm, SI-E.2).
- **Not verified here:** a fresh end-to-end rerun of the complete analysis pipeline, and
  the live contents of the remote release (the archive's own checksums are verified, not
  Zenodo's copy). The manuscript cites the concept DOI 10.5281/zenodo.23415179, which is
  the version of record for every analysis here (v1.4: original analyses plus the six
  follow-ups, the finish analyses and the feature-subsampling sensitivity). The earlier
  v1.3 version DOI 10.5281/zenodo.23434268 covers the original analyses only. Their
  evidence and verification boundary are described below.

## Table S7: training-mean baseline (standalone, no model training)

The generator is shipped in **this v6 package**:
`scripts/training_mean_baseline.py`. It does not import the v5 analysis code or
fit a random forest. The public raw uptake CSV is an external input and is not
redistributed.

Input identity:
- hMOF full screening CSV: `all_MOFs_screening_data.csv`;
- 324,426 rows, 42 columns, 148,092,921 bytes;
- MD5: `81e9c75fcbf17368bce957ea06e7a79f`;
- source record: https://archive.materialscloud.org/records/nsp7v-2dk91
- screening archive: https://archive.materialscloud.org/records/nsp7v-2dk91/files/screening_data.tar.gz?download=1

Download and extract the screening archive separately, then supply the full CSV path.
Use an environment containing NumPy and pandas. Exact versions for the archived
execution are recorded in `outputs/baseline/training_mean_baseline_audit.json`.

Run from the reproduction-package root (replace the example path with your CSV):

```text
python scripts/training_mean_baseline.py recompute --csv "C:/path/to/all_MOFs_screening_data.csv" --outdir "outputs/baseline_rerun"
python scripts/training_mean_baseline.py verify --outdir "outputs/baseline_rerun"
```

Without the raw CSV, verify the **archived arithmetic only**:

```text
python scripts/training_mean_baseline.py verify
```

The two checks have different scopes. The first regenerates the baseline from the
original targets; the last command checks file hashes and recomputes four summaries
from the 20 archived seed-level rows. It cannot independently establish that those
rows were generated from the raw data.

Definition: for each seed 42/143/244/345/446, sample 50,000 rows using the original
pandas sampling rule, then retain nonmissing targets and eight numeric descriptors.
For each nbo/pcu test topology, arm a trains on all other topologies; arm b also
removes the partner selected by maximal overlap of coarse composition keys. Predict
the arithmetic mean of **that arm's training targets**. Divide test MAE by the test
target SD (`ddof=0`). Table S7 reports the mean and sample SD (`ddof=1`) across
the five per-seed ratios. The archive's RF `MAE_over_sd` is used only to check the
test SD; it is never used as the constant prediction or baseline MAE.

Archived outputs:
- `outputs/baseline/training_mean_baseline_seeds.csv`: 20 rows, sample sizes,
  training mean, test SD, absolute and squared-error metrics, normalized MAE,
  row-order fingerprints, and archived RF error for comparison;
- `outputs/baseline/training_mean_baseline_summary.csv`: four topology/arm summaries;
- `outputs/baseline/training_mean_baseline_audit.json`: input/script/reference hashes,
  software versions, sampling definitions, checks and execution time;
- `outputs/baseline/SHA256SUMS.txt`: hashes for these three generated files.
  This new manifest is separate from the historical `outputs/MD5SUMS.txt`.

The reference outputs in `outputs/baseline/` were generated during the AI-assisted local
check on 2026-10-19. The author reran the same archived commands on 2026-10-20; the
recomputation and verification logs are archived under `outputs/baseline_rerun/`
(`author_rerun.log`, `author_verify.log`). The seed-level and summary CSVs agree with the
reference outputs; the audit JSON differs only in its recorded execution time, so its hash
is expected to differ. Table S7 continues to cite `outputs/baseline/`. This is a
reproducibility check with the same script, not an independent implementation and not
external validation on new data.

Roles of the two directories:

- `outputs/baseline/`: the authoritative data source cited by Table S7.
- `outputs/baseline_rerun/`: the 2026-10-20 re-execution, its logs and audit record. It is
  not a second set of paper numbers and is not deleted as scratch.

Read-only acceptance check for both directories:

```text
python scripts/training_mean_baseline.py verify --outdir outputs/baseline
python scripts/training_mean_baseline.py verify --outdir outputs/baseline_rerun
```

`verify` checks archived integrity and arithmetic only; it does not re-read the raw uptake.
A raw-data recomputation uses the `recompute` subcommand with the original CSV.


## Six follow-up experiments integrated on 2026-10-23

The local archive `outputs/followup_20261023/` is the source of SI-I and Tables
S19–S24. `archive_provenance.json` records each copied source path, byte size and
SHA256. These additions are part of the v1.4 deposit (the version of record); the
earlier v1.3 release does not contain them. This step edits the manuscript and
archives evidence; it does not rerun model training.

Run the following read-only checks from this reproduction-package directory:

```text
python scripts/verify_followup_tables.py
python scripts/check_v6_consistency.py
python scripts/make_md5sums.py --check
```

The standalone follow-up check uses only the Python standard library. It recomputes
paired representation differences from pooled seed metrics, verifies their derived
summary tables, checks novelty counts against retained populations, recomputes pilot
return counts and completed-check counts, recomputes Spearman correlations with ties,
recomputes paired endpoint t intervals, and checks all 480 screening-metric records
against 96 summaries. It also compares every printed S19–S24 cell with those
calculations. This is an archived-metric arithmetic check, not independent recovery
of raw-data preprocessing, expert validation or a model refit.

Before integration, the working-directory experiment outputs were additionally
checked against saved predictions: experiment 1/2 derived summaries (648 pooled arms,
6,048 topology arms and 3,888 C3-subtype arms), experiment 5's ten prediction archives
and experiment 6's 120 score archives / 480 budget records. The large prediction
archives remain in the working experiment directories and are not redistributed
in this compact follow-up snapshot. These prior checks are distinct from the
portable acceptance command above.

`experiment12/` contains both full and common-mapped metrics, mapping evidence
and frozen configurations. The 100k stage completed all 756 expected prediction
files in the working directory: 696 nonempty and 60 expected-empty mapped folds.
It is one larger sample from the same hMOF database. The initial 25k stage uses five
sample redraws. I/B comparisons add role-specific linker identifiers; T/I comparisons
use the restricted parent-linker mapping. They do not establish causal information
effects or population-wide fingerprint superiority.

`experiment3/` contains a 40-CIF CoRE technical pilot and its pending validation
sheet (an experimental annotation file). Its source is CoRE MOF 2019 ASR v1.1.0,
DOI 10.5281/zenodo.3370144. No full-library support result or external adsorption
prediction is available. `experiment4/` contains descriptive fold diagnostics;
its 66 records reuse eleven topology groups and must not be pooled as 66 independent
validation groups. Numerical distance and linker-vocabulary definitions differ
between experiments 2 and 4 (SI-I).

`experiment5/` contains fixed-pool replacement designs, row-index mapping,
matching diagnostics and paired endpoints. Five seeds vary model randomness and
replacement order, not test sampling; only the two endpoints were refitted after
negative-descriptor cleaning. `experiment6/` contains all metric arms, frozen
candidate identities, training-membership records, vocabularies and selected IDs.
Its five seeds vary the learner only. Both are retrospective analyses conditional
on fixed pools.

The `source_scripts/` folders are original execution snapshots for traceability.
They retain original workspace-relative dependencies and are not standalone
entry points after moving this snapshot. Full retraining requires the original
hMOF data, source analysis modules, experiment directory layout and packages recorded
by those scripts. Do not execute them as if they were the portable table-verification
command. In particular, the screening producer writes its configuration and refits
models; it is not a read-only verifier. Experiments 1/2 use 120 trees with
`max_features='sqrt'`; experiments 5/6 use the default 1.0. This difference is
explicit in SI-I and precludes attributing cross-experiment absolute changes solely
to representation.

The archive MD5 manifest is regenerated after adding these files. Historical
manifest dates/counts earlier in this document refer to the preceding snapshot;
the current file count is given by `make_md5sums.py --check`.

## Paired-seed tests added 2026-10-24 (main-text 3.3 and 3.4)

`screening_paired_tests.py` recomputes, from the archived per-seed outputs, the two
paired tests now quoted in the results:

* the screening gap — random minus topology top-1% overlap, five paired seeds:
  31.12 ± 5.26 percentage points, 95% paired t interval 24.59–37.65, t(4) = 13.24,
  p = 1.9 × 10⁻⁴ (source: `outputs/screening_utility_seed*.csv`);
* the nbo-side arm (a) → (b) MAE change: +0.0746 mmol/g, 95% interval
  +0.0591 to +0.0900, t(4) = 13.41, p = 1.8 × 10⁻⁴, i.e. +70.0% with a 95%
  interval of +55.5% to +84.5% when the same bounds are divided by the fixed
  arm-(a) mean 0.1065 mmol/g (source: `outputs/isoreticular_control_seeds.csv`).

The script is standard-library only; it evaluates the t(4) tail from the closed-form
CDF, uses the same 2.776445 multiplier as `verify_followup_tables.py`, and writes
`outputs/paired_tests_20261024.csv`. `check_v6_consistency.py` reads that CSV and
asserts each quoted value against the manuscript, so the interval strings cannot
drift from the archived computation. Both intervals are on five redraws of one
database and inherit the scope statement of main-text 2.5.

The earlier manuscript quoted the nbo interval lower bound as +0.0592; recomputation
from the archived rows gives +0.059147, i.e. +0.0591 at four decimals. The value was
corrected in the manuscript, the cover letter and the claim–evidence list rather than
kept for continuity.

## Corrected portable diagnostic

`python scripts/confound_diagnostic.py --csv DATA.csv --group-col topology --coarse-cols metal_linker,organic_linker1,organic_linker2 --pair-report` produces global and per-group summaries plus detailed pairs. Pair counts use all groups unless a subset is explicitly requested and labelled. Each granularity is computed separately; plugin and Miller–Madow estimates are distinct. No causal or performance verdict is emitted. See the root README for missing-value policy. `singleton_audit.py verify` is the fixed-dataset archived-table check, not the arbitrary-CSV tool.

After building both PDFs from finalized sources, explicitly run `python scripts/verify_build_manifest.py --record`. Routine checking uses `--check`; do not refresh the record merely to silence a failure. This content-hash check supplements visual layout inspection.
