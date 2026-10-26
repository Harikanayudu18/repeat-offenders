# DRAFT — review and personalise before publishing (not published)
## What I Built
Repeat Offenders: students re-read old papers trying to remember which topics keep returning. This tool does the counting, then tests honestly whether a tabular foundation model (TabPFN) beats simple baselines at ranking topics for an unseen year. [Add your own story here.]
## Demo
[Render URL — fill in only after a real deployment] · repo: [link]
## How It Works
Local Gemma (Ollama) suggests topic labels; a human accepts them. Deterministic Python builds leakage-free features, runs an expanding-window backtest (last year frozen) and computes top-K marks coverage. TabPFN scores topics when installed and licensed.
## Evaluation (synthetic data, from `eval/results/synthetic_summary.md`; TabPFN NOT run)
Dev folds (2019–2023), mean coverage K=8: naive frequency 50.4%, recency 45.4%, logistic regression 50.3%, random 30.2%. Frozen 2024 holdout K=8: 62.5% / 57.5% / 60.5% / 31.1%. [Replace with your TabPFN run: `--version v2`.]
## What Worked
Rankings beat random by a clear margin on synthetic data; the pipeline, leakage tests and fallbacks work.
## What Failed
TabPFN was unavailable in my build environment, so there is no TabPFN number yet. Baselines were within fold noise of each other (5 dev folds). Only CSV import is implemented. [Add real failures.]
## Why Open Innovation Matters
Topic assignment uses a local open-weight Gemma model; TabPFN performs the tabular prediction when configured; private paper content stays on the user's machine in local mode; the deterministic analysis is useful with no model. After install and model download, inference needs no hosted API (downloads still need internet).
## What It Saves
[Not measured. Only report a time saving after timing a manual counting exercise.]
## Privacy and Local Inference
See docs/PRIVACY.md.
## Prize Categories
TabPFN (adapter + backtest), Gemma (local suggestions, human review), Render (synthetic static demo), Sentry (opt-in, sanitised stage tracing — [add real traces]). No prize is guaranteed.
## Limitations
Few examination years ⇒ no statistical certainty; scores are uncalibrated recurrence scores; see README limitations.
## What I Learned
[Your reflections.]
