# Supplementary Information

**What topology hold-out removes — and what it does not**  
Tao Wang, College of Chemical Engineering, Nanjing Tech University, Nanjing 211816, China

> This Supporting Information accompanies the main text. Its sections are
> organised into nine thematic containers — **SI-A** (data, methods and reporting
> standard), **SI-B** (support audit and identification bounds), **SI-C** (fixed-test-set
> interventions), **SI-D** (protocol and aggregation robustness), **SI-E** (diagnostics and
> alternative analyses), **SI-F** (screening and elite subset), **SI-G** (ten targets and
> identity information) **SI-H** (ARC-MOF sources and granularity) and **SI-I** (six follow-up experiments and evidence limits). Tables are numbered
> `Table S1` … in the order they appear.

---

## SI-A. Data, methods and reporting standard

### SI-A.1 Production entry and verification boundary

The single authoritative record of inputs, producer commands and verification scope is
`REPRODUCE.md`; `FIGURE_MANIFEST.md` is only an index of figure number ↔ filename. Final
figures are drawn by `build_main_v6.py` (main figures, S3, S4, S7), by the source
package's `pubfig` builder (S1, S2, S5, S6) and, for the table-of-contents graphic, by
`build_toc_v6.py`. Historical rerun evidence applies only to the
dated step lists documented in `REPRODUCE.md`. Archived outputs and current commands should
therefore not be described as a fresh end-to-end rerun of the present package.

### SI-A.2 Data availability

The two input databases are not redistributed. hMOF (ref. 2) is retrieved from the
Materials Cloud Archive record `nsp7v-2dk91`; ARC-MOF v6 (ref. 15) from Zenodo
`10.5281/zenodo.13891643`. The source package's `DATA.md` lists the retrieval commands,
expected byte sizes and MD5 checksums, and records two upstream failure modes (intermittent
HTTP 503, and silently truncated parallel downloads). Archived analysis outputs are stored
under `outputs/`. `outputs/MD5SUMS.txt` is regenerated from that archive by
`scripts/make_md5sums.py` and covers every file in it; `--check` verifies the manifest
against the files. Table S7 has a separate SHA256 manifest under `outputs/baseline/`.
Final figure files are stored under `../01_manuscript/figures/`. The manuscript and SI
PDFs are built from their Markdown sources and the designated final figures.

The code deposit is described in main-text §9: the concept DOI
`10.5281/zenodo.23415179` resolves to the latest deposited version, which is the version of
record for every analysis in this manuscript (original pipeline plus the six follow-ups of
SI-I and the sensitivity runs); the version DOI `10.5281/zenodo.23434268` refers to v1.3,
which contains the original analyses only. Both this SI and the manuscript quote the same
two identifiers, so the reader can tell which archived bytes support which claim.

### SI-A.2b Model and experiment parameters

The working model is a random forest; tree counts, sample sizes and replication units differ
by experiment and are not a single default shared across every analysis. The default is 120
trees; the 25,000-row multi-seed LOTO aggregation and the ten-target panel use 100 trees, and
the S_g curve uses 100 to match the ten-target panel.

| Experiment | Section | Rows | Features | Trees | Split | Replication unit |
| --- | --- | ---: | --- | ---: | --- | --- |
| Protocol comparison | §3.2 | 100,000 | 426 / matched 415 | 120 | shuffled 5-fold KFold, seed 42; GroupKFold(5); separate LOTO (11 folds) | single run |
| Controlled intervention | §3.3 | 50,000 | 426 | 120 | fixed test set, training pool varied (arms a–f) | 5 outer seeds; arm (c) 5×5 nested draws |
| Screening | §3.4 | 25,000 | 426 | 120 | 5 strategies, out-of-fold on a shared support set | 5 seeds |
| Multi-seed LOTO aggregation | SI-D | 25,000 | 426 | 100 | LOTO per topology | 5 seeds |
| Ten-target panel | SI-G | 25,000 | 426 | 100 | random vs topology hold-out | single run |
| S_g curve | SI-B | 100,000 | 8 numeric + categorical one-hot (426 total) | 100 | LOTO per topology | single run |
| Singleton / entropy audit | §2.2, §3.1, §3.5, Table 3 | full database | none (counting only, no model) | — | — | single pass |
| Geometric residual model (η²) | §4.2 | 25,000 | 8 numeric descriptors | 120 | shuffled 5-fold KFold | single run |
| Single-group residual predictor (η²) | §4.2 | 25,000 | one-hot for the named grouping variable | 120 | shuffled 5-fold KFold | single run |

The random-split arms use shuffled 5-fold KFold at seed 42, the grouped arms use GroupKFold(5)
over the same rows, and the LOTO runs hold out one topology per fit. The 426 one-hot columns
are built once over the sampled rows before splitting, so every fold shares the vocabulary;
the follow-up representation study instead fits encoders within each fold. The hMOF release's
42 fields group as 28 property-and-error fields, 8 numerical structure
descriptors, 5 identity fields (metal centre, two linkers, functional group, topology) and 1
`MOFname` identifier. Models use the 8 descriptors plus the categorical one-hot blocks of
§2.3.

### SI-A.3 The 22-rule grouped-split reporting checklist

The complete checklist is reproduced here (the one-page summary table and the rules); the
long-form evidence per rule lives in `REPORTING_CHECKLIST.md` alongside the runnable
`scripts/confound_diagnostic.py`.

**Read this before applying any rule: on an enumerated library a high single-topology fraction is partly expected from the building-block recombination recipe, so the audit reports the size of the coupling, not its cause. The numbers must not be quoted as evidence about MOF chemistry, and a reporter should state whether their own library is enumerated before quoting the fraction as a finding.** This warning governs every rule below, which is why it is stated once here instead of being repeated in 22 rows.

The three principles of main-text §4.3 are the condensed
form of these 22 rules.

| # | Rule | Why it matters here |
|---|---|---|
| **A1** | State n beside every exclusivity / entropy figure | both are sample-size dependent: 98.9% at n = 25,000 vs 93.2% at n = 324,426, same data |
| **A2** | State the granularity at which "chemistry" is defined | 74.7% (metal + 2 linkers) vs 93.2% (+ functional groups) |
| **A3** | Report pooled / weighted / macro / median; choose the headline by the intended deployment population | pooled alone reads +0.381 where macro reads −0.541 |
| **A4** | Check target variance on both sides before subtracting R² across splits | a 7.7× variance gap reversed the direction of the claim |
| **A5** | State why, and whether, a ratio target is log-transformed, including zero handling | selectivity R² swings +0.42 … −0.06 without it |
| **A6** | Report the number of *valid* folds | a zero-variance fold silently turns `macro` into NaN (10–11 folds here, not 11) |
| **B1** | Disclose the three diagnostic numbers in the paper, not only in the SI | single-group fraction, conditional-entropy ratio, count of pairs sharing chemistry |
| **B2** | Describe a grouped split by its held-out groups and the covariate shifts that accompany them; reserve claims about an isolated group effect for designs that identify that effect | predicting for an unseen topology is a legitimate deployment task; it is the *isolated group effect* that needs an identifying design |
| **B3** | Report a ranking metric on a *shared support set* where a screening decision is the use case | top-1% hit rate fell 50.4% → 19.3% (five seeds) across the split, on the same 25,000-sample support set |
| **B4** | Do not use random compression as a chemical-comparability correction (it may still serve as a null model or sensitivity analysis) | compression only coarsens, so it manufactures the difference it claims to remove |
| **B5** | Report n, M and the composition frequency distribution; r = n/M alone does not make libraries comparable | two libraries can differ 100× in M at similar n; matching n matches nothing |
| **B6** | Compare groupwise metrics at a common support set, or state the coverage and distribution of each population | a different support set is a different denominator, and those cannot be subtracted |
| **B7** | Stratify the diagnostic by source sub-library | needs no cross-database comparison; range here 86.1% – 100.0% |
| **C1** | Fix the test set and change only the training set for a training-intervention effect (this does not by itself isolate jointly-changing chemistry and geometry) | supports a training-intervention reading, not an automatic isolation of the chemical factor |
| **C2** | Add a training-size-matched arm | Tests whether random thinning to the same size reproduces the contrast; it does not isolate chemistry or exclude size–distribution interactions. |
| **C3** | State how many independent contrasts you actually have | one pair is not a population |
| **C4** | Removing a topology with no shared chemical keys does not directly remove matched chemical examples, but it can still change training size, descriptor coverage, and the target distribution | it is not a chemistry intervention, and it is not a pure sample-count intervention either |
| **D1** | Do not treat an ordered top-N slice as a random sample; state the sampling rule | enumerated files are sorted by topology, so the first N rows are a handful of topologies |
| **D2** | Do not feed bootstrap replicates of one sample to a between-group test | resamples are not independent observations; the p-value is pseudo-replicated |
| **D3** | Distinguish "not detected" from "zero" | median −0.011 at p = 0.28 is not proof of absence |
| **D4** | Assert on row counts and column matches before computing | an empty frame once skipped a whole check silently |
| **D5** | Verify downloads by HTTP status *and* MD5 *and* file tail | two files were truncated while `curl` still exited 0 |

**Minimal disclosure block.** If one wants a single paragraph to paste into a methods
section:

> Grouped validation evaluates prediction for groups absent from training. When group
> identity is associated with chemical composition, this evaluation also includes
> chemical-support shift and does not isolate an effect attributable to group identity
> alone. For our data (n = N; chemistry defined as *…*), **X%** of distinct compositions
> occur in a single `<group>`, and H(G|C)/H(G) = **Y** under the stated weighting
> convention. We report these diagnostics alongside the evaluation population, valid-fold
> counts, aggregation definitions and, where screening is the intended use, ranking
> performance on a shared support set.

**What the checklist cannot tell you.** These diagnostics do not identify a causal
contribution of topology to prediction error. The nonzero conditional entropy does not by
itself establish a usable matched contrast; that requires pairwise chemical overlap and
sufficient observations. The diagnostic can be applied to experimentally derived
libraries, but the empirical coupling measured here should not be assumed to carry over
without a new audit. It is not a novelty claim: several 2026 studies report the split
effect and its target-dependence; the checklist addresses the premise underneath them.

---

### SI-A.4 Input validity: legal domains and what was done about them

**Seven of the eight** numeric descriptors of the hMOF release contain negative values, and
the release does not document what they encode. The counts are archived per field in
`outputs/input_validity_audit.csv`; in the full 324,426-structure database, **169 rows
(0.052%) carry at least one negative descriptor** — surface area and void fraction 169 each,
the three pore-diameter fields 138 each, volume and weight 2 each, and void volume none —
and the per-field sets overlap, so the union is 169 rather than the **756** that summing the
seven non-zero columns gives. No descriptor is missing; the target has no missing and
no negative value, and its 1,901 zeros are retained because a zero uptake is a
physically defined outcome rather than a missing record. Zero surface areas (28,528) and
zero void volumes (6,467) are likewise retained: only negative values are treated as
non-physical here, and that choice is a judgement, not a documented property of the release.

The affected rows are not spread evenly over topologies (acs 114, nbo 38, pcu 10, tbo 4,
sra 2, the 1). Their incidence in the analysis samples is 15, 18, 17, 10 and 10 rows at
n = 25,000 for seeds 42, 143, 244, 345 and 446 (0.060%, 0.072%, 0.068%, 0.040% and 0.040%
of each sample), 29 at n = 50,000 and 55 at n = 100,000 for seed 42. Three of the five 25k
samples therefore carry a slightly higher share than the 0.052% database rate and two a
slightly lower one; the sample rates are not uniformly inflated, and none of these counts is
large enough for a rate comparison to be informative on its own. Three consequences are
recorded rather than assumed away.

