# Level 3 - representative rerun from raw data

`run_subset.py` rebuilds one representative experiment end to end and compares it with the
archive:

* sample: 25,000 rows drawn with `random_state=42` from the public hMOF CSV;
* filtering: non-finite or negative numerical descriptors dropped, target must be finite
  (this reproduces the experiment-12 sampling rule; no rows are refilled);
* splits: `KFold(5, shuffle=True, random_state=42)`;
* representations: G (eight numerical descriptors), B (+ metal-node and functional-group
  one-hot), I (+ the two role-specific linker one-hot blocks);
* learner: random forest, 120 trees, `max_features='sqrt'`, `random_state=42`, `n_jobs=1`;
* output: pooled MAE/R² per representation, compared with
  `../outputs/followup_20261023/experiment12/full/pooled_metrics.csv`.

```text
python level3_rerun/run_subset.py --csv /path/to/all_MOFs_screening_data.csv
```

The input is not redistributed. Fetch it from the record in `../config/config.json` and
check the SHA256 first. The run takes about three minutes on one CPU core.

## What level 3 does not do

One subset is not the paper. It does not rebuild leave-one-topology-out, the fixed-test-set
intervention arms, the ARC-MOF audit, the CoRE pilot or the screening experiments, and it
does not reproduce the 100,000-row stage. Claiming "the full paper was retrained" on the
strength of this script would be wrong.
