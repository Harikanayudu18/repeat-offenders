"""Opt-in Sentry tracing. Only numeric/bool/allow-listed short attrs are ever recorded. No text, prompts or filenames."""
import logging
import os
import time
from contextlib import contextmanager

log = logging.getLogger("ro.trace")
SAFE_STR_KEYS = {"model_family", "model", "error_category", "status", "stage", "fold"}
ENABLED = False
_sdk = None


def safe_attrs(attrs: dict) -> dict:
    return {k: v for k, v in attrs.items()
            if isinstance(v, (bool, int, float)) or (k in SAFE_STR_KEYS and isinstance(v, str) and len(v) < 64)}


def sanitize_event(event, hint=None):
    """before_send hook (also used by tests): strips request/user/extra/breadcrumbs, exception messages, locals, free text."""
    for k in ("request", "user", "extra", "breadcrumbs", "contexts", "message", "logentry"):
        event.pop(k, None)
    for ex in (event.get("exception") or {}).get("values", []):
        ex["value"] = ex.get("type", "error")
        for fr in (ex.get("stacktrace") or {}).get("frames", []):
            fr.pop("vars", None); fr.pop("context_line", None); fr.pop("pre_context", None); fr.pop("post_context", None)
    for sp in event.get("spans", []) or []:
        sp["data"] = safe_attrs(sp.get("data") or {})
        sp["description"] = sp.get("op")
    return event


def init() -> bool:
    global ENABLED, _sdk
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=dsn, send_default_pii=False, traces_sample_rate=1.0, max_request_body_size="never",
                        before_send=sanitize_event, before_send_transaction=sanitize_event)
        _sdk, ENABLED = sentry_sdk, True
    except Exception as e:  # sentry unavailable must never break the app
        log.warning("sentry unavailable: %s", type(e).__name__)
    return ENABLED


@contextmanager
def span(stage: str, **attrs):
    """Named stage span. Yields a dict; add safe metadata (row_count, feature_count, fallback, retries...)."""
    info = dict(attrs); t0 = time.perf_counter()
    sp = _sdk.start_span(op=stage) if ENABLED else None
    try:
        yield info
        info.setdefault("status", "ok")
    except Exception as e:
        info["status"], info["error_category"] = "error", type(e).__name__
        raise
    finally:
        info["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        s = safe_attrs(info)
        if sp is not None:
            for k, v in s.items(): sp.set_data(k, v)
            sp.finish()
        log.info("stage=%s %s", stage, s)
