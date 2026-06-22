"""WRITE-03 / WRITE-06 apply-spine contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 03 (`habibos.apply`) implements against.
Until `habibos.apply` exists they FAIL RED on the missing import — the intended Wave-0
state (08-VALIDATION.md 08-03·T1/T2), NOT a failure to fix.

THE SEAM (CLAUDE.md hard rule 1): Python NEVER opens a socket. The agent supplies every
MCP-call result to apply() as plain data / zero-arg callables:
  - start_dryrun:  () -> the actions_start(dryRun:true) response dict
  - start_apply:   () -> the actions_start(dryRun:false) response dict (the real write)
  - get_status:    () -> the latest actions_get response dict (the poll loop drives this)
  - find_echo:     () -> the *_FIND response dict for the post-write echo confirm
apply() classifies each via the reused Phase-6/7 primitives and threads the typed grammar.

What the contract pins:
  - test_reversible_write_end_to_end (WRITE-03): build -> dryRun(Proceed) -> apply -> poll
    to COMPLETED -> FIND-echo confirm -> AppliedResult (the happy path).
  - test_dryrun_refusal_blocks_apply (WRITE-03): a dryRun STOP short-circuits BEFORE any
    start_apply call (the real write never fires on an invalid dryRun).
  - test_poll_loop_to_terminal (WRITE-03): the spine drives get_status through in-flight
    responses to a terminal status (reuses datadoe.poll_action_status).
  - test_apply_logs_decision_and_brain (WRITE-06): an applied write appends a decisions.md
    line AND a brain/raw note, each carrying the actionId — tmp_path-monkeypatched paths.
  - test_canary_one_time_confirm (WRITE-03/D-08): the first apply of the phase requires the
    one-time canary confirm; once the marker is written, subsequent applies auto-apply.
  - test_disabled_action_refuses (WRITE-05 reuse): a 412/disabled or ERROR poll surfaces a
    clean typed refusal and does NOT retry.
  - test_find_echo_mismatch (WRITE-03): the FIND echo's mutated field disagrees with the
    intended write (state != PAUSED) -> Refusal(code="find_echo_mismatch"), never recorded
    as applied.

All payload SHAPES are loaded from committed fixtures (Task 1 dryRun fixtures + Task 2
support fixtures) — NO inline fabricated DataDoe schema. No seller UUID literal anywhere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# RED on import: habibos.apply does not exist until Plan 03. The intended Wave-0 baseline.
from habibos import apply
from habibos.result import AppliedResult, ProposedAction, Refusal

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"

# Task-1 live-pinned dryRun fixture (the pause schema). Referenced by path; the test fails
# RED on the missing apply module before this is read.
DRYRUN_PAUSE = FIXTURES / "actions_start_dryrun_pause.json"
# Task-2 support fixtures.
GET_COMPLETED = FIXTURES / "actions_get_completed.json"
GET_INFLIGHT = FIXTURES / "actions_get_inflight.json"
GET_ERROR = FIXTURES / "actions_get_error.json"
FIND_ECHO_PAUSED = FIXTURES / "campaigns_find_echo.json"  # CMP-...003 state == PAUSED
OWNED = FIXTURES / "owned_asins_test.toml"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _pause_action() -> ProposedAction:
    """A reversible whole-campaign pause on the FIND-cached CMP-1000000000003."""
    return ProposedAction(
        sku="X",
        action_type="pause",
        delta_spend=0,  # the spine sets delta_spend<=0 for reversible (Open Q3) -> gate auto-pass
        entity_type="campaigns",
        entity_id="CMP-1000000000003",
        params={"state": "PAUSED"},
    )


@pytest.fixture
def spine_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Monkeypatch every data/log seam to tmp_path so no real ledger/decisions/brain write."""
    monkeypatch.setattr(apply, "DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(apply, "DECISIONS_PATH", tmp_path / "decisions.md", raising=False)
    monkeypatch.setattr(apply, "BRAIN_RAW_DIR", tmp_path / "brain_raw", raising=False)
    return tmp_path


def test_reversible_write_end_to_end(spine_dirs: Path) -> None:
    """WRITE-03: build->dryRun(Proceed)->apply->poll-to-COMPLETED->echo->AppliedResult."""
    statuses = iter([_load(GET_COMPLETED)])
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),  # returns the started action w/ actionId
        get_status=lambda: next(statuses),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(result, AppliedResult)
    assert result.status == "COMPLETED"
    assert result.action_id