1. **Figure S2 is refitted on valid rows.** The PDP model of the previous revision was
   fitted on all 25,000 sampled rows and its quantile grid was computed over the same rows,
   so the void-fraction grid reached −0.468 and the surface-area grid −0.5. The grid is now
   computed only over rows with no negative descriptor, every grid point is asserted to lie
   inside the observed valid domain, the model is refitted on those rows, and the historical
   behaviour remains available as `prepare_figS2_pdp_data.py --keep-sentinels`. The two
   versions are different models, not two renderings of one; the newer one is the one shown.
2. **The model-based endpoints were re-run as a paired sensitivity (screening and
   intervention, five seeds; seed 42 is detailed below).** Folds and scoring rows are held fixed, variant A trains on
   every row of the sample, variant B drops the non-physical rows from the *training* part of
   the same folds, and both are scored on the same legal rows, so the contrast is the
   preprocessing step and not a change of evaluation set. Variant A scored on all rows
   reproduces the archived seed-42 values exactly (screening: random top-1% 0.508, topology
   0.132, R² 0.7066 / 0.3660; arms: nbo a/b/e MAE 0.1104 / 0.1797 / 0.1257 and pcu 0.2403 /
   0.2407 / 0.2298), which is the fidelity gate for the re-run; the gate is automated in
   `sensitivity_invalid_rows.py` (a mismatch above 5e-4 exits non-zero, `--gate-only` re-checks
   a finished table).

   *Screening (25,000 rows, seed 42, 15 non-physical rows).* On the legal rows the random
   arm moves from 0.508 to 0.504 at k = 1%, from 0.5653 to 0.5709 at 5% and from 0.6717 to
   0.6705 at 10%; the topology arm moves from 0.132 to **0.112** at k = 1%, from 0.3339 to
   0.3299 at 5% and from 0.4235 to 0.4311 at 10%. R² and MAE are essentially unchanged
   (0.7074 → 0.7082 and 0.3674 → 0.3662; MAE 0.1589 → 0.1587 and 0.2578 → 0.2575) while the
   top-1% overlap moved, so the aggregate error and the top-k metric do not respond together.
   A stable aggregate does not identify or exclude a calibration change, and no such
   inference is drawn here. At this seed the
   random-minus-topology gap at k = 1% widens slightly, from 0.376 to 0.392; the five-seed
   summary below shows that this direction is not representative of the five-seed set.
   *Intervention (50,000 rows, seed 42, 29 non-physical rows).* nbo-side MAE moves from
   0.1100 to 0.1114 (arm a), 0.1794 to 0.1774 (arm b) and 0.1252 to 0.1250 (arm e);
   pcu-side MAE moves from 0.2403 to 0.2429, 0.2407 to 0.2419 and 0.2298 to 0.2311. The
   nbo a→b absolute difference is +0.06946 mmol/g on the historical fit and +0.06602 mmol/g on
   the cleaned fit (+63.1% against +59.2% when scaled by the arm-a mean), and the pcu a→b
   change stays within ±0.5% with a sign that flips between the two variants, while the pcu
   a→e difference is −0.01053 mmol/g and −0.01181 mmol/g — the direction-dependent pattern and
   the near-zero pcu change are preserved at this seed.

   *Five-seed summary (42/143/244/345/446).* The same paired design was run for the other
   four seeds. Across the five seeds, mean random top-1% recovery moves from 0.504 to
   0.502 and mean topology top-1% recovery from 0.193 to 0.198; the per-seed topology
   change ranges from −2.0 to +2.4 pp (mean +0.6 pp), and the random-minus-topology gap
   change ranges from +1.6 to −2.8 pp (mean −0.8 pp). The seed-42 widening is therefore
   not representative: the sign of the screening change varies by seed. The intervention
   directions are stable: nbo a→b is positive in all five seeds (mean +0.0746 → +0.0750
   mmol/g) and pcu a→e is negative in all five (mean −0.0131 → −0.0127). Per-seed values
   are in `outputs/sensitivity_five_seeds_summary.csv`, produced by
   `scripts/summarize_sensitivity.py`.

   Scope: five seeds for screening and the a/b/e arms; the remaining screening strategies were
   **not** re-run on the cleaned sample. The affected rows are ~0.06% of each 25,000-row
   screening sample and ~0.06% of each 50,000-row arm sample.

   *LOTO cleaned sensitivity (100,000 rows, 11 folds).* The Table S8 leave-one-topology-out
   run was repeated with the 55 non-physical rows removed from each training fold, scoring on
   the same legal test rows. The historical-all run reproduces Table S8 exactly; historical-legal
   vs cleaned-legal give pooled 0.3823 → 0.3695, weighted −0.0579 → −0.0631, macro
   −0.5399 → −0.4973 and median 0.2927 → 0.2814. The four-rule signs are unchanged (pooled
   positive, macro negative), so the sign reversal in Table 1 Panel B is not an artefact of the
   55 non-physical rows. This is a single 100k run; the 25k five-seed version is reported next.
   *Source data:* `outputs/loto_cleaned_per_topology_100k.csv`,
   `outputs/loto_cleaned_aggregates_100k.csv`; producer
   `scripts/loto_cleaned_sensitivity.py`.

   *25k five-seed LOTO cleaned sensitivity.* The 25k LOTO design (100 trees, five seeds) was
   repeated with the same paired rule. The historical-all run reproduces Table S9 exactly.
   Cleaned-minus-historical-legal differences are small and not systematic: pooled +0.0011
   (sd 0.0102), weighted +0.0001 (0.0107), macro −0.0052 (0.0236) and median −0.0017
   (0.0293). After cleaning, pooled is positive and macro negative in all five seeds;
   weighted is negative in four of five and flips to +0.0054 at seed 345 (historical
   −0.0038), i.e. the near-zero weighted sign is not stable. The aggregation-dependent sign
   reversal is therefore not a non-physical-row artefact. *Source data:*
   `outputs/loto_cleaned_per_topology_25k.csv`, `outputs/loto_cleaned_aggregates_25k.csv`;
   producer `scripts/loto_cleaned_25k.py`.
3. **The model-free support audit was re-run both ways.** Dropping the 169 rows leaves the
   coarse composition count at 1,622 and the single-topology composition fraction unchanged
   at 74.7226%; the structure-weighted unseen fraction moves from 61.3434% to 61.3350% and
   H(T|C)/H(T) from 0.179942 to 0.180030. Both archived in
   `outputs/input_validity_audit.csv` under `support_audit_sensitivity`.

This bounds what can be claimed: the structural headline is insensitive to the treatment at
the quoted precision, and the model-based endpoints were re-fitted on the cleaned sample for
all five seeds for screening and the a/b/e arms. The screening top-1% effect is seed-dependent
in sign, while the nbo a→b and pcu a→e directions are preserved. Both LOTO cleaned runs
preserve the aggregation-dependent sign pattern (pooled positive, macro negative): 100k
pooled 0.3823 → 0.3695 and macro −0.5399 → −0.4973; the 25k five-seed weighted sign flips at
seed 345 but remains near zero.

### SI-A.5 Composition-key order

The coarse key keeps `organic_linker1` and `organic_linker2` in file order. Sorting the pair
before concatenation collapses six ordered keys into three (three pairs are reversed
duplicates) and reduces the composition count from 1,622 to 1,619; the single-topology
composition fraction moves from 0.7472256 to 0.7467573 (both 74.7% at the quoted precision),
the structure-weighted unseen fraction is unchanged at 0.6134342, and the same seven
topologies are complete hold-outs. The ordered definition is retained because it is the file's own convention and the release
documentation does not say whether `organic_linker1` and `organic_linker2` encode distinct
construction sites. We therefore report the unordered sensitivity instead of asserting a
site semantics, and the sensitivity shows only that the support counts do not depend on the
convention, not that the grouping or intervention models are invariant to it.

## SI-B. Support audit and identification bounds

### SI-B.1 Full per-topology decomposition

The main text reports 7 of 11 topologies as exact composite-key hold-outs and the pcu / nbo
unseen fractions (60.1% / 12.3%). The complete eleven-row decomposition, at the coarse
granularity on the full 324,426-structure database, is:

**Table S1.** Per-topology chemical-support loss (coarse key, full hMOF database).

| Held-out topology | n_samples | seen fraction | unseen fraction |
| --- | ---: | ---: | ---: |
| pcu | 205,361 | 0.399 | **0.601** |
| nbo | 49,464 | 0.877 | **0.123** |
| sra | 23,962 | 0.000 | 1.000 |
| etb | 19,682 | 0.000 | 1.000 |
| acs | 13,655 | 0.000 | 1.000 |
| bcu | 8,795 | 0.000 | 1.000 |
| pts | 1,522 | 0.000 | 1.000 |
| fof | 1,256 | 0.000 | 1.000 |
| tbo | 363 | 0.110 | 0.890 |
| the | 352 | 0.000 | 1.000 |
| rht | 14 | 1.000 | 0.000 |

*Source data:* `outputs/chemistry_seen_by_topology.csv`. "Completely unseen" holds only
for the composite chemistry key, not for each building block separately — a topology can
have no composite-key counterpart while its metal centre or a linker still recurs in
training.

**Component breakdown (same counting rules).** To show which part of the composite key
drives the exclusivity, the same full-database count was repeated with three key
definitions: metal centre only (M = 7), the ordered linker pair (M = 602), and the
conjunction of metal and both linkers (M = 1,622). The single-topology composition
fractions are 57.1%, 46.0% and 74.7%; the structure-weighted unseen fractions are 28.7%,
23.1% and 61.3%; and H(T|C)/H(T) is 0.345, 0.512 and 0.180. Neither component alone
reproduces the conjunction: the metal key is too coarse (7 values), and the linker pair
alone leaves more than half of the compositions multi-topology. The conjunction is
therefore the right headline, while the component rows show that the exclusivity is a
property of the combination rather than of one building block. *Source data:*
`outputs/component_breakdown.csv`, produced by `scripts/component_breakdown.py` from the
same raw hMOF release. The three key fields used here (`metal_linker`, `organic_linker1`,
`organic_linker2`) are complete in this release: 0 missing and 0 literal `NA` values in all
324,426 rows, so the tuple-based grouping has no missing-value category; the script fails
closed if a future input contains one. The functional-group field is not part of this
breakdown; its 1,997 unannotated rows are treated as one fine-granularity value in SI-B.2,
as stated in §2.1.

### SI-B.2 Entropy, singletons and the two directions

