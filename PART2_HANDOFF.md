# Part 2 handoff (paste this + the original spec into the other account, upload this repo zip)
Part 1 is DONE and tested (9 tests pass): backend/services/{common,features,forecasting,backtesting,planning,synthetic},
backend/adapters/{gemma,tabpfn_adapter}.py, scripts/run_evaluation.py. Do NOT rewrite them; import them.

Part 2 TODO (keep it lean, no web browsing):
1. FastAPI (backend/main.py): SQLite via SQLAlchemy (subjects, units, topics, papers, questions, topic_assignments).
   Endpoints: health, system/models (use TabPFNAdapter.status + GemmaAdapter.check), CSV import preview/confirm,
   question tagging (Gemma suggest -> human review), analytics (build_features), backtests (run_backtest), study-plans (build_plan).
   Bind 127.0.0.1, CORS to localhost only, 5 MB upload limit, safe error envelope. Never log question text.
2. Frontend (Vite+React+TS) in frontend/: pages = Setup, Import, Review, Analytics(heatmap), Backtest, Study Plan, Privacy.
   VITE_DEMO_MODE=true => read-only, loads public/demo-fixture.json (generate it from scripts + eval/results/synthetic_results.json).
3. render.yaml static site (rootDir frontend, `npm ci && npm run build`, publish dist, VITE_DEMO_MODE=true).
4. Sentry (optional, DSN opt-in): span helper in backend/adapters/sentry_tracing.py, before_send scrubbing text/prompts.
5. Docs: README, MODEL_SETUP (Ollama + gemma3:1b, TabPFN licence at platform.priorlabs.ai), PRIVACY, DEV_SUBMISSION_DRAFT
   (honest, use eval/results/*, no fabricated numbers; TabPFN not run unless really run).
6. Run `pip install tabpfn` locally with accepted licence and re-run `python scripts/run_evaluation.py --version v2` for real TabPFN numbers.
