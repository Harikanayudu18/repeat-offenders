# Synthetic evaluation (SYNTHETIC DATA: demonstrates workflow, not real exam performance)

- Version `v1`; fingerprint `f5e74678afeaa8d0...`; years [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]; final holdout 2024
- TabPFN status: `{"available": false, "code": "package_missing", "message": "tabpfn package not installed (pip install tabpfn; see docs/MODEL_SETUP.md)"}`
- Coverage = held-out marks in top-K topics / total held-out marks.

## Dev folds (5, years [2019, 2020, 2021, 2022, 2023]) mean coverage (± std across folds)

| model | folds | K=3 | K=5 | K=8 |
|---|---|---|---|---|
| naive_frequency | 5/5 | 23.6% ± 9.2% | 28.5% ± 13.1% | 50.4% ± 16.0% |
| recency_weighted | 5/5 | 25.1% ± 9.3% | 29.6% ± 11.1% | 45.4% ± 11.2% |
| logistic_regression | 5/5 | 19.6% ± 5.6% | 34.4% ± 9.1% | 50.3% ± 13.7% |
| tabpfn | 0/5 | not run | not run | not run |
| random | 5/5 | 10.4% ± 0.4% | 16.8% ± 0.8% | 30.2% ± 2.2% |

## Frozen final holdout: 2024 (80 marks)

| model | K=3 | K=5 | K=8 |
|---|---|---|---|
| naive_frequency | 30.0% | 40.0% | 62.5% |
| recency_weighted | 30.0% | 47.5% | 57.5% |
| logistic_regression | 30.0% | 47.5% | 60.5% |
| tabpfn | unavailable (package_missing) |
| random | 9.4% | 16.8% | 31.1% |

## Comparison (dev folds, mean coverage)
- K=3: TabPFN vs naive_frequency: **not run** (TabPFN unavailable)
- K=3: TabPFN vs recency_weighted: **not run** (TabPFN unavailable)
- K=3: TabPFN vs logistic_regression: **not run** (TabPFN unavailable)
- K=3: TabPFN vs random: **not run** (TabPFN unavailable)
- K=5: TabPFN vs naive_frequency: **not run** (TabPFN unavailable)
- K=5: TabPFN vs recency_weighted: **not run** (TabPFN unavailable)
- K=5: TabPFN vs logistic_regression: **not run** (TabPFN unavailable)
- K=5: TabPFN vs random: **not run** (TabPFN unavailable)
- K=8: TabPFN vs naive_frequency: **not run** (TabPFN unavailable)
- K=8: TabPFN vs recency_weighted: **not run** (TabPFN unavailable)
- K=8: TabPFN vs logistic_regression: **not run** (TabPFN unavailable)
- K=8: TabPFN vs random: **not run** (TabPFN unavailable)

## Limitations
- Only 5 dev folds and one final year: differences are not statistically reliable.
- Synthetic data; real papers will differ. A baseline winning is a valid outcome.