The structure-weighted ratio is H(T|C)/H(T) = 0.180 (coarse), so conditioning on coarse
chemistry removes 82.0% of the entropy in the topology label; the reverse ratio
H(C|T)/H(C) = 0.860 says topology removes only 14% of composition uncertainty (H(C) =
10.438 bit, H(T) = 1.777 bit, H(C|T) = 8.981 bit). The
fine-granularity ratio is 7.8%, but the fine space is dominated by singletons: at least
2M − N = 80,536 of 202,481 fine compositions occur exactly once, and the non-singleton
single-topology fraction is 79.1% among the 66,172 non-singleton compositions. The
first-order Miller–Madow correction is
ΔH(T|C) = (K_TC − K_C)/(2 N ln 2): 0.000912 bit (0.3%) at coarse and 0.0307 bit (22%) at
fine, against H(T|C) = 0.320 and 0.139 bit. The coarse headline is barely affected by the
observed singleton count (21 of 1,622, i.e. 1.3%; 74.4% among non-singletons against 74.7%
overall). The correction is a first-order diagnostic, not a proof of unbiasedness. Because a
22.1% correction demotes the hMOF fine value while a 19.8% correction leaves the ARC fine value
standing, "survives" means only that the corrected value stays well above the coarse comparison;
all fine-granularity values are reported as robustness checks rather than headline estimates,
whatever their correction.
The `NA` fill convention inherited from `chemistry_seen.py` does not merge distinct values
here: the three coarse key fields have 0 missing and 0 literal `NA` values, and the fine
key's only missing category is the 1,997 unannotated functional-group entries (no literal
`NA`); this was checked on the full release.
*Source data:* `outputs/singleton_audit.csv` (both entropy ratios, the singleton counts,
the non-singleton fractions and all four Miller–Madow corrections); the coarse/fine
marginals are also in `outputs/confound_full.csv`.

### SI-B.3 Pairwise overlap and the S_g negative result

**Table S2.** Compositions spanning more than one topology, at both granularities
(full hMOF database, 324,426 structures). Each row's last three columns partition the
multi-topology set exactly.

| Granularity | Distinct compositions M | Multi-topology compositions | Share of M | From pcu ↔ nbo | From rht ↔ tbo | From the other 53 pairs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Coarse** (metal + 2 linkers) | 1,622 | **410** | **25.3%** | **408** (99.5% of the multi-topology set) | 2 | **0** |
| **Fine** (+ functional groups) | 202,481 | **13,825** | **6.8%** | **13,821** | 4 | **0** |

*Source data:* `outputs/confound_full.csv` (the two M values and the composition-level
single-topology fractions) and `outputs/jaccard_full.csv` (the 55-pair table). No hMOF
composition spans more than two topologies, so the multi-topology set is exhausted by the
two named pairs at each granularity and the arithmetic closes exactly (408 + 2 = 410;
13,821 + 4 = 13,825). The fine-granularity counts keep the `fillna` convention of
main-text §2.1 (a missing functional group is one additional value, not a dropped row) and
are inflated by singleton compositions, so they are a robustness check only.

The S_g analysis asks whether the unseen-chemistry fraction predicts the hold-out cost of
the same topology, measured on one common run (100,000 samples, the 100-tree, seed-42
model, leave-one-topology-out; `scripts/s_g_curve.py`, `outputs/s_g_curve.csv`). That run
is distinct from the 120-tree LOTO run behind Table S8, which is why the two tables'
per-topology R² values differ in the second decimal (for example etb −2.55 here against
−2.49 there); neither is a correction of the other. This exploratory analysis did not
establish a statistical association. Seven of the eleven topologies share S_miss = 1.000
yet their pooled R² spans −2.55 (etb) to +0.47 (bcu). Across the ten topologies with
n_test ≥ 100, Pearson r = +0.10 (p = 0.78) and Spearman ρ = +0.28 (p = 0.44); excluding
pcu gives r = +0.53 (p = 0.11). These small-sample results do not establish absence of an
association (Figure S7).

**Table S3.** S_g curve: per held-out topology, on one common run (100,000 samples).

| Held-out topology | n_test | S_miss | r = n_train/M_train | sd(y) in fold | pooled R² |
| --- | ---: | ---: | ---: | ---: | ---: |
| rht | 5 | 0.000 | 62.9 | 0.113 | −3.02 |
| nbo | 15,200 | 0.121 | 54.8 | 0.110 | −0.97 |
| pcu | 63,447 | 0.604 | 38.8 | 0.472 | +0.29 |
| tbo | 101 | 0.911 | 63.7 | 0.270 | +0.24 |
| acs | 4,120 | 1.000 | 63.0 | 0.663 | +0.28 |
| bcu | 2,707 | 1.000 | 64.1 | 0.667 | +0.47 |
| sra | 7,323 | 1.000 | 65.7 | 0.883 | +0.40 |
| etb | 6,091 | 1.000 | 64.6 | 0.216 | −2.55 |
| fof | 412 | 1.000 | 63.1 | 0.880 | −1.94 |
| pts | 487 | 1.000 | 62.9 | 0.254 | +0.32 |
| the | 107 | 1.000 | 63.1 | 0.424 | +0.37 |

*Source data:* `outputs/s_g_curve.csv`. The per-fold R² values sit on different test
populations, so their differences cannot be attributed uniquely to the model or protocol;
the panel is a descriptive sensitivity analysis. R² on the *same* test rows is a strong
control (the denominator does not change), and R² on different populations can still be
reported — it just cannot be differenced as a model or protocol effect. The
exploratory S_miss–R² analysis does not establish an error ordering across topology
groups. It uses a different outcome and model configuration from the absolute-MAE
associations in SI-I.4; neither analysis calibrates a prospective risk rule.
The fixed-test intervention in §3.3 addresses a separate within-population
training-pool contrast.

---

## SI-C. Fixed-test-set interventions

### SI-C.1 Arms and the two size-matched designs

The six prespecified arms (a–f) are defined in the main text Methods, which also defines
the post hoc arm (g) used only as a control in SI-C.4. Two distinct size-matched (c)
designs exist and are kept separate: the **nested (c)** (0.1071 ± 0.0048 MAE on nbo,
0.2364 ± 0.0031 on pcu, from `scripts/diversity_control.py`,
`outputs/composition_matched_control.csv`) makes five size-matched draws **within each of
the five outer seeds** (25 draws), with the SD taken across the five outer seed means, never
across the 25 draws; the **seed-42 repeated-draw (c)** (0.1030 ± 0.0031,
from `scripts/confound_diagnosis.py --size-match`, `outputs/isoreticular_control_sizematched.csv`)
uses five draws at the seed-42 baseline. These are different replication designs, not two
precisions of one estimate.

### SI-C.2 Arm (d) construction limitation

Arm (d) reproduces (b)'s topology/composition profile, which confines it to (b)'s own row
set (42,329 − 31,682 = 10,647); it is therefore an internal-consistency check, not an
independent mechanism contrast. Its per-seed composition counts (496 compositions against
(c)'s 1,484) show that composition count alone does not order the result.

### SI-C.3 Per-seed tables

**Table S4.** Controlled contrast at seed 42: fixed test set, changing training set.

| Test topology | Training set | n_train | R² | **MAE** | **RMSE** | MAE/sd |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| **nbo** (n = 7,671) | with the partner pcu | 42,329 | −0.875 | **0.1104** | **0.1456** | 1.038 |
| **nbo** (n = 7,671) | **pcu removed** | 10,647 | −4.383 | **0.1797** | **0.2467** | 1.690 |
| pcu (n = 31,682) | with the partner nbo | 18,318 | +0.268 | 0.2403 | 0.4038 | 0.509 |
| pcu (n = 31,682) | **nbo removed** | 10,647 | +0.262 | 0.2407 | 0.4055 | 0.510 |

**Table S5.** Arms (e) and (f) at seed 42: partner-shared-composition removal and
size-matched control. Every cell is a seed-42 value; `n_shared_removed` for arm (e) is the
number of partner rows this seed actually removes (12,300 at seed 42 on the nbo side and
6,765 on the pcu side; the five-seed means are 12,342 and 6,689, the numbers quoted in
main-text §3.3).

| Test topology | Training set | n_train | **MAE** | **RMSE** | R² | n_shared_removed | n_compositions |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **nbo** | (a) with partner | 42,329 | **0.1104** | 0.1456 | −0.875 | — | 1,530 |
| **nbo** | (b) partner removed | 10,647 | **0.1797** | 0.2467 | −4.383 | 31,682 | 493 |
| **nbo** | (e) shared-composition rows removed | 30,029 | **0.1257** | 0.1660 | −1.438 | 12,300 | 1,143 |
| **nbo** | (f) size-matched from (e) | 10,647 | **0.1211** | 0.1667 | −1.459 | — | 1,117 |
| pcu | (a) with partner | 18,318 | 0.2403 | 0.4038 | +0.268 | — | 923 |
| pcu | (b) nbo removed | 10,647 | 0.2407 | 0.4055 | +0.262 | 7,671 | 493 |
| pcu | (e) shared-composition rows removed | 11,553 | **0.2298** | 0.3949 | +0.300 | 6,765 | 536 |
| pcu | (f) size-matched from (e) | 10,647 | **0.2322** | 0.4005 | +0.280 | — | 535 |

**Table S6.** Full per-seed MAE [mmol/g] for the five outer seeds and every arm, nbo and
pcu test sets. Arm (c) is the mean of that seed's five size-matched inner draws.

| Test | seed | a | b | c (nested) | e | f |
|---|---|---:|---:|---:|---:|---:|
| nbo | 42 | 0.1104 | 0.1797 | 0.1103 | 0.1257 | 0.1211 |
| nbo | 143 | 0.1030 | 0.1628 | 0.1031 | 0.1279 | 0.1325 |
| nbo | 244 | 0.1077 | 0.2013 | 0.1116 | 0.1453 | 0.1317 |
| nbo | 345 | 0.1082 | 0.1809 | 0.1096 | 0.1364 | 0.1244 |
| nbo | 446 | 0.1034 | 0.1807 | 0.1009 | 0.1275 | 0.1152 |
| pcu | 42 | 0.2403 | 0.2407 | 0.2374 | 0.2298 | 0.2322 |
| pcu | 143 | 0.2465 | 0.2383 | 0.2369 | 0.2318 | 0.2262 |
| pcu | 244 | 0.2387 | 0.2387 | 0.2395 | 0.2287 | 0.2308 |
| pcu | 345 | 0.2399 | 0.2401 | 0.2370 | 0.2262 | 0.2259 |
| pcu | 446 | 0.2466 | 0.2401 | 0.2311 | 0.2299 | 0.2368 |

Arm (d) uses the same row set as (b) and is therefore not tabulated separately. The absolute
paired 95% interval for the (a)→(b) change is a t-interval on the five within-seed differences;
the percentage version divides that difference by the with-partner mean, with the denominator
treated as fixed.

**Table S7.** Training-mean-predictor baseline, MAE divided by test-set SD (five-seed mean
± SD, generated from the raw uptake by the archived script under the original sampling
rule). Each arm's baseline is its own
training-fold mean, so it differs between arms. The `MAE_over_sd` column of the archived
`isoreticular_control_seeds.csv` is the random forest's standardised error, **not** this
baseline.

| Test topology | arm | training-mean predictor MAE / test-set SD |
| --- | --- | ---: |
| nbo | a (with partner) | 3.438 ± 0.085 |
| nbo | b (partner removed) | 5.171 ± 0.143 |
| pcu | a (with partner) | 0.702 ± 0.004 |
| pcu | b (partner removed) | 0.969 ± 0.009 |

Both arms beat their own baseline in all five seeds on both test topologies.
For each seed and arm, the constant prediction is the mean of that arm's training
uptake. MAE is divided by the test-target SD (ddof=0); the table reports the mean and
sample SD (ddof=1) of the five seed-level ratios. No model is fitted for this calculation.
*Source data:* `outputs/baseline/training_mean_baseline_seeds.csv` and
`outputs/baseline/training_mean_baseline_summary.csv`.
*Producer:* `scripts/training_mean_baseline.py`; input checksums, execution timeline and
verification commands are recorded in `REPRODUCE.md`.

The five-seed means of every arm (the headline numbers of main-text Table 2) are:
nbo MAE — a 0.1065 ± 0.0032, b 0.1811 ± 0.0136, c 0.1071 ± 0.0048, e 0.1326 ± 0.0082,
f 0.1250 ± 0.0073; nbo RMSE — a 0.1352 ± 0.0077, b 0.2405 ± 0.0136, c 0.1375 ± 0.0109,
e 0.1745 ± 0.0127, f 0.1697 ± 0.0145; pcu MAE — a 0.2424 ± 0.0038, b 0.2396 ± 0.0010,
c 0.2364 ± 0.0031, e 0.2293 ± 0.0020, f 0.2304 ± 0.0045; pcu RMSE — a 0.4030 ± 0.0021,
b 0.4024 ± 0.0030, c 0.4002 ± 0.0044, e 0.3935 ± 0.0032, f 0.3961 ± 0.0066. The (c) SD
is the nested value (SD across the five outer seed means of five inner draws each), not the
flat SD over the 25 draws.
*Source data:* `outputs/isoreticular_control_seeds.csv` (a, b),
`outputs/composition_matched_control.csv` (c, d), `outputs/arm_e_partner_coverage.csv`
(e, f). Arm (f)'s n_train equals arm (b)'s **by construction** — it draws that many rows
from arm (e)'s pool — so the two agree seed by seed, and the script asserts it.

### SI-C.4 A post hoc random-partner-row control

The a–f design does not separate “remove the shared-composition partner rows” from
“remove partner rows in general”. We therefore added a post hoc arm (g): from arm (a),
remove at random the same number of partner rows that arm (e) removes, without conditioning
on whether their composition occurs in the test set. This control was run after the a–f
design was fixed; it is a post hoc check, not a new preregistered arm, and it does not change
Table 2.

The original five-seed means are a/e/g = 0.2424/0.2293/0.2341 mmol/g on pcu
and 0.1065/0.1326/0.1189 on nbo. A paired-seed reanalysis gives e−g =
−0.004850 mmol/g for pcu (95% t interval [−0.010086, +0.000385]) and
+0.013668 for nbo ([+0.009000, +0.018337]). The pcu interval includes zero.
Thus e's improvement over a does not establish a composition-specific advantage
over same-count random partner deletion. These are contrasts between training
interventions within one chemistry-overlapping pair; they do not isolate shared
composition from descriptor or target-distribution changes. The five sample redraws
overlap within the same database, so the intervals do not represent independent
external validation. A second adequately supported chemistry-matched pair is not
available in hMOF (rht ↔ tbo has only two shared compositions).
*Source data:* `outputs/partner_random_g.csv`, `outputs/arm_e_partner_coverage.csv`
and `outputs/followup_20261023/experiment5/main_a_e_g_paired.csv`.
The fixed-size matched replacement follow-up (SI-I.5) addresses a different
intervention and retains residual composition and outcome differences.

---

## SI-D. Protocol and aggregation robustness

### SI-D.1 Aggregation rules and valid folds

The four rules (pooled / weighted / macro / median) and their LOTO values (+0.3814 /
−0.0589 / −0.5414 / +0.2782) are in the main text. All eleven fold R² values are defined in
the 100,000-row LOTO run. In the 25,000-row runs, seeds 42, 345 and 446 each contain a
singleton rht test fold, giving ten valid fold R² values; seeds 143 and 244 have eleven.
Pooled scoring retains all predictions, whereas macro and median aggregation use defined
fold scores. Across the five 25k seeds, pooled's dispersion is 4.2% of its mean while
macro's is 91.5% (Figure S4; the four rules of one run and their eleven folds are in
Figure S5).

