# Contributing

Thanks for your interest in Repeat Offenders. Bug reports, fixes and documentation improvements are welcome.

## Development setup

```bash
git clone https://github.com/<your-username>/repeat-offenders.git
cd repeat-offenders
make install        # Python deps + frontend deps
make test           # backend tests
make lint           # ruff
make frontend-check # typecheck, frontend tests, production build
```

Python 3.10+ and Node 20+ are required.

## Ground rules

- **Never commit real exam papers, personal data or secrets.** Test data must be synthetic.
- **Keep deterministic code the source of truth.** Models (Gemma, TabPFN) may suggest or score, but a model that is not installed must show as "unavailable", never be silently replaced by a substitute.
- **Do not weaken the evaluation protocol.** Features for a forecast year may only use earlier years, and the final holdout runs once per `--version`. Bump the version only when metric or feature definitions change deliberately.
- Do not log question text. Tests cover log redaction and Sentry sanitisation; keep them passing.
- Add or update tests with every behaviour change.

## Pull requests

1. Branch from `main` and keep the change focused.
2. Make sure `make lint`, `make test` and `make frontend-check` pass.
3. Describe what changed and why in the PR description.
