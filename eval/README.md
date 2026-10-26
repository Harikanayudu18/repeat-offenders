# Evaluation

```bash
python scripts/run_evaluation.py --version vN
```

Outputs are written to `eval/results/` and use **synthetic data only**:

- `synthetic_results.json`: full machine-readable results
- `synthetic_per_fold.csv`: per-fold, per-model, per-K coverage
- `synthetic_summary.md`: human-readable summary

`final_lock.json` stores the frozen final-year result per (version, data fingerprint), so the holdout is evaluated once. Bump `--version` only when metric or feature definitions change deliberately.