**"Excluding pcu" is a scoring-fold exclusion, not a retraining.** Predictions from the
other ten test folds were retained without refitting; their original training pools were
unchanged. Recomputing pooled over those ten folds gives +0.4629 over the remaining 36,553
test rows; the per-group aggregates excluding pcu (weighted −0.678, macro −0.625) are
different summaries of the same remaining folds. *Source data:* `outputs/metrics_audit.csv`.

**Table S8.** Leave-one-topology-out per held-out topology on the 100,000-sample single run
(120 trees, `scripts/loto_full_metrics.py recompute`). Every fold has a defined R²
(11/11 valid: n_test ≥ 2 and SST > 0). MAE and RMSE are in mmol/g; R² is normalised within
each fold by that fold's own target sum of squares. The four aggregates of this run are
pooled +0.381, weighted −0.059, macro −0.541 and median +0.278
(`outputs/loto_aggregates_100k.csv`).

| Held-out topology | n_test | MAE | RMSE | per-topology R² |
| --- | ---: | ---: | ---: | ---: |
| pcu | 63,447 | 0.2382 | 0.3952 | +0.298 |
| nbo | 15,200 | 0.1153 | 0.1537 | −0.943 |
| sra | 7,323 | 0.4793 | 0.6862 | +0.396 |
| etb | 6,091 | 0.3125 | 0.4041 | −2.492 |
| acs | 4,120 | 0.4193 | 0.5633 | +0.278 |
| bcu | 2,707 | 0.3056 | 0.4866 | +0.467 |
| pts | 487 | 0.1153 | 0.2087 | +0.326 |
| fof | 412 | 1.2610 | 1.5029 | −1.924 |
| the | 107 | 0.1660 | 0.3275 | +0.399 |
| tbo | 101 | 0.1556 | 0.2330 | +0.247 |
| rht | 5 | 0.1876 | 0.2018 | −3.007 |

MAE and R² need not rank topologies identically, because R² normalises squared error by each
fold's target variation. For example, nbo has a lower MAE than pcu (0.115 versus
0.238 mmol/g), but a lower R² (−0.943 versus +0.298). These metrics therefore provide
complementary descriptions of predictive performance across different test populations.

**Table S9.** Leave-one-topology-out aggregation on the 25,000-sample five-seed design
(100 trees; `scripts/loto_full_metrics.py recompute25k`; `outputs/loto_aggregates_25k.csv`).
`weighted` is the sample-size-weighted mean of the valid per-fold R²,
Σ(nᵢR²ᵢ)/Σnᵢ, normalised over valid folds only; "covered" is the number of test rows those
valid folds contain. Seeds 42, 345 and 446 each contain a singleton rht fold (n_test = 1),
which has no defined R² and is excluded from weighted/macro/median but retained in the pooled
score.

| seed | n | pooled | weighted | macro | median | valid folds | covered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 42 | 25,000 | +0.367 | −0.052 | −0.354 | +0.247 | 10 | 24,999 |
| 143 | 25,000 | +0.337 | −0.033 | −0.538 | +0.206 | 11 | 25,000 |
| 244 | 25,000 | +0.339 | −0.032 | −1.539 | +0.264 | 11 | 25,000 |
| 345 | 25,000 | +0.358 | −0.004 | −0.238 | +0.240 | 10 | 24,999 |
| 446 | 25,000 | +0.367 | −0.031 | −0.289 | +0.278 | 10 | 24,999 |

**Table S10.** Within- versus cross-topology R² per topology (25,000 samples, eight
structure-derived descriptors; `outputs/within_vs_cross_final.csv`).

| Topology | n | within R² | cross R² |
| --- | ---: | ---: | ---: |
| bcu | 705 | 0.810 | 0.496 |
| sra | 1,859 | 0.711 | 0.460 |
| acs | 1,049 | 0.662 | 0.159 |
| pcu | 15,833 | 0.648 | 0.279 |
| nbo | 3,798 | 0.612 | **−0.312** |
| etb | 1,481 | 0.477 | **−4.269** |

**Table S11.** Macro and median aggregation for the within/cross comparison (25,000 samples).

| Rule | within | cross |
| --- | ---: | ---: |
| macro | **+0.654** | **−0.531** |
| median | +0.655 | +0.219 |

Median and macro differ by 0.75 because etb (−4.27) and nbo (−0.31) pull the mean; every
topology moves in the same direction (within > cross for all six groups), so the
disagreement is about magnitude only (Figure S3). This is a different statistic from the LOTO aggregate
of §3.2 (different test folds, feature set and sample size), so the two sections' macro
values (−0.541 and −0.531) are close by coincidence, not identity.

### SI-D.2 Model families and the second target

The three families are instantiated as `RandomForestRegressor(n_estimators=120, random_state=42)`, `HistGradientBoostingRegressor(random_state=42)` with scikit-learn defaults, and `StandardScaler` followed by `RidgeCV(alphas=(0.1, 1.0, 10.0, 100.0))`; the 100,000-row subsample is drawn with `random_state=42` and no seed is varied, so each family contributes one fit per protocol. The random-to-topology gap was refit under gradient boosting and ridge (single fits, no
tuning), confirming it is not specific to random forests; the per-family rows are in
`outputs/leakage_results_gb100k.csv` and `outputs/leakage_results_ridge100k.csv`. The
second target (log-selectivity) is in `outputs/leakage_results_logsel100k.csv`; the main
text states the target dependence in one sentence.

### SI-D.3 The 415-feature matched check

Removing the topology block from both arms (415 features) gives the chemistry-key decrease
as 21.5% of the topology decrease (21.1% unmatched); the matched decrease is 0.3603
(0.3603271, rounded). This is a descriptive protocol ratio, not a causal share.
*Source data:* `outputs/leakage_results_notopo100k.csv`.

---

## SI-E. Diagnostics and alternative analyses

### SI-E.1 Candidate explanations

**Table S12.** R² by nearest-neighbour distance bin (25,000 samples per scheme). The 12
bins are quantiles of the distance distribution pooled over the two schemes, with
open-ended first and last bins; `n` is the number of test rows each scheme
contributes to that bin. The two schemes do not hold the same rows even where the
edges coincide, so each row is a pair of overlapping but non-identical
populations. Producer: `leakage_mechanism.py`; the bin edges and both sample
counts are fields of `fig7_nn_curve_final.csv`, not a separate rule (REPRODUCE,
"Distance-bin diagnostic").

| nearest-neighbour distance bin | n (random) | n (topology) | random R² | LOTO R² |
| --- | ---: | ---: | ---: | ---: |
| `(-inf, 0.082]` | 3,671 | 499 | 0.693 | 0.258 |
| `(0.082, 0.105]` | 3,435 | 730 | 0.652 | 0.222 |
| `(0.105, 0.127]` | 3,193 | 972 | 0.626 | 0.157 |
| `(0.127, 0.149]` | 2,960 | 1,209 | 0.695 | 0.170 |
| `(0.149, 0.173]` | 2,724 | 1,440 | 0.713 | 0.276 |
| `(0.173, 0.2]` | 2,320 | 1,847 | 0.670 | 0.292 |
| `(0.2, 0.232]` | 1,838 | 2,329 | 0.695 | 0.258 |
| `(0.232, 0.271]` | 1,461 | 2,705 | 0.680 | 0.281 |
| `(0.271, 0.318]` | 1,106 | 3,061 | 0.637 | 0.292 |
| `(0.318, 0.386]` | 898 | 3,268 | 0.515 | 0.254 |
| `(0.386, 0.507]` | 744 | 3,423 | 0.705 | 0.003 |
| `(0.507, inf]` | 650 | 3,517 | 0.541 | **−0.775** |

