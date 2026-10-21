# Figure manifest — v6 compressed package

This file is an index only: it maps figure numbers to final filenames. The authoritative
record of input data, plotting command and verification scope for every figure is the
"Figure pipeline" table in `REPRODUCE.md`; do not duplicate it here.

All final files live in `../01_manuscript/figures/`.

| Figure | Final file | REPRODUCE entry |
|---|---|---|
| 1 | `Fig1_support_structure.png` / `.pdf` | `F1` |
| 2 | `Fig2_intervention.png` / `.pdf` | `F2` |
| 3 | `Fig3_screening.png` / `.pdf` | `F3` |
| 4 | `Fig4_arcmof.png` / `.pdf` | `F4` |
| S1 | `figS1_shap_family.png` / `.pdf` / `.svg` / `.tiff` | `FS1` |
| S2 | `figS2_pdp_geometry.png` / `.pdf` / `.svg` / `.tiff` | `FS2` |
| S3 | `figS3_within_vs_cross.png` / `.pdf` | `FS3` |
| S4 | `figS4_aggregation_stability.png` / `.pdf` | `FS4` |
| S5 | `figS5_aggregation_rules.png` / `.pdf` / `.svg` / `.tiff` | `FS5` |
| S6 | `figS6_source_confound.png` / `.pdf` / `.svg` / `.tiff` | `FS6` |
| S7 | `figS7_sg_curve.png` / `.pdf` | `FS7` |

`TOC_graphic.png` (975 × 525 px, 300 dpi) is the journal table-of-contents graphic: a
purpose-built two-block schematic — "support removed" (74.7%, hMOF) and "cost at screening"
(top-1% recovery 50.4% → 19.3%) — whose numbers are read from `outputs/confound_full.csv`
and `outputs/screening_utility_seed*.csv` at build time and asserted against the manuscript
(`REPRODUCE.md`, entry `TOC`). It is not a numbered figure, is not referenced by the main
text, and deliberately uses a rule rather than an arrow between the blocks, because the
ranking loss is not shown to be caused by the support loss.

The previous 8-figure main-text set (`fig1_*` … `fig8_*`) is superseded and removed.