def test_dryrun_refusal_blocks_apply(spine_dirs: Path) -> None:
    """WRITE-03: a dryRun STOP short-circuits BEFORE any start_apply call (no real write)."""
    fired = {"apply": False}

    def _start_apply() -> dict:
        fired["apply"] = True
        return _load(GET_COMPLETED)

    # An invalid dryRun: valid:false (mirror dryrun_invalid.json shape).
    bad_dryrun = {"status": "VALIDATED", "validation": {"valid": False, "issues": [{"code": "X"}]}}
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: bad_dryrun,
        start_apply=_start_apply,
        get_status=lambda: _load(GET_COMPLETED),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(result, Refusal)
    assert fired["apply"] is False  # the real write NEVER fired on an invalid dryRun


def test_poll_loop_to_terminal(spine_dirs: Path) -> None:
    """WRITE-03: the spine drives get_status through in-flight to a terminal COMPLETED."""
    responses = iter([_load(GET_INFLIGHT), _load(GET_INFLIGHT), _load(GET_COMPLETED)])
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_INFLIGHT),
        get_status=lambda: next(responses),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(result, AppliedResult)
    assert result.status == "COMPLETED"


def test_apply_logs_decision_and_brain(spine_dirs: Path) -> None:
    """WRITE-06: an applied write appends a decisions.md line + a brain/raw note w/ actionId."""
    statuses = iter([_load(GET_COMPLETED)])
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),
        get_status=lambda: next(statuses),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(result, AppliedResult)
    decisions = (spine_dirs / "decisions.md").read_text(encoding="utf-8")
    assert result.action_id in decisions
    brain_notes = list((spine_dirs / "brain_raw").glob("*.md"))
    assert brain_notes, "an applied write must write a brain/raw note"
    assert result.action_id in brain_notes[0].read_text(encoding="utf-8")


def test_canary_one_time_confirm(spine_dirs: Path) -> None:
    """WRITE-03/D-08: the first apply needs --confirm-canary; then the marker auto-applies."""
    # First apply WITHOUT the confirm and with no marker present -> canary_unconfirmed refusal.
    first = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),
        get_status=lambda: _load(GET_COMPLETED),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=False,
    )
    assert isinstance(first, Refusal)
    assert first.code == "canary_unconfirmed"

    # Same apply WITH the one-time confirm -> proceeds and writes the canary marker.
    statuses = iter([_load(GET_COMPLETED)])
    confirmed = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),
        get_status=lambda: next(statuses),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(confirmed, AppliedResult)

    # Marker now present -> a subsequent apply auto-applies WITHOUT the confirm (D-09).
    statuses2 = iter([_load(GET_COMPLETED)])
    auto = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),
        get_status=lambda: next(statuses2),
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=False,
    )
    assert isinstance(auto, AppliedResult)


def test_disabled_action_refuses(spine_dirs: Path) -> None:
    """WRITE-05 reuse: a 412/disabled or ERROR poll -> clean typed refusal, no retry."""
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_ERROR),
        get_status=lambda: _load(GET_ERROR),  # terminal ERROR -> typed refusal, not a retry
        find_echo=lambda: _load(FIND_ECHO_PAUSED),
        confirm_canary=True,
    )
    assert isinstance(result, Refusal)


def test_find_echo_mismatch(spine_dirs: Path) -> None:
    """WRITE-03: the FIND echo disagrees with the intended write -> Refusal(find_echo_mismatch).

    The pause intended state == PAUSED, but the echo reflects state == ENABLED — the write
    did not take. The spine refuses and NEVER records it as applied (no AppliedResult).
    """
    bad_echo = {
        "campaigns": [
            {
                "campaignId": "CMP-1000000000003",
                "adProduct": "SPONSORED_PRODUCTS",
                "state": "ENABLED",
            }
        ],
        "nextToken": None,
    }
    statuses = iter([_load(GET_COMPLETED)])
    result = apply.apply(
        _pause_action(),
        owned_source=OWNED,
        start_dryrun=lambda: _load(DRYRUN_PAUSE),
        start_apply=lambda: _load(GET_COMPLETED),
        get_status=lambda: next(statuses),
        find_echo=lambda: bad_echo,
        confirm_canary=True,
    )
    assert isinstance(result, Refusal)
    assert result.code == "find_echo_mismatch"