The two curves do not coincide in any bin, but **neither column is monotonic**, and the
degradation is concentrated in the largest-distance bin (−0.775). The 25,000 rows of each scheme fall entirely into the 12 bins
(3,671 + … + 650 = 25,000 for random, 499 + … + 3,517 = 25,000 for the
held-out-topology scheme), so no bin was dropped by a minimum-count rule
and the table preserves the full support set. Within-bin median distances
differ by scheme (0.066 for random against 0.070 for the held-out scheme in
the first bin), which is why the rows are keyed by bin edges rather than by a
shared median. Distance-stratified and
family-seen diagnostics describe differences across evaluation subsets; they do not
estimate the fraction of the topology-hold-out penalty attributable to distance or
chemistry, because the subsets have different target distributions and R² denominators.
The family-level diagnostic is exploratory in the same way: the composite family (metal +
both linkers + functional groups, **excluding topology**) is present in training for only
8.9% of random-split test samples, so the family-seen contrast is a weak negative rather
than a clean comparison. SHAP
family attribution is essentially unchanged between splits (structure-derived 82.3% →
85.1%, identity 17.7% → 14.9%) (Figure S1; partial dependence of the four leading
descriptors is in Figure S2). None of these diagnostics fully accounts for the gap, and
none is an orthogonal intervention, so they are descriptive rather than decisive.

### SI-E.2 The withdrawn deep-learning comparison

**Table S13.** Why the deep-learning comparison is not interpretable: two test sets 7.7×
apart in target variance.

| | Random split | Topology hold-out (test set all pcu) |
| --- | ---: | ---: |
| n | 500 | 317 |
| **Test-set target variance Var(y)** | **0.5460** | **0.0706** |
| R² | +0.205 | **−0.448** |
| **MAE** | **0.3958** | **0.2617** |
| **RMSE** | **0.6587** | **0.3199** |

The variances differ 7.7× (standard deviations 2.78×); R² is normalised by the test-set
variance, and the hold-out side's MAE and RMSE are **smaller** on its own test population.
Lower absolute error on a different test population does not establish model superiority,
so these six numbers are reported only to show why the comparison is not interpretable. The R² and test-variance values are in `outputs/metrics_audit.csv` (the CGCNN rows; for these rows the `macro` column stores the test-set variance); the MAE and RMSE values are reported from the run log of the withdrawn arm, which is not archived. No claim elsewhere in the paper rests on these numbers. A crystal-graph arm would be interpretable only if (i) the two
test sets are matched on topology composition and target variance, (ii) MAE/RMSE, not R²,
are the primary metrics, and (iii) both arms are trained to convergence; none of the three
holds.

### SI-E.3 Mitigation and omitted-variable analyses

**Table S14.** Mitigation strategies compared under a fixed protocol (25,000 samples).

| Feature set | # features | Random R² | Grouped-by-topology R² | gap |
| --- | ---: | ---: | ---: | ---: |
| structure-derived + building-block one-hot (baseline) | 426 | 0.7066 | 0.3660 | **0.341** |
| structure-derived descriptors only (identity removed) | 8 | 0.6719 | 0.3740 | 0.298 |
| structure-derived + hash encoding (32-dim) | 40 | 0.6652 | 0.3762 | 0.289 |
| structure-derived + **in-fold target encoding** | 11 | 0.6998 | 0.2885 | **0.411** |

In this single-run comparison using the original identity block, removing that block
changes topology-grouped R² from 0.366 to 0.374 while lowering random-split R². This
does not characterize the effect of adding linker identities: the follow-up I−B
comparisons use a different identity block, encoding and feature-subsampling setting
(SI-I.1).
Under this implementation, in-fold target encoding increased the random-versus-grouped
performance gap (0.411 against the 0.341 baseline); the implementation encodes each training fold with its own whole-fold
category means and no inner cross-fitting, and a canonical inner-cross-fitted implementation
is not evaluated here. Hash encoding and identity removal shrink the gap by lowering the
random-split R² far more than the grouped-split R² moves, so both terms of every gap are
reported. *Source data:* `outputs/mitigation_results_mit25k.csv`.

---

## SI-F. Screening and the elite subset

### SI-F.1 All seeds and k values

The five-seed top-1% overlap is in the main text (50.4% → 19.3%, complete ordering 4/5).
The per-seed rows, all five strategies, and the single seed-42 run (which sits at the
low-recovery end, 0.132) are in `outputs/screening_utility_seed{42,143,244,345,446}.csv`
and `outputs/screening_utility.csv`. The oracle shortfall is 46.3% by the ratio-of-means
convention (1 − mean(selected)/mean(oracle) = 46.324993%); the per-seed mean of ratios
(mean of 1 − selected/oracle) is 46.300683% — a distinct statistic that happens to round to
the same 46.3%. The selected mean is 1.742 mmol/g and the oracle mean 3.246 mmol/g; the
oracle differs across seeds (3.207–3.319 mmol/g, mean ± SD 3.246 ± 0.043) because each seed
redraws the sample, while within a seed the oracle is the same for every strategy.

**Table S15.** Five-seed top-k overlap at three budgets (% of the true top-k recovered, mean ±
SD across the five seeds; the same five seeds for every strategy).

| Budget k | random overlap | topology overlap |
| --- | ---: | ---: |
| 1% | 50.40 ± 2.48 | 19.28 ± 7.06 |
| 5% | 56.82 ± 1.09 | 33.31 ± 2.06 |
| 10% | 67.23 ± 0.49 | 40.66 ± 1.70 |

The gap persists at all three budgets and is not monotonic in k: 31.1 percentage points
at 1%, 23.5 at 5% and 26.6 at 10% (random minus topology, five-seed means). The main text
quotes the k = 1% headline and refers the 5%/10% values here rather than mixing them with
the seed-42 numbers. For the k = 1% headline the five paired within-seed differences give
31.12 ± 5.26 percentage points (95% paired t interval 24.59 to 37.65; t(4) = 13.24,
p = 1.9 × 10⁻⁴), computed by `scripts/screening_paired_tests.py` and archived in
`outputs/paired_tests_20261024.csv`; the 5% and 10% gaps are reported descriptively only,
because k = 1% is the prespecified headline budget and no test is attached to the wider
budgets. As in the main text, the interval describes seed-to-seed variation within one
database. *Source data:* `outputs/screening_utility_seed{42,143,244,345,446}.csv`.

**Tie audit at the truncation.** Row-level predictions are archived for the random and
topology strategies (five seeds, two row policies: historical and cleaned). At k = 1%, 5%
and 10% no predicted score tie straddles the cut in any of the 60 combinations; the maximum
number of rows sharing the boundary score is one. Re-ranking the tied block by lowest source
row ID instead of archived row order selects exactly the same members in every case
(`outputs/finish_20261023/tie_audit.csv`, produced by `scripts/analyze_finish_20261023.py`).
The chemistry-key, linker-pair and metal strategies are archived only as summary metrics, so
the same audit cannot be repeated for them; the rule in the main text applies to all five but
is only verified for two. For the fixed candidate pool, ties are resolved by source-row ID and
the archived file stores only the selected materials, not the full score vector
(SI-I.6), so no tie audit is possible there.

**Candidate resampling versus model redraws.** A within-sample row bootstrap (200 resamples
per seed and strategy, k = 1%) gives an overlap SD of 2.1–3.0 percentage points, against a
five-seed SD of 2.5 points for random and 7.1 points for topology. The two objects answer
different questions: the bootstrap varies which 25,000 materials are in the candidate set under
one fitted protocol, while the seed SD varies the model redraw and its training memberships.
Neither estimates variation across independent MOF libraries, and the smaller bootstrap SD must
not be substituted for the seed SD (`outputs/finish_20261023/oof_candidate_bootstrap.csv`).

### SI-F.2 The elite subset and its permutation nulls

The confound is undiluted on the release's elite subset (the curated ≥ 2.0 mmol/g set,
**not** a model's own top-k): H(T|C) = 0.000 bit there. Observed single-topology fraction
**100.0%** (coarse, M = 448) against a row-level permutation null mean of **21.4%**
(sd 1.0%; 95% interval 19.64–23.44%); in 10,000 row-level permutations **no simulated value
reached the observed 100.0%**, so the Monte Carlo p is bounded by the simulation precision
(~1×10⁻⁴) rather than being an exact zero (`outputs/null_elite_permutation_row.csv`). A
composition-level permutation (`outputs/null_elite_permutation_composition.csv`) gives null
mean 100.0% with zero variance, because it holds fixed the property "each composition maps
to a single topology" — the specific topology label of a composition may change, but the
single-topology statistic is 1 by construction; the row-level unit is therefore the correct
test, and the composition-level result is reported only to make that choice auditable. At
fine granularity the null mean is already 86.3%, because singleton compositions dominate and
remain single-topology under permutation, so the fine-grained 100.0% carries far less
information.

---

## SI-G. Ten targets and identity information

### SI-G.1 The ten-target panel (descriptive)

**Table S16.** Ten-target panel: split effect and descriptor-only R² under both splits
(25,000 samples).

| Target | R² (random) | R² (topology hold-out) | **ΔR²** | R² (descriptors only, random) | R² (descriptors only, topology) |
| --- | ---: | ---: | ---: | ---: | ---: |
| CO₂ uptake 0.15 bar / 298 K | 0.704 | 0.370 | 0.335 | 0.672 | 0.377 |
| CO₂ uptake 0.10 bar / 363 K | 0.518 | 0.113 | 0.405 | 0.488 | **−0.076** |
| CO₂ uptake 0.70 bar / 413 K | 0.587 | **0.017** | **0.571** | 0.535 | 0.044 |
| **excess** CO₂ uptake 0.15 bar | 0.973 | 0.972 | **0.001** | 0.981 | 0.980 |
| CO₂ uptake (CO₂/N₂ binary) | 0.700 | 0.377 | 0.322 | 0.665 | 0.388 |
| N₂ uptake (CO₂/N₂ binary) | 0.770 | 0.394 | 0.376 | 0.737 | 0.491 |
| working capacity (VSA) | 0.713 | 0.388 | 0.325 | 0.679 | 0.404 |
| working capacity (TSA) | 0.726 | 0.454 | 0.272 | 0.698 | 0.466 |
| CO₂ heat of adsorption | 0.861 | 0.744 | 0.117 | 0.848 | 0.755 |
| log₁₀(CO₂/N₂ selectivity) | 0.825 | 0.726 | 0.100 | 0.813 | 0.711 |

The 0.704 / 0.370 pair differs from the main-text baseline (0.7066 / 0.3660) by ≤ 0.004
because this panel is a separate run using 100 rather than 120 trees. The split effect is
positive on 10/10 targets (median +0.324, Wilcoxon p = 0.0020), but the targets are
algebraically dependent, so n = 10 is not ten independent units and the p-values are
descriptive, not confirmatory.

### SI-G.2 Identity-block availability

Under the original representation, the observed identity effects differ across grouping
schemes and covary descriptively with the availability of non-grouped identifiers.
This availability pattern is a property of the fold construction; it is not a general
rule for the value of identity features or an identified mechanism of the topology penalty. *Source data:*
`outputs/chemistry_seen_grouping.csv`, `outputs/multitarget_confound_{metal,linker_pair}.csv`.

---

## SI-H. ARC-MOF sources and granularity

### SI-H.1 Non-singleton and sampling controls

The coarse single-topology fraction is 99.3% (256,351 rows, 180,989 compositions), 97.3%
among the 49,869 non-singleton compositions; the fine values are 99.7% and 98.2% (26,380
non-singletons). The occupied-cell differences for the entropy correction are 3,989
(coarse) and 863 (fine), giving 0.0112 bit (15.2%) and 0.0029 bit (19.8%) against
H(T|C) = 0.0739 and 0.0147 bit. *Source data:* `outputs/singleton_audit.csv` (all four
values, both singleton counts and both corrections); the marginals are also in
`outputs/confound_arcmof.csv`.

