# What topology hold-out removes—and what it does not

This repository contains the corrected submission code published on 2026-10-25 at commit 80bd0bc1046cedd3f8eb7069c1bc1acc8b0a5dc7 and the v1.5 submission revision. The existing v1.4 tag and deposit (fixed DOI **10.5281/zenodo.23618746**) remain unchanged. The corrected code is publicly accessible at https://github.com/wang359826/topology-holdout-support-audit/tree/80bd0bc1046cedd3f8eb7069c1bc1acc8b0a5dc7. The concept DOI 10.5281/zenodo.23415179 links the deposited version series; no unverified new deposit is asserted.

## Current entry points

The current manuscript, SI and figures are under `manuscript_v6/`. In the source workspace the authoritative sibling package is `03_投稿专用包_v6压缩/`; selected deliverable files are synchronized here before packaging.

| Location | Purpose |
|---|---|
| `manuscript_v6/01_manuscript/Manuscript_v6.pdf` | Current manuscript, four main figures |
| `manuscript_v6/02_supplementary/SI_v6.pdf` | SI, eight figures, Tables S1–S25 and S25b |
| `manuscript_v6/03_reproduction_package/REPRODUCE.md` | Current claim-to-source mapping and three verification levels |
| `scripts/confound_diagnostic.py` | Portable support diagnostic; also in the v6 supplement |
| `scripts/test_confound_diagnostic.py` | Portable-tool regression tests |
| `REPORTING_CHECKLIST.md` | 22 reporting rules |
| `DATA.md` | Source records, retrieval and checksums |
| `REPRODUCE.md` | Historical v5 five-level analysis pipeline |
| `requirements.txt` | Dependencies |
| `LICENSE` | MIT for code; source-data rights remain with owners |

## Scientific scope

In hMOF, 74.7% of coarse composition keys occur in one topology and account for 61.3% of structures. Seven of eleven groups lose all same-key counterparts but contain only 21.3% of structures. These are support counts, not a causal attribution of error. The 21.1% comparison of chemistry-key and topology-grouped R² decreases is a descriptive protocol ratio.

The pcu–nbo intervention is limited to one usable matched pair, one library and the tested uptake target. The nbo partner-removal MAE difference is +0.0746 mmol/g (paired 95% t interval +0.0591 to +0.0900). Screening is retrospective out-of-fold recovery, not prospective single-model discovery. ARC-MOF is a partly dependent second-key audit. See the manuscript for target and representation sensitivity.

## Portable diagnostic

```bash
python scripts/confound_diagnostic.py --csv DATA.csv --group-col topology --coarse-cols metal_linker,organic_linker1,organic_linker2 --pair-report
python scripts/test_confound_diagnostic.py
```

Use columns present in your CSV; `--fine-cols` supplies a second chemistry definition and `--preset hmof` supplies hMOF columns. The default evaluates **all groups** and computes overlap counts even without `--pair-report`; that flag also exports detailed pairs. Explicit `--top-n-groups` limits pair coverage and labels it partial.

Outputs are `confound_diagnostic.csv`, `confound_diagnostic_groups.csv`, and optionally `confound_diagnostic_pairs.csv`. They report composition/structure-weighted unseen rates, per-group support, both entropy directions, plugin and Miller–Madow estimates separately, and overlap at each granularity. Missing group labels and wholly missing chemistry keys are excluded and counted; partial missing tuples are retained and counted. Literal `NA` text is retained. Tuple keys avoid delimiter collisions. Undefined ratios remain undefined; the tool issues no independence, causality or performance verdict.

## Verification coverage

In `manuscript_v6/03_reproduction_package/`, Level 1 checks covered archived numbers and consistency, Level 2 recomputes 50 intervention MAE values and 30 screening overlaps from archived predictions, and Level 3 rebuilds one seed-42, 25,000-row random-split RF G/B/I comparison from raw hMOF. Only Level 3 trains, and it is not a full-paper retrain.

The root `scripts/run_all.py --level 1..5` is the historical training pipeline, distinct from the three v6 verification levels. Later source snapshots are not all standalone portable rerun entry points. See the per-result mapping for exact coverage.

This revision corrects the diagnostic, input validation, S25/S25b checks, manuscript wording and figure/PDF presentation, including the missing 415-feature overlay in Figure 2. Scientific source outputs are retained. Original databases are not redistributed. Any public release must use a new version; do not move published v1.4.
