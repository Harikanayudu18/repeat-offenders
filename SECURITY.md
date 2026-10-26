# Security policy

Repeat Offenders is a **local, single-user tool with no authentication**. Run it on `127.0.0.1` only and do not expose it to a network.

## Reporting a vulnerability

Please report security issues privately through GitHub's *Security > Report a vulnerability* feature on this repository rather than opening a public issue. Include steps to reproduce and the affected version.

## Built-in hardening

Trusted-host check, security headers with a strict CSP, per-IP rate limiting, upload size and archive-expansion limits, in-memory parsing only (uploads are never written to disk), log redaction, and a non-root container. Details are in the [README](README.md) and [docs/PRIVACY.md](docs/PRIVACY.md).