**Why the audit N is 256,351.** The ARC-MOF release has 264,225 structures; 7,874 lack the
metal/linker cluster keys and are excluded from the coarse audit (256,351 rows). The fine
key additionally requires a functional-group key. Of the 256,351 coarse-valid rows,
41,808 lack that key and the remaining 214,543 carry both; 49,682 is the full-release count
of structures missing either key (264,225 − 214,543). Rows are therefore dropped by key availability, not by topology; the
topology column used here is `Crystalnet`.

**Cluster IDs are chemistry-level labels generated from RAC descriptors.** The release
distributes three chemistry-cluster tables (`mc-clusters.csv`, `flig-clusters.csv`,
`func-clusters.csv`) and a separate topology table (`all_topology_lists.csv`); its data
description states that each chemistry table assigns each MOF to a cluster and that negative IDs
denote “not in any cluster (i.e., assumed unique)” (ref. 15). More importantly, the ARC-MOF SI
describes the diversity clustering as UMAP + HDBSCAN on RAC descriptors for metal-centre,
ligand, functional-group and geometry types, with `min_samples = 1`, minimum cluster size 2 and
`epsilon = 0.01`; points assigned −1 were treated as unique, and clusters were validated by the
within-cluster standard deviation of RACs (ref. 3, SI “Diversity Analysis”, Tables S3–S4).
Topology is not among the clustering input types. The cluster IDs are therefore chemistry-level
clusters, not per-topology labels; in the archived data they recur across topologies: 495 of
2,450 metal-cluster IDs (20.2%), 16,866 of 125,230 linker IDs (13.5%) and 7,272 of 43,745
functional-group IDs (16.6%) occur in more than one topology. This rules out the circularity in
which each observed ID would be used in only one topology. Because the clustering inputs are RAC
descriptors rather than topology labels, the observed cross-topology recurrence is not a
per-topology artefact. *Source data:* `outputs/arcmof_cluster_span.csv`, produced by
`scripts/arcmof_cluster_span.py` from the archived ARC metadata.

### SI-H.2 Source removal and the DB0 condition

Removing one source sub-library at a time bounds any hMOF overlap, **only if** the
hMOF-derived rows are concentrated in the largest sub-library (DB0); removing DB0 discards
79.0% of the analysed rows, so the exercise is a stress test on a fifth of the data, not a
worst case over all of it.

**Table S17.** Leave-one-source-out single-topology fraction, coarse and fine columns (the two
granularities are separate; the "any other source" rows report the minimum and maximum over
the remaining sub-libraries).

| Removal | coarse | fine |
| --- | ---: | ---: |
| none | 99.26% | 99.74% |
| DB0 removed | **98.57%** | **98.96%** |
| any single other source (minimum) | 99.22% (DB5) | 99.72% (DB1) |
| any single other source (maximum) | 99.46% (DB13) | 99.84% (DB13) |

*Source data:* `outputs/confound_arcmof_excl_derived.csv`, `outputs/arcmof_overlap.csv`.

### SI-H.3 Within-source null on the common support set

**Table S18.** Per-source single-topology fraction against its within-source topology-permutation
null (common support set, coarse chemistry, 1,000 permutations; the degenerate single-topology
source DB6 is excluded). "Excess" is observed − null mean.

| source | N | M | topologies | observed | null mean | 95% reference | excess (pp) | H(T) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DB0 | 169,489 | 121,479 | 178 | 99.74% | 77.17% | 77.06–77.28 | +22.6 | 2.29 |
| DB1 | 11,546 | 9,008 | 19 | 100.0% | 95.10% | 94.89–95.29 | +4.9 | 1.93 |
| DB5 | 12,496 | 9,651 | 11 | 99.95% | 94.45% | 94.12–94.78 | +5.5 | 0.69 |
| DB7 | 4,653 | 3,588 | 19 | 99.36% | 85.84% | 85.23–86.48 | +13.5 | 2.02 |
| DB12 | 2,411 | 1,352 | 163 | 98.45% | 61.14% | 60.50–61.76 | +37.3 | 5.59 |
| DB13 | 4,207 | 3,220 | 10 | 92.30% | 81.58% | 80.93–82.17 | +10.7 | 2.31 |
| DB15 | 965 | 753 | 35 | 85.39% | 82.84% | 82.07–83.67 | +2.6 | 3.74 |

The observed single-topology fraction sits above its own within-source topology-permutation
null in every non-degenerate source, with excesses from **+2.6** (DB15) to **+37.3** (DB12)
percentage points (Figure S6b; the per-source exclusivity rates of Figure S6a show the same
spread at both granularities). The two nulls
used in this section address different hypotheses and are reported separately: (i) the
within-source permutation holds composition keys and topology-label counts fixed and
permutes topology labels across records (1,000 permutations, Figure S8c); (ii) a
common-rate binomial parametric bootstrap (20,000 draws) tests between-source
heterogeneity. The excess shows a moderate-to-strong positive point estimate against H(T)
(Pearson r = +0.67, p = 0.10; Spearman ρ = +0.32, p = 0.48; n = 7 non-degenerate sources),
but with seven points and one influential row (DB12, H(T) = 5.59 bit, +37.3 pp) this is
weak evidence; removing DB12 flips the point estimate (Pearson r = −0.08, Spearman ρ
−0.09), so the association is not established. The source-to-source spread is 3,554× larger
than a one-common-rate binomial model predicts at the fine granularity (about 2,000× at the
coarse); in the 20,000-draw bootstrap **no simulated statistic reached the observed value**,
so the reported Monte Carlo p is bounded by the simulation precision (~5×10⁻⁵) rather than
being an exact zero. The within-source permutation is a label-shuffle reference, not a test
of a database-construction mechanism.
*Source data:* `outputs/common_support/null_topology_cardinality.csv`,
`outputs/source_confound_granularity.csv`, `outputs/source_spread_test.csv`.

---

## SI-I. Follow-up and sensitivity experiments: representation, support and screening limits

These follow-up analyses were integrated on 23 October 2026 and comprise exactly six
experiments, in the order used in the abstract, main-text 2.7 and the cover letter:
(1) representation (SI-I.1), (2) constituent novelty and numerical support (SI-I.2),
(3) the CoRE structural-feasibility pilot (SI-I.3), (4) descriptive fold-level diagnostics
(SI-I.4), (5) fixed-size partner replacement (SI-I.5) and (6) fixed-candidate-pool
screening (SI-I.6). The ARC-MOF audit is not one of the six: it is the second-database
support audit of main-text 3.5, with its controls in SI-H, and it adds no new performance
or representation experiment. They complement the original analyses; they do not share a
single replication unit, preprocessing rule or feature-encoding implementation. The new
evidence is archived under `outputs/followup_20261023/` and belongs to the version-of-record
deposit described in main-text 9 (v1.4), not to the earlier v1.3 release, which covers the
original analyses only. No model was refitted during this manuscript-integration step.
Tables S19–S24 can be recomputed from the archived metrics with
`scripts/verify_followup_tables.py`. SI-I.7 adds a prespecified feature-subsampling
sensitivity (Table S25) that *was* refitted on 24 October 2026 and is counted outside the
six; its archive is `outputs/sensitivity_mf1/mapped/` and `outputs/sensitivity_mf1/full/`.
That check establishes arithmetic consistency, not a fresh raw-data rerun.

### SI-I.1 Representation comparisons (experiment 1)

Both targets were modelled: CO₂ uptake at 0.15 bar and 298 K (mmol g⁻¹), and
log₁₀(CO₂/N₂ selectivity), retaining only positive selectivity before transformation.
G contains the eight numerical structure descriptors; these include mass and
mass-normalized quantities and are not chemically orthogonal. B adds metal-node
and functional-group identifiers. I adds the two linker identifiers in their original
file slots. O adds topology to B; its training-fold encoding and feature-sampling
configuration differ from the original 426-column analysis, so it is not an exact
rerun of that model. T retains B and substitutes two parent-linker fingerprints for
the linker-identifier blocks: 2,048 Morgan bits per slot, radius 2, no chirality.
Constant fingerprint bits are removed using training rows only. Categorical encoders
are fitted on training rows; unknown categories are ignored.

RF and ExtraTrees (ET) each use 120 trees and `max_features='sqrt'`.
Five independent 25,000-row redraws use seeds 42, 143, 244, 345 and 446.
The 100,000-row stage uses seed 42 only. Rows are sampled before removing
non-finite values and negative numerical descriptors; no replacement rows are added.
The targets therefore have different retained counts. The 100k run is a
within-database sample-size check, not an independent or external test.

Parent-linker mappings were available for 33 of 58 identifiers, supported by
automated graph-consistency checks; 21 have a second reference and 12 have a single
reference. This is not expert confirmation of all framework-bound linker identities.
The common mapped population retains 5,977/24,985 valid uptake rows in the seed-42
25k draw and 23,711/99,945 in the 100k draw. Only eight of eleven topologies remain;
rht, tbo and the have no mapped rows. All mapped representations are compared on the
same retained population. Fingerprint results are conditional on this mapping,
parent representation, population selection and fixed model configuration.

**Table S19.** Paired pooled LOTO MAE changes. Each contrast is the first representation
minus the second; negative values favour the first. The 25k columns show mean and
sample SD across five paired redraws. The 100k column is one paired result. Uptake
MAE is in mmol g⁻¹; log-selectivity MAE is on the log₁₀ scale.

| Population | Contrast | Target | Model | 25k ΔMAE, mean ± SD | 100k ΔMAE |
| --- | --- | --- | --- | --- | --- |
| Full | I-B | Uptake | RF | -0.008929 ± 0.005451 | -0.005575 |
| Full | I-B | Uptake | ET | -0.023178 ± 0.008336 | -0.033010 |
| Full | I-B | Log-selectivity | RF | -0.005480 ± 0.000609 | -0.007276 |
| Full | I-B | Log-selectivity | ET | -0.006210 ± 0.002166 | -0.007255 |
| Mapped | T-I | Uptake | RF | +0.149485 ± 0.015124 | +0.164800 |
| Mapped | T-I | Uptake | ET | +0.160250 ± 0.014027 | +0.153138 |
| Mapped | T-I | Log-selectivity | RF | +0.039205 ± 0.001760 | +0.042820 |
| Mapped | T-I | Log-selectivity | ET | +0.054883 ± 0.003967 | +0.055937 |

All five 25k contrasts are negative for full-population I−B and positive for
mapped-population T−I, for both targets and ensembles. Pooled directions do not
imply uniform per-topology effects or superiority over G. Resolving each contrast
topology by topology (five-redraw mean of the paired difference) makes the reversals
explicit. For uptake/RF, I−B is negative in 7 of 11 topologies and positive in bcu,
fof, tbo and the, with mean differences from −0.023 to +0.035 mmol g⁻¹; 10 of 11
topologies keep the same sign in at least four of the five redraws. On the mapped
subset, T−I is positive on average for uptake/RF yet negative in 3 of 8 topologies,
and the largest single-topology change is +0.277 mmol g⁻¹. A pooled mean therefore
summarises opposing local effects; the signs and counts for all four
contrast–target–model combinations are in
`outputs/finish_20261023/per_topology_direction_counts.csv`. For example, five-redraw
uptake/RF mean MAE is 0.2510 for I and 0.2400 for G. Numerical inputs already contain
chemical information, and dimensionality changes the feature-sampling opportunities
of the trees. The experiment does not isolate a causal effect of chemical information.
*Source data:* `experiment12/{full,mapped_common}/pooled_metrics.csv`,
`experiment12/paper_tables/primary_LOTO_paired_directions.csv` and
`experiment12/paper_tables/size_sensitivity_LOTO_paired.csv`, all beneath the
follow-up archive.

