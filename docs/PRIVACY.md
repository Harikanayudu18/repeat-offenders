# Privacy

## Local mode

- The backend binds to `127.0.0.1` and CORS is limited to the local frontend.
- Data is stored in a local SQLite file (`RO_DB`).
- Gemma runs through local Ollama.
- There is no telemetry by default.

## Public demo

The hosted demo serves a synthetic fixture only: no uploads and no backend.

## Sentry (only if `SENTRY_DSN` is set)

Sentry receives stage names, durations, row and feature counts, fallback flags and error categories. A `before_send` hook strips requests, extras, breadcrumbs, exception messages and local variables. Tests assert that question text never appears in logs or sanitised events.
