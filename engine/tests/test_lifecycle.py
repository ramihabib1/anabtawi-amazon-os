"""WRITE-01 / WRITE-05 lifecycle classifier contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 02 (`habibos.lifecycle`) implements against.
Until `habibos.lifecycle` exists they FAIL RED on the missing import — that is the intended
Wave 0 state (06-VALIDATION.md), not a failure to fix.

What the contract pins:
  - the dryRun PROCEED gate (status=="VALIDATED" && validation.valid && issues==[]) returns
    a typed Proceed; any invalid/issue dryRun returns a Refusal carrying the issue message
    verbatim (WRITE-01);
  - the actions_get status classification: COMPLETED -> done, in-flight statuses -> in_flight,
    ERROR/BLOCKED -> Refusal surfacing ActionExecutionErrorResult.message verbatim, an unmodeled
    status -> Refusal(code="unknown_status") (never assumed-terminal, never infinite-polled),
    and the ACTION_TERMINAL enum is pinned verbatim (WRITE-05 / SC-4);
  - a DataDoe export status is NOT treated as an action confirmation (reconcile guard);
  - each classify op wraps logged_call with no seller UUID in the log (TRUST-03 / hard rule 5).

Fixtures load with the test_tacos.py repo-root idiom; the log test mirrors test_logging.py.
The seller UUID prefix is assembled at runtime (never written literally) so test_env.py's
source scan stays clean.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import structlog

from habibos import datadoe, lifecycle
from habibos import logging as hlog
from habibos.result import PollOutcome, Proceed, Refusal

# Assembled, never written literally — mirrors test_env.py / test_logging.py secret hygiene.
SELLER_UUID_PREFIX = "5692" + "b95f"

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point logging at a temp JSONL file (mirror of test_logging.py:34-43)."""
    path = tmp_path / "external-calls.jsonl"
    monkeypatch.setattr(hlog, "LOG_PATH", path)
    hlog.configure()
    yield path
    structlog.reset_defaults()


def test_action_terminal_enum_pinned() -> None:
    """SC-4 / WRITE-05: ACTION_TERMINAL matches the verified enum verbatim."""
    assert datadoe.ACTION_TERMINAL == {
        "COMPLETED",
        "PARTIALLY_COMPLETED",
        "COMPLETED_WITH_ISSUES",
        "ERROR",
        "CANCELED",
        "BLOCKED_NO_TOKENS",
        "BLOCKED_INVALID_INPUT",
    }
    # The roadmap's assumed names must NOT appear (no FAILED; CANCELED is one-L).
    assert "FAILED" not in datadoe.ACTION_TERMINAL
    assert "CANCELLED" not in datadoe.ACTION_TERMINAL


def test_dryrun_validated_proceeds() -> None:
    """WRITE-01: a clean dryRun classifies PROCEED (typed Proceed, never a bare True)."""
    result = lifecycle.classify_dryrun(_load("dryrun_validated.json"))
    assert isinstance(result, Proceed)
    assert result.action_type == "AMAZON_ADS_CAMPAIGNS_UPDATE"


def test_dryrun_invalid_stops() -> None:
    """WRITE-01: an invalid dryRun STOPS, surfacing the issue message verbatim."""
    payload = _load("dryrun_invalid.json")
    expected_msg = payload["validation"]["issues"][0]["message"]
    result = lifecycle.classify_dryrun(payload)
    assert isinstance(result, Refusal)
    assert result.code == "dryrun_invalid"
    assert expected_msg in result.reason


def test_poll_terminal_classification() -> None:
    """WRITE-05: COMPLETED -> done; in-flight statuses -> in_flight."""
    done = lifecycle.classify_poll(_load("actions_get_completed.json"))
    assert isinstance(done, PollOutcome)
    assert done.state == "done"

    for status in ("PENDING", "IN_PROGRESS", "WAITING_EXTERNAL_PROCESSING"):
        outcome = lifecycle.classify_poll(
            {"actionId": "ACT-X", "type": "AMAZON_ADS_CAMPAIGNS_UPDATE", "status": status}
        )
        assert isinstance(outcome, PollOutcome)
        assert outcome.state == "in_flight"


def test_poll_error_surfaces_message() -> None:
    """WRITE-05: an ERROR action surfaces ActionExecutionErrorResult.message verbatim."""
    payload = _load("actions_get_error.json")
    expected_msg = payload["error"]["message"]
    result = lifecycle.classify_poll(payload)
    assert isinstance(result, Refusal)
    assert result.code == "action_error"
    assert expected_msg in result.reason


def test_unknown_status_refuses() -> None:
    """WRITE-05: an unmodeled status -> Refusal, never assumed-terminal nor infinite-polled."""
    result = lifecycle.classify_poll(
        {"actionId": "ACT-X", "type": "AMAZON_ADS_CAMPAIGNS_UPDATE", "status": "WAT_IS_THIS"}
    )
    assert isinstance(result, Refusal)
    assert result.code == "unknown_status"


def test_export_not_confirmation() -> None:
    """Reconcile guard: a DataDoe EXPORT status is never treated as an action confirmation.

    The export TERMINAL set ({COMPLETED, FAILED}) and the action lifecycle are distinct. A
    DataDoe export-only sentinel ("FAILED", which is NOT in the action enum) must classify as
    an unknown action status (a Refusal), never silently as a terminal action confirmation.
    """
    result = lifecycle.classify_poll(
        {"actionId": "ACT-X", "type": "AMAZON_ADS_CAMPAIGNS_UPDATE", "status": "FAILED"}
    )
    assert isinstance(result, Refusal)
    assert result.code == "unknown_status"
    # "FAILED" is an export terminal, NOT an action terminal — the two sets stay separate.
    assert "FAILED" not in datadoe.ACTION_TERMINAL
    assert "FAILED" in datadoe.TERMINAL


def test_ops_logged_no_secret(log_file: Path) -> None:
    """TRUST-03 / hard rule 5: a classify op emits one .start+.end and leaks no UUID."""
    result = lifecycle.classify_poll_logged(_load("actions_get_completed.json"))
    assert isinstance(result, PollOutcome)

    lines = [ln for ln in log_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    events = [json.loads(ln) for ln in lines]
    assert len(events) == 2, f"expected one .start + one .end, got {len(events)}"
    assert events[0]["event"].endswith(".start")
    assert events[1]["event"].endswith(".end")
    assert SELLER_UUID_PREFIX not in log_file.read_text(encoding="utf-8")