### SI-I.2 Constituent novelty and numerical support (experiment 2)

The primary coarse key is the ordered tuple (metal-node ID, linker-1 ID, linker-2 ID),
without functional group. For each training/test split, CU denotes missing constituent
identity; C0 has a seen coarse key; C1 has an unseen key but a seen metal-node ID and
seen ordered linker pair; C2 has an unseen pair but a seen metal-node ID and both
role-specific linker IDs seen separately; C3 has at least one unseen metal-node or
role-specific linker ID. Sorted-pair and union-vocabulary alternatives are sensitivity
analyses. The role distinction follows the source columns and does not establish a
chemical site interpretation.

Numerical support uses nearest-neighbour Euclidean distance in the eight-descriptor
space, standardized using training medians and IQRs; zero IQR falls back to training
population SD and then one. A test row is outside at a distance above the training
leave-one-out nearest-neighbour 95th percentile. This differs from the mean/SD
definition in SI-I.4.

**Table S20.** Constituent novelty in the seed-42, full-population uptake I/RF LOTO
audit. The classes partition all retained predictions in these two samples. MAE is
in mmol g⁻¹. Class numbering is a support taxonomy, not an ordinal risk scale.

| Class | 25k n | 25k MAE | 100k n | 100k MAE |
| --- | --- | --- | --- | --- |
| C0 | 9,336 | 0.170034 | 38,490 | 0.178178 |
| C1 | 4,624 | 0.268939 | 17,550 | 0.287387 |
| C2 | 3,653 | 0.243445 | 14,441 | 0.262556 |
| C3 | 7,372 | 0.349379 | 29,464 | 0.341106 |

Among unseen-key predictions, C1+C2 account for 52.9% at 25k and 52.1% at 100k.
Thus exact-key loss often consists of recombining previously observed constituents.
Approximately 96.9% of C3 rows involve unseen database metal-node identifiers; these
are not unseen chemical elements. Linker-only unseen subclasses can be very sparse
and do not justify general conclusions about new linker chemistry. In this specified
I/RF audit, C1 MAE exceeds C2 at both sizes. At 25k, within each C0–C3 class,
numerically outside rows have lower MAE than inside rows; target and topology
composition can confound these comparisons. Neither pattern validates a monotonic
novelty-to-error rule.
*Source data:* `experiment12/full/novelty_error_metrics.csv`,
`experiment12/full/C3_subtype_metrics.csv` and
`experiment12/paper_tables/main_novelty_numerical_cross.csv`.

### SI-I.3 CoRE structural-feasibility pilot (experiment 3)

The source is CoRE MOF 2019 ASR v1.1.0, Zenodo DOI
`10.5281/zenodo.3370144`. Forty CIFs were randomly sampled with seed 20261022.
The topology sub-pilot uses a preselected ten-structure subset. Counts below refer
to successful parsing or returned technical objects, not identification accuracy.

**Table S21.** Completed technical steps in the CoRE pilot.

| Pilot measure | Returned / completed |
| --- | --- |
| CIFs in source archive | 12,020 |
| Sampled CIFs parsed | 40 / 40 |
| Metal + organic candidates with bond cuts | 38 / 40 |
| Topology pilot: net key | 9 / 10 |
| Topology pilot: named-net match | 6 / 10 |
| Independent expert checks completed | 0 / 40 |

The five independent-check fields (node, linker, periodic boundary, interpenetration,
and source-publication checks) remain pending for all 40 records. A retry returning
fragments does not resolve missing molecular identifiers. No database-wide composition
support audit, comparable full-library topology annotation or external
adsorption-prediction validation was completed. The zero completed expert checks
must not be interpreted as zero correct structures.
*Source data:* `experiment3/summary.json`, `experiment3/topology_pilot.json`,
`experiment3/expert_review_sheet.csv` and `experiment3/sample_manifest.json`.

### SI-I.4 Descriptive fold-level diagnostics (experiment 4)

This analysis attaches support summaries to the archived original LOTO fold MAE;
it does not fit a risk model. The 66 fold records span six samples but reuse the same
eleven topology groups. They are not 66 independent groups. Table S22 uses only
the seed-42 100k sample. Its eight numerical descriptors are standardized by
training means and population SDs (zero SD becomes one). The far threshold is the
95th percentile of leave-one-out nearest-neighbour distances for a deterministic
sample of up to 5,000 training rows. Linker novelty uses the union of both training
slot vocabularies. These metrics must not be identified with the role-specific
classes or median/IQR distances of SI-I.2.

**Table S22.** Spearman correlations between topology-level diagnostics and absolute
LOTO MAE. The second column uses eleven topologies; the last excludes the five-row
rht group and retains ten topologies and 99,995 test rows. These are descriptive
associations, without a claim of calibrated risk prediction.

| Diagnostic | ρ, 11 topologies | ρ, 10 topologies (n ≥ 100) |
| --- | --- | --- |
| Exact-key mismatch | +0.515932 | +0.589077 |
| Any building-unit novelty | +0.603023 | +0.609723 |
| Metal-node novelty | +0.575642 | +0.547898 |
| Linker novelty (union) | +0.193649 | +0.189934 |
| Mean numerical distance | -0.781818 | -0.818182 |
| Numerically far fraction | -0.763636 | -0.818182 |
| Novel and numerically far | +0.295573 | +0.231363 |

Seven topologies have complete exact-key mismatch, yet their MAE ranges from
0.115300 to 1.260980 mmol g⁻¹. The original joint strata, cut at the eleven-group
medians of unit novelty (0.1742241556) and far fraction (0.2340862423), contain
1/5/5/0 topologies in the low/low, low/high, high/low and high/high cells.
These sparse strata do not establish complementary predictive value. Negative
distance correlations do not imply that greater distance improves predictions.
Absolute archived fold MAE is not a matched random-to-LOTO performance loss. Fourteen
correlations are reported here (seven diagnostics by two fold sets); no multiplicity correction
is applied and they are exploratory.
*Source data:* `experiment4/fold_diagnostics.csv`,
`experiment4/joint_group_strata.csv` and `experiment4/analysis_metadata.json`.

### SI-I.5 Fixed-size partner replacement (experiment 5)

Within the seed-42 50k sample, the held-out test topology, nonpartner background,
training size and partner fraction are fixed. Shared and nonshared partner rows
are matched without replacement using outcome-blind greedy matching in the
standardized eight-descriptor space, using the mean and population SD of the non-target-topology candidate pool (Euclidean caliper 0.5).
The nbo direction uses 1,000 matched partner pairs and 4,000 background rows; pcu
uses 726 pairs and 4,000 background rows. Partner doses are 0, 25, 50, 75 and 100%
shared rows. These percentages describe the partner subset, not complete test
coverage: even 100% gives only 78.75% and 15.08% exact-key coverage of the respective
historical test sets.

Five seeds (42, 143, 244, 345, 446) vary the model and replacement order, with the same fixed pools and
test rows. At the endpoints, training membership is fixed across seeds.
The RF has 120 trees and default `max_features=1.0`.
Paired intervals below describe conditional learner variability, not uncertainty
over new test sets, material populations or independent chemistry pairs.
A separate paired sensitivity removes rows with negative numerical descriptors;
only its two endpoints were refitted.

**Table S23.** Endpoint uptake MAE (mmol g⁻¹), averaged across five learner seeds.
ΔMAE is 100% minus 0% shared partner rows. Intervals are paired t intervals
(df = 4), conditional on the fixed pools.

| Row policy | Test | MAE, 0% | MAE, 100% | ΔMAE | Paired 95% t interval |
| --- | --- | --- | --- | --- | --- |
| Historical rows | nbo | 0.149276 | 0.158659 | +0.009384 | [+0.004902, +0.013865] |
| Historical rows | pcu | 0.233135 | 0.239102 | +0.005967 | [+0.004025, +0.007909] |
| Negative descriptors removed | nbo | 0.151084 | 0.158125 | +0.007041 | [+0.001748, +0.012335] |
| Negative descriptors removed | pcu | 0.232815 | 0.238754 | +0.005939 | [+0.003533, +0.008346] |

Both directions show increased endpoint MAE with shared partners in this local
replacement design, including after descriptor cleaning. This does not demonstrate
a causal disadvantage of shared chemistry. Residual differences remain in
multivariate descriptor, metal-node, functional-group and target distributions:
maximum metal total-variation distances are 0.095 and 0.171, and functional-group
distances 0.340 and 0.416. Approximate numerical matching does not eliminate them.
The cleaned test/training counts are nbo 7,663/4,991 and pcu 31,682/4,719.
For the original deletion arms, the paired e−g interval includes zero on pcu
(SI-C.4), so arm e's improvement over a does not establish a composition-specific
advantage over same-count random partner deletion.
*Source data:* `experiment5/curve_metrics.csv`,
`experiment5/paired_endpoints.csv`, `experiment5/cleaned_endpoint_metrics.csv`,
`experiment5/cleaned_endpoint_summary.csv` and
`experiment5/matching_quality_summary.csv`.

### SI-I.6 Fixed-candidate-pool retrospective screening (experiment 6)

One fitted model scores each entire frozen candidate pool, using the cleaned
experiment-5 endpoint training sets. Candidate pools were examined in earlier
analyses; this is a retrospective simulation, not an untouched external test.
Categorical encoding is fitted on training rows only. G/B/I have the definitions
above, and topology is not an input. RF and ET each have 120 trees with default
`max_features=1.0`, unlike the `'sqrt'` setting in experiment 1.
Absolute differences across these experiments cannot be attributed to representation
alone. Five learner seeds (42, 143, 244, 345, 446) keep training and candidate membership fixed.

Budgets are 1%, 5%, 10% and 20%, with k = ceil(N × fraction).
True and predicted ties are resolved by the original source-row ID. Recovery is
the overlap between predicted and oracle top-k sets divided by k. Regret is oracle
mean uptake minus selected mean uptake; both refer to the same candidates.
All G/B/I × RF/ET × 0/100%-shared arms and budgets are retained in the archived CSV.

**Table S24.** RF at the prespecified illustrative 5% budget: all twelve
direction × partner-support × representation arms. Recovery SD reflects learner
randomness only. Selected mean and regret are in mmol g⁻¹. The nbo candidate/training
counts are 7,663/4,991; pcu counts are 31,682/4,719.

| Test | Shared partners | Representation | k | Recovery (%), mean ± SD | Selected mean | Regret |
| --- | --- | --- | --- | --- | --- | --- |
| nbo | 0% | G | 384 | 51.20 ± 0.93 | 0.433540 | 0.105741 |
| nbo | 0% | B | 384 | 49.95 ± 0.56 | 0.429056 | 0.110225 |
| nbo | 0% | I | 384 | 53.44 ± 0.56 | 0.437661 | 0.101621 |
| nbo | 100% | G | 384 | 51.30 ± 0.88 | 0.431347 | 0.107934 |
| nbo | 100% | B | 384 | 50.05 ± 0.65 | 0.428988 | 0.110294 |
| nbo | 100% | I | 384 | 51.61 ± 1.16 | 0.433466 | 0.105815 |
| pcu | 0% | G | 1585 | 20.08 ± 0.27 | 1.028581 | 1.012150 |
| pcu | 0% | B | 1585 | 20.96 ± 0.24 | 1.041194 | 0.999537 |
| pcu | 0% | I | 1585 | 15.81 ± 0.57 | 0.903649 | 1.137082 |
| pcu | 100% | G | 1585 | 20.06 ± 0.42 | 1.029769 | 1.010962 |
| pcu | 100% | B | 1585 | 21.35 ± 0.50 | 1.054243 | 0.986488 |
| pcu | 100% | I | 1585 | 17.05 ± 0.62 | 0.933868 | 1.106863 |

