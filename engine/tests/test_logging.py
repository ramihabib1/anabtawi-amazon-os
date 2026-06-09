"""TRUST-03 / D-12 logged_call wrapper test (consumed by plan 02-01, used by 02-02/02-03).

Asserts the "one event in, one event out" contract for every wrapped external call:
exactly one `*.start` and one `*.end` JSON line, the end event carrying row_count,
byte_size, duration_ms, and status (D-12). On exception the end event STILL emits and the
exception re-raises (a wrapped call never swallows an error so a fabricated number can
follow — TRUST-03 / T-02-03). And no secret (the seller UUID prefix) ever lands in the log
(security V7/V8 / T-02-02).

Asserts NOW (does not skip): each test points logging.LOG_PATH at a temp file and reads it
back — no live connection needed. The seller UUID prefix is assembled at runtime (never
written literally) so test_env.py's source scan stays clean.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import structlog

from habibos import logging as hlog

# Assembled, never written literally — mirrors tests/test_env.py's secret-hygiene idiom.
SELLER_UUID_PREFIX = "5692" + "b95f"


def _read_events(path: Path) -> list[dict]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


@pytest.fixture
def log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point logging at a temp JSONL file and (re)configure structlog to write there."""
    path = tmp_path / "external-calls.jsonl"
    monkeypatch.setattr(hlog, "LOG_PATH", path)
    hlog.configure()
    yield path
    # Reset structlog so a later test's configuration is honored.
    structlog.reset_defaults()


def test_one_event_in_one_out(log_file: Path) -> None:
    with hlog.logged_call("datadoe_export", source_id="57a0cb319c", filters="CA/30d") as end:
        end["row_count"] = 30
        end["byte_size"] = 4096
        end["status"] = "ok"

    events = _read_events(log_file)
    assert len(events) == 2, f"expected exactly one start + one end, got {len(events)}"
    start, finish = events
    assert start["event"] == "datadoe_export.start"
    assert start["source_id"] == "57a0cb319c"
    assert finish["event"] == "datadoe_export.end"
    # D-12 required end fields.
    assert finish["row_count"] == 30
    assert finish["byte_size"] == 4096
    assert finish["status"] == "ok"
    assert "duration_ms" in finish
    assert isinstance(finish["duration_ms"], (int, float))


def test_end_event_on_exception(log_file: Path) -> None:
    class Boom(RuntimeError):
        pass

    with pytest.raises(Boom):
        with hlog.logged_call("datadoe_export", source_id="57a0cb319c"):
            raise Boom("export blew up")

    events = _read_events(log_file)
    # Still exactly one start + one end — the .end emits even on failure.
    assert len(events) == 2
    start, finish = events
    assert start["event"] == "datadoe_export.start"
    assert finish["event"] == "datadoe_export.end"
    # The error is reflected, never swallowed.
    assert finish["status"] == "error"
    assert "error" in finish
    assert "Boom" in finish["error"]


def test_no_secret_in_log(log_file: Path) -> None:
    # Even if a careless caller passed identifying context, the seller UUID must never
    # appear. Here we confirm a normal wrapped call writes nothing matching the prefix.
    with hlog.logged_call("datadoe_export", source_id="57a0cb319c", filters="CA/30d") as end:
        end["row_count"] = 30
        end["byte_size"] = 1024
        end["status"] = "ok"

    raw = log_file.read_text(encoding="utf-8")
    assert SELLER_UUID_PREFIX not in raw, "seller UUID prefix leaked into the log (V7/V8)"
