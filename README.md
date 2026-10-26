# Repeat Offenders

**Study the pattern, not the prediction.**

Repeat Offenders is a local-first study planner. It imports past exam papers, counts which syllabus topics keep coming back, tests honestly whether a tabular foundation model ([TabPFN](https://github.com/PriorLabs/TabPFN)) beats simple baselines at ranking topics for an unseen year, and builds a deterministic revision plan that never skips a unit.

> **Status:** v0.1.0, early stage. It is a single-user local tool, not production-hardened. All bundled data and results are **synthetic**.

## What it does

- **Imports papers** from CSV, XLSX, DOCX, TXT and text-based PDF files.
- **Tags questions with human review.** A local Gemma model (via Ollama) can suggest topics; nothing counts until a person accepts it.
- **Analyses recurrence** with a recurrence table, topic-by-year heatmap and unit-level marks.
- **Backtests honestly** with an expanding-window rolling backtest and a frozen final-year holdout, scored by top-K marks coverage.
- **Builds a study plan** that fits a time budget and guarantees a minimum slot for every unit (CSV export and print view).

## What it does not do

It does not predict future questions, find leaked papers, perform OCR, or guarantee outcomes. Scores are recurrence scores, not calibrated probabilities. A baseline beating TabPFN is a valid, reported result.

## Architecture

```
frontend/   React + Vite + TypeScript UI (Setup, Import, Review, Analytics, Backtest, Study plan, Privacy)
backend/    FastAPI + SQLite API
  services/   features, forecasting, backtesting, planning, imports, synthetic data
  adapters/   Gemma (Ollama), TabPFN, optional Sentry tracing
scripts/    start scripts, evaluation runner, demo-fixture generator
eval/       synthetic evaluation outputs and the frozen-holdout lock
docs/       model setup, privacy, observability, deployment
tests/      unit and integration tests
```

Deterministic Python is the source of truth. Models only suggest labels (Gemma) or score topics (TabPFN); if a model is missing, the UI shows it as **unavailable** and never substitutes another result.

## Quick start

Requirements: Python 3.10+ and Node 20+.

```bash
git clone https://github.com/<your-username>/repeat-offenders.git
cd repeat-offenders

pip install -r requirements.txt -r requirements-dev.txt
cd frontend && npm install && cd ..

./scripts/start_unix.sh          # Windows: scripts\start_windows.ps1
# open http://localhost:5173
```

The API binds to `127.0.0.1:8000`; interactive API docs are at `/docs`. `make install`, `make test`, `make lint` and `make run` are available as shortcuts.

### Input format

- **CSV / XLSX** with the columns `year, marks, question_text`, plus optional `question_number` and `topic`.
- **TXT / DOCX / text-based PDF** with a `YEAR 2021` line followed by questions such as `1. Explain ... [5 marks]`.
- Scanned PDFs are rejected with guidance, because OCR is not supported.

### Docker (local, single container)

```bash
docker compose up --build
# open http://127.0.0.1:8000  (UI and API on one port, bound to localhost only)
```

Ollama stays on the host and is reached through `OLLAMA_ENDPOINT`. The app has **no authentication**; never expose it to a network.

## Optional models

Both models are optional. Everything deterministic works without them. See [docs/MODEL_SETUP.md](docs/MODEL_SETUP.md).

| Model | Role | Setup |
| --- | --- | --- |
| Gemma (Ollama) | Suggests topic labels for review | `ollama pull gemma3:4b`, then set `OLLAMA_MODEL` |
| TabPFN | Scores topics in the backtest | Accept the licence at [platform.priorlabs.ai](https://platform.priorlabs.ai), then `pip install tabpfn` |

## Configuration

Copy `.env.example` to `.env`. Main variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `RO_DB` | `./repeat_offenders.db` | SQLite file location |
| `OLLAMA_ENDPOINT` | `http://127.0.0.1:11434` | Local Ollama server |
| `OLLAMA_MODEL` | `gemma3:4b` | Model used for topic suggestions |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed CORS origin |
| `RO_MAX_UPLOAD_BYTES` | `2000000` | Upload size limit |
| `RO_RATE_LIMIT_PER_MIN` | `600` | Per-IP request limit |
| `RO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Trusted `Host` headers |
| `SENTRY_DSN` | empty (off) | Opt-in, sanitised tracing ([docs](docs/OBSERVABILITY.md)) |

## Evaluation

```bash
python scripts/run_evaluation.py --version v1
```

The runner uses synthetic data and writes to `eval/results/`. Development folds run every time; the frozen final-year holdout runs **once per version** and is stored in `eval/final_lock.json`. Bump `--version` only when metric or feature definitions change deliberately.

Current synthetic results (mean top-K marks coverage, K=8; **TabPFN was not run** because the package is not installed in the reference environment):

| Model | Dev folds (2019-2023) | Frozen holdout (2024) |
| --- | --- | --- |
| Naive frequency | 50.4% | 62.5% |
| Recency weighted | 45.4% | 57.5% |
| Logistic regression | 50.3% | 60.5% |
| TabPFN | not run | not run |
| Random | 30.2% | 31.1% |

With only five development folds and one holdout year, differences between the baselines are within noise. Full tables are in [`eval/results/synthetic_summary.md`](eval/results/synthetic_summary.md).

## Testing

```bash
python -m pytest -q                                   # backend
ruff check .                                          # lint
cd frontend && npm run typecheck && npm test          # frontend
python scripts/verify_installation.py                 # optional: check real Gemma/TabPFN installs
```

CI runs all of the above on every push and pull request.

## Public demo

A static, read-only demo runs on [Render](https://render.com) from a synthetic fixture (`frontend/public/demo-fixture.json`, regenerated with `python scripts/generate_demo_fixture.py`). It has no backend and no uploads. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Privacy and security

- Runs on your machine: the backend binds to `127.0.0.1`, data lives in a local SQLite file, and Gemma runs through local Ollama.
- No telemetry by default. Optional Sentry tracing records only stage names, durations and counts, never question text. See [docs/PRIVACY.md](docs/PRIVACY.md).
- Hardening: trusted-host check, security headers and CSP, per-IP rate limit, upload size and archive-expansion limits, log redaction, and a non-root container with a health check. See [SECURITY.md](SECURITY.md).

## Known limitations

- No authentication; local use only.
- No database migrations; the schema is created automatically.
- OCR is not supported; scanned PDFs are rejected.
- Gemma and TabPFN have not been exercised against real installs in the reference environment.
- Few examination years means no statistical certainty. Treat comparisons as indicative only.
- The study plan is deterministic; model-written plan wording is not implemented.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Application source is released under the [MIT License](LICENSE). Model weights (Gemma, TabPFN) have their own licences and are neither bundled nor covered; see [NOTICE](NOTICE).