The identity representation increases recovery relative to G for nbo but decreases
it for pcu under nonshared partners. Within I, shared-partner replacement changes
recovery in opposite directions across the two tests. Results also depend on budget
and model. They establish local ranking sensitivity, not a universally preferable
representation, reliable benefit of shared composition, prospective screening
performance or a validated synthesis budget.
*Source data:* `experiment6/screening_metrics.csv`,
`experiment6/screening_summary.csv`, `experiment6/pool_audit.csv`,
`experiment6/frozen_config.json` and `experiment6/candidates_*.csv`.

---

## SI-I.7 Feature-subsampling sensitivity (`max_features=1.0`)

The representation comparisons above use `max_features='sqrt'`. Feature dimension changes how
many descriptors a tree can sample at each split, so the same contrast was re-run with
`max_features=1.0` and every other setting held fixed: 120 trees, the same sampling seed, the
same targets and preprocessing, and the archived `split.npz` files reused row for row (no new
sample, no new split). The setting was written into `frozen_config.json` before any fit, and
all seeds, targets and folds are reported regardless of direction. Runs are archived under
`outputs/sensitivity_mf1/mapped/` and `outputs/sensitivity_mf1/full/`; the analysis is
`scripts/analyze_mf_sensitivity.py`, which asserts identical `raw_row_id` vectors on both
sides before computing any difference.

**Table S25.** Mapped-subset I versus T contrast under the two feature-subsampling settings
(5 seeds × 25,000-row draws; pooled leave-one-topology-out MAE in mmol g⁻¹ for uptake and on
the log₁₀ scale for selectivity). "Gap" is T − I; "seeds > 0" counts the five redraws in which
the gap is positive.

| Target | Model | MAE I (sqrt → 1.0) | MAE T (sqrt → 1.0) | Gap (sqrt → 1.0) | Seeds > 0 (sqrt / 1.0) |
| --- | --- | --- | --- | --- | --- |
| Uptake | RF | 0.3131 → 0.3144 | 0.4626 → 0.4365 | +0.1495 → **+0.1221** | 5/5 / 5/5 |
| Uptake | ET | 0.3269 → 0.3391 | 0.4872 → 0.4643 | +0.1603 → **+0.1252** | 5/5 / 5/5 |
| Log-selectivity | RF | 0.1443 → 0.1450 | 0.1835 → 0.1462 | +0.0392 → **+0.0011** | 5/5 / 3/5 |
| Log-selectivity | ET | 0.1488 → 0.1476 | 0.2036 → 0.1590 | +0.0549 → **+0.0114** | 5/5 / 5/5 |

*Source data:* `outputs/sensitivity_mf1/mapped/mf1_pooled.csv`, `mf1_paired.csv`.

**Table S25b.** Full-sample B versus I contrast under the two settings (5 seeds; RF; pooled
LOTO MAE). "Gap" is I − B; "seeds < 0" counts redraws in which I is better.

| Target | MAE B (sqrt → 1.0) | MAE I (sqrt → 1.0) | Gap (sqrt → 1.0) | Seeds < 0 (sqrt / 1.0) |
| --- | --- | --- | --- | --- |
| Uptake | 0.2599 → 0.2532 | 0.2510 → 0.2499 | −0.0089 → **−0.0034** | 5/5 / 5/5 |
| Log-selectivity | 0.1340 → 0.1382 | 0.1285 → 0.1321 | −0.0055 → **−0.0061** | 5/5 / 5/5 |

*Source data:* `outputs/sensitivity_mf1/full/mf1_pooled.csv`, `mf1_paired.csv`.

Three consequences. (i) For uptake, the T−I direction is unchanged: T is worse than I in all
five redraws under both settings, and the gap is 18% (RF) and 22% (ET) smaller under the
full-feature setting. (ii) For log-selectivity, the T−I gap nearly disappears under the
full-feature setting (97% smaller for RF, where only 3 of 5 redraws remain positive; 79% for
ET). (iii) Neither representation is uniformly better per topology: under the full-feature
setting the uptake/RF gap is concentrated in pcu (+0.209) and etb (+0.132), with fof (−0.102)
and nbo (−0.023) still favouring T, and pts changing sign from +0.010 to −0.038.

For the full-sample B/I contrast the direction is preserved in all five redraws for both
targets: I remains better than B under the full-feature setting, by a smaller margin for
uptake (−0.0034 against −0.0089) and by the same margin for log-selectivity (−0.0061 against
−0.0055). The representation statements in the main text therefore hold under both settings,
with the uptake magnitude explicitly configuration-dependent.

The two settings support different strengths of statement. "T did not improve pooled
leave-one-topology-out MAE" holds for uptake and is the sentence used in the main text; for
log-selectivity the correct statement is that the difference becomes negligible under the
full-feature setting, not that fingerprints are neutral or harmful there. Random-split results
are unchanged in direction (both representations improve slightly under 1.0), so the
sensitivity bears on the topology-held-out contrast, not on the random-split level.

**Limits.** The full-feature tier covers the full 25,000-row samples for the B/I contrast with
RF only: ExtraTrees requires about 150 s per fit at this setting, which exceeded the available
compute, so no ET row exists for that tier (the mapped tier covers both learners). The mapped
tier is 5,977 of 24,985 uptake rows and eight of eleven topologies, so it cannot represent the
full sample. Neither tier is a hyperparameter search: one prespecified setting is compared with
the archived one.

---

## SI figures

**Figure S1.** SHAP attribution aggregated by feature family under a random split and under
topology hold-out. The attribution is dominated by structure-derived scalar descriptors in
both regimes (82.3% / 85.1%). The original model assigns 17.7% and 14.9% of total
mean absolute SHAP attribution to its encoded identity block. These shares do not
measure the information content of chemistry or the benefit of adding linker
identities (SI-I.1).
Left panel: mean |SHAP| per fold; right panel: the same numbers as a share of total
attribution. n_folds = 5 (random) and 11 (topology hold-out). *Source data:*
`outputs/fig5_shap_family_final.csv`.

**Figure S2.** Centred partial dependence of the four leading structure-derived descriptors.
The model is a random forest fitted to the **full analysis sample** of 24,985 rows (25,000
sampled with seed 42, minus the 15 rows that carry a negative descriptor value); it is not a
training fold of the random split, and the figure footer says so. Partial dependence was
calculated by replacing the selected descriptor with each grid value and averaging
predictions over a fixed 4,000-row background; the grid of each descriptor is restricted to
the observed valid domain, and every grid point is asserted to lie inside it
(`outputs/pdp_geometry_grids.csv` records the range and the per-field invalid count).
Curves are centred on the offset archived in the meta table, 0.519784 mmol/g, which is the
mean of the per-tree root values (mean of tree means) rather than an explicit
mean[f(background)] over the 4,000 background rows. Shading is ±1.96 background standard
errors of the prediction mean, conditional on the fitted model; it is not a confidence
interval for a causal effect, and a marginal substitution can produce feature combinations
that lie outside the joint distribution, so the curves do not identify a causal response.
PDP and SHAP describe different quantities. Descriptors, largest range first: void fraction
(0.79), largest included sphere diameter (0.33), void volume (0.22), volume (0.22). *Source
data:* `outputs/pdp_geometry_curves.csv`, `outputs/pdp_geometry_meta.csv`,
`outputs/pdp_geometry_grids.csv`; producer `prepare_figS2_pdp_data.py`.

**Figure S3.** Within-topology against cross-topology R² per topology for the eight
structure-derived descriptors (25,000 samples). Each row is one topology, ordered by
test-set size; the connector is the within-to-cross gap and a topology's n is printed with
its label. Median within 0.655 against median cross 0.219; cross-topology R² is negative for
2 of the 6 topologies (etb −4.27, nbo −0.31). *Source data:*
`outputs/within_vs_cross_final.csv`.

**Figure S4.** Across-seed dispersion by aggregation rule. (a) Pooled, median and macro on
the same run with the zero line. (b) The across-seed dispersion of each rule (sd / |mean|):
pooled 4.15%, median 11.03%, macro 91.53%. The figure reports the three rules' dispersion;
it does not attribute the difference to any single cause. *Source data:*
`outputs/multi_seed_uptake25k_fix.csv`.

**Figure S5.** Leave-one-topology-out R² for each topology under four aggregation rules.
(a) The four aggregates of one run (pooled +0.381, weighted −0.059, macro −0.541, median
+0.278). (b) The eleven folds behind them, ordered by R², with the pooled, macro and median
values marked by dashed rules (weighted sits near zero and is shown only in panel a); a
fold's test-set size is printed with its name. Excluding pcu, weighted is −0.678 and macro
−0.625; pooled without the pcu scoring fold is +0.4629. *Source data:*
`outputs/metrics_audit.csv`, `outputs/loto_per_topology_final.csv`.

**Figure S6.** Confounding across ARC-MOF's source sub-libraries (n ≥ 200). (a)
Single-topology chemistry fraction at coarse and fine granularity with bootstrap error bars
(10 resamples); each sub-library's n is printed under its label. (b) Each source's confound
degree above its own within-source permutation null (coarse, common support, B = 1,000)
against H(T); the excess runs +2.6 pp (DB15) to +37.3 pp (DB12), DB6 excluded. The positive
association is sensitive to DB12: Pearson r changes from +0.67 to −0.08 when that source is
excluded. With seven non-degenerate sources, this does not establish a stable association.
*Source data:* `outputs/source_confound_granularity.csv`,
`outputs/common_support/null_topology_cardinality.csv`.

**Figure S7.** The S_g curve: does a topology's unseen-chemistry rate order its hold-out
cost? (a) Each held-out topology is one point: horizontal = S_miss (fraction of that
topology's structures with no chemical counterpart in training), vertical = that fold's
held-out R²; panel (a) is restricted to the ten topologies with n_test ≥ 100, while panel
(b) shows all eleven. Seven points sit at S_miss = 1.000 and still span R² from −2.55 (etb)
to +0.47 (bcu); the exploratory association was not statistically established
(Pearson r = +0.10, p = 0.78; Spearman ρ = +0.28,
p = 0.44). (b) Target variation within held-out topologies (sd(y) from 0.11 to 0.88 mmol/g);
the pcu fold accounts for 63.4% of the scored test rows. *Source data:*
`outputs/s_g_curve.csv`.

**Figure S8.** Bounded support audit in ARC-MOF (moved here from the main figures; the
compact summary remains Table 3). **(a)** Single-topology composition fraction at four
combinations (coarse/fine × all/non-singleton): 99.3, 97.3, 99.7 and 98.2.
**(b)** Leave-one-source-out sensitivity: removing DB0 moves the fraction to 98.57–98.96,
any other single source to 99.22–99.84. **(c)** Observed versus within-source
topology-permutation null on the common support set, with the degenerate single-topology
source (DB6) excluded; the permutation SD is below 0.5%, so the horizontal error bars are
not visually distinguishable. *Source data:* `outputs/confound_arcmof.csv`,
`outputs/confound_arcmof_excl_derived.csv`,
`outputs/common_support/null_topology_cardinality.csv`.
