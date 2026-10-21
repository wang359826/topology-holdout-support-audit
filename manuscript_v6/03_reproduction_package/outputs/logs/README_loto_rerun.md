# LOTO re-run: what these files do and do not show

Three different things are easy to confuse here. They are kept separate on purpose.

## 1. Failed / incomplete attempts (not evidence of anything)

| File | What it is |
|---|---|
| `loto_100k_attempt1_FAILED_nopipe.log` | The first attempt inside a confined sandbox. It dies with `PermissionError: [WinError 5]` when joblib starts its worker pool, because the sandbox denies the named pipes that `multiprocessing` uses. No model was fitted to completion; this log proves nothing about results. |
| `loto_100k_attempt2_PARTIAL_killed.log` | A retry with `--n-jobs 1`. It shows one fold (`acs`) and then stops because the run was cancelled. It is a truncated record, not a result. |

Both document an **environment** limitation, not a numerical outcome. They are named so they
cannot be mistaken for a successful run, and they are **not** evidence that training
succeeded.

## 2. Evidence scope

The author reports completing the 100k and five-seed 25k LOTO runs on 2026-10-20. The
resulting per-fold and aggregate CSVs are archived; the successful training console output
was not retained. The archived failed and interrupted attempts are not evidence of successful
completion. The read-only verifier checks internal arithmetic consistency and agreement with
historical results. **It does not independently establish the provenance of the training
outputs.**

The runs that produced the CSVs were executed from a normal PowerShell session with
`--n-jobs -1` (joblib parallelism works outside the confined sandbox). In a sandbox that
denies named pipes, pass `--n-jobs 1`; results are identical because each forest has a fixed
`random_state`, but the 100,000-row run then takes roughly ten minutes per fold.

## 3. Archive verification (reproducible, but bounded)

```text
python scripts/loto_full_metrics.py verify --outdir outputs
```

Scope, stated narrowly so it is not over-read. The verifier **reconstructs `weighted`,
`macro` and `median` R², valid-fold counts and covered sample counts from the per-fold
tables**. **Pooled R² is compared with the historical archive**; it is not recomputed from
per-sample predictions, and per-fold MAE is not recomputed from predictions either.

Within that scope it checks:

- key uniqueness (11 rows for 100k; 55 for 25k) and positive fold sizes;
- `RMSE² × n_test == SSE`;
- for valid folds, `R2 == 1 − SSE/SST`;
- `MAE ≤ RMSE` on every fold, and non-negative MAE / RMSE / SSE / SST;
- that the `valid_R2` flag matches its own definition (`n_test ≥ 2` and `SST > 0`) rather
  than being taken on trust;
- that each check **accumulates** into the verdict instead of overwriting an earlier failure;
- `weighted` / `macro` / `median` / valid-fold count / covered rows rebuilt from the per-fold
  tables and compared with the aggregate CSVs;
- the 100k per-fold R² and `n_test` against `loto_per_topology_final.csv`;
- the four 100k aggregates against `metrics_audit.csv`;
- the five-seed pooled/macro/median/valid-fold counts against `multi_seed_uptake25k_fix.csv`.

The corrected verifier passed on the archived data and rejected deliberately corrupted copies
(a 100k MAE or R² set to 999, a 25k `weighted` set to 999, a valid fold flagged invalid, a
negative MAE). That both-directions test is shipped as `scripts/verify_regression.py`; re-run
it with `python scripts/verify_regression.py`. It works on scratch copies and never modifies
the archive. Logs: `loto_verify_20261020.log` (archive check) and
`loto_verify_regression_20261020.log` (corrupted-input test).

Anyone receiving the package can run those checks without the raw database.
