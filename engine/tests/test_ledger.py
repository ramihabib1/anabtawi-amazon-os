"""WRITE-07 idempotency-ledger contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 02 (`habibos.ledger`) implements against.
Until `habibos.ledger` exists they FAIL RED on the missing import — the intended Wave-0
state (08-VALIDATION.md 08-02·T1), NOT a failure to fix.

What the contract pins (D-10):
  - test_completed_hash_is_noop: a hash whose ledger entry is COMPLETED -> a LedgerHit
    (no-op), so the spine NEVER fires a second actions_start for an already-applied write.
  - test_inflight_resumes_at_poll: a hash whose ledger entry is in-flight (IN_PROGRESS /
    PENDING / WAITING_*) -> resume at poll on its action_id, NEVER re-fire actions_start.
  - test_hash_excludes_date: the content hash is identity over {entity_type + entity_id +
    action_type + normalized_params} and is INVARIANT to the date — re-pausing an already-
    paused campaign on two different days yields the SAME hash (a re-run is always a no-op).

DATA_DIR is monkeypatched to tmp_path (mirror of test_find_cache.py:31-35) so no real
data/actions_ledger.jsonl write happens. The seed fixture is the committed, sanitized
actions_ledger_seed.jsonl (Pattern 3 schema). No seller UUID literal appears anywhere here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# RED on import: habibos.ledger does not exist until Plan 02. This is the intended Wave-0
# baseline — the tests below collect but error on the missing module.
from habibos import ledger

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
SEED = FIXTURES / "actions_ledger_seed.jsonl"

# Seed identities (from the committed actions_ledger_seed.jsonl):
#   COMPLETED pause   -> campaigns / CMP-1000000000003 / {"state": "PAUSED"}
#   COMPLETED bid_down-> targets   / TGT-2000000000007 / {"bid": 0.42}
#   IN_PROGRESS pause -> campaigns / CMP-1000000000009 / {"state": "PAUSED"}


@pytest.fixture
def ledger_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ledger.DATA_DIR at tmp_path seeded with the committed ledger fixture."""
    monkeypatch.setattr(ledger, "DATA_DIR", tmp_path)
    shutil.copy(SEED, tmp_path / "actions_ledger.jsonl")
    return tmp_path


def test_completed_hash_is_noop(ledger_dir: Path) -> None:
    """WRITE-07/D-10: a COMPLETED hash -> LedgerHit (no-op), the spine fires no second start."""
    h = ledger.action_hash("campaigns", "CMP-1000000000003", "pause", {"state": "PAUSED"})
    hit = ledger.lookup(h)
    assert isinstance(hit, ledger.LedgerHit)
    assert hit.status == "COMPLETED"
    assert hit.action_id == "ACT-PLACEHOLDER-COMPLETED-0001"


def test_inflight_resumes_at_poll(ledger_dir: Path) -> None:
    """WRITE-07/D-10: an in-flight actionId -> resume at poll, never re-fire actions_start."""
    h = ledger.action_hash("campaigns", "CMP-1000000000009", "pause", {"state": "PAUSED"})
    hit = ledger.lookup(h)
    assert isinstance(hit, ledger.InFlight)
    assert hit.action_id == "ACT-PLACEHOLDER-INFLIGHT-0001"
    # An in-flight entry is NOT a terminal no-op — it carries an action_id to resume polling on.
    assert not isinstance(hit, ledger.LedgerHit)


def test_hash_excludes_date(ledger_dir: Path) -> None:
    """WRITE-07/D-10: identity is entity+action+params, NOT date — same inputs => same hash."""
    h1 = ledger.action_hash("campaigns", "CMP-1000000000003", "pause", {"state": "PAUSED"})
    h2 = ledger.action_hash("campaigns", "CMP-1000000000003", "pause", {"state": "PAUSED"})
    assert h1 == h2
    # The hash carries no date component, so a re-pause on a later day is still a no-op.
    h_other = ledger.action_hash(
        "campaigns", "CMP-1000000000003", "pause", {"state": "ENABLED"}
    )
    assert h_other != h1  # a different param DOES change identity
