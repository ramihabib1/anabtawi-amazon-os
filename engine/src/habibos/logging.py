"""Structured "one event in, one event out" wrapper for every external call (TRUST-03 / D-12).

Every DataDoe (and, later, Supabase) operation is wrapped in logged_call, which emits
exactly one `<op>.start` event and one `<op>.end` event as JSON lines to a local file
(the interim decision_ledger until Phase 3.5). The .end event carries the D-12 fields
(row_count, byte_size, duration_ms, status). On exception the .end event STILL emits with
an error status and the exception RE-RAISES — a wrapped call never swallows an error so a
fabricated number can follow (TRUST-03 / T-02-03).

Security (V7/V8 / T-02-02): callers MUST NOT pass the seller UUID or any secret into the
start/end fields; nothing here ever logs a secret of its own.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog

# Repo-root-relative runtime log path (RESEARCH §Pattern 3). logs/ is gitignored — this is
# runtime output, not a tracked artifact. Tests monkeypatch this to a temp file, so
# configure() must read it at call time (not capture it at import).
LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "external-calls.jsonl"


def configure() -> None:
    """Configure structlog to write JSON lines to LOG_PATH (creating its dir)."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.WriteLoggerFactory(file=LOG_PATH.open("a", encoding="utf-8")),
    )


@contextmanager
def logged_call(op: str, **start_fields: object) -> Iterator[dict]:
    """Wrap an external operation: one `<op>.start` in, one `<op>.end` out.

    Yields a mutable dict the caller fills with end fields (row_count, byte_size, status).
    On exception the .end event still emits with status="error" and the error repr, then
    the exception re-raises (never swallowed). NEVER pass a secret into start_fields.
    """
    log = structlog.get_logger()
    t0 = time.perf_counter()
    log.info(f"{op}.start", **start_fields)  # one event IN
    status = "ok"
    end_fields: dict = {}
    try:
        yield end_fields  # caller fills row_count, byte_size, status
    except Exception as exc:  # noqa: BLE001 - record + re-raise, never swallow (TRUST-03)
        status = "error"
        end_fields["error"] = repr(exc)
        raise
    finally:
        log.info(
            f"{op}.end",  # one event OUT
            status=end_fields.pop("status", status),
            duration_ms=round((time.perf_counter() - t0) * 1000, 1),
            **end_fields,
        )
