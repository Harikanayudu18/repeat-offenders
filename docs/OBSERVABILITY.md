# Observability

Tracing is **opt-in** and uses Sentry. It is implemented in `backend/adapters/sentry_tracing.py`.

## Traced stages

`import_parse`, `topic_tag_suggestion`, `topic_tag_validation`, `feature_generation`, `historical_evaluation` (baselines plus TabPFN) and `study_plan_generation`.

## Recorded attributes

Duration, row and feature counts, model family and name, fallback flag, error category and retries.

## Never recorded

Question text, syllabus content, prompts and filenames.

## Enable / disable

- Enable: `pip install sentry-sdk`, set `SENTRY_DSN` in `.env`, restart the backend.
- Disable: unset `SENTRY_DSN`.

A `before_send` hook strips requests, extras, breadcrumbs, exception messages and local variables. Verify the sanitisation locally with:

```bash
pytest tests/integration/test_api.py::test_sentry_sanitization
```

No token or cost data is recorded, because inference is local.
