# Level 2 - prediction review (no model is fitted)

`verify_predictions.py` reads the row-level predictions shipped in `../outputs/`:

| file | rows | content |
|---|---|---|
| `predictions_arms_seed{42,143,244,345,446}.csv` | ~236k each | one row per test material × arm (`nbo:a`, `pcu:b`, …) × row policy, with `raw_row_index`, `y_true`, `y_pred` |
| `predictions_screening_seed{42,143,244,345,446}.csv` | 100k each | one row per material × strategy (random / topology) × row policy |

It recomputes, from those rows only:

* MAE for the intervention arms and compares it with `sensitivity_five_seeds_summary.csv`
  (both the historical `_h` and the cleaned `_c` columns);
* top-k overlap at 1%, 5% and 10% for the screening strategies and compares it with
  `screening_utility_seed*.csv` (k is taken from the archived table, i.e. 250 / 1,250 / 2,500
  of the 25,000 scored rows).

The archived metrics score **every** test row; the `legal` flag in the predictions marks the
separate input-validity sensitivity and is *not* used to subset here.

```text
python level2_predictions/verify_predictions.py
```

Exit code 0 means every recomputed value matched within 1e-6.

## What level 2 cannot do

The slim archive does **not** contain:

* the experiment-12 representation/novelty predictions (`prediction_*.npz`), so Table S19,
  S20 and the per-topology deltas cannot be recomputed here;
* the full score vector of the fixed candidate pool (only the selected materials and the
  summary metrics are archived), so Table S24 cannot be recomputed from predictions;
* the LOTO per-fold predictions behind Tables S8/S9 (their metrics are archived, not the rows).

Those are level-1 checks (archived metrics) or require the original experiment directories.
Do not describe this level as "full prediction review".
