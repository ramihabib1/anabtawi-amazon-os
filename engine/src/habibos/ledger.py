"""Content-hash idempotency ledger over data/actions_ledger.jsonl (WRITE-07 / D-10).

THE GUARANTEE (D-10, T-08-04/T-08-06): re-running an already-applied reversible write is a
no-op, and an in-flight write resumes at poll — it NEVER fires a second `actions_start`. The
mechanism is a content hash over an action's IDENTITY — `{entity_type + entity_id +
action_type + normalized_params}` — and the append-only `data/actions_ledger.jsonl` store
that records each fired write's hash + status + actionId.

WHY THE HASH EXCLUDES DATE (load-bearing, T-08-06): if the date were part of the identity,
re-pausing an already-paused campaign tomorrow would hash differently and fire a SECOND
`actions_start` — exactly the double-apply this ledger exists to prevent. So `action_hash`
is INVARIANT to time: the same entity + action + normalized params always yields the same
hash, on any day. `test_hash_excludes_date` pins this.

PARAM NORMALIZATION (load-bearing — the identity of a write). Two payloads that mean the
same mutation MUST hash the same, so params are canonicalized before hashing per the
08-SCHEMA-PIN normalized-params map:
  - pause           -> {"state": "PAUSED"}                       keyed by campaignId
  - negative add    -> {"keyword": <lc text>, "matchType": "EXACT", "negative": true}
  - bid-down        -> {"bid": <new bid, 2dp>}                   keyed by targetId
Normalization rules applied here (see `_normalize_params`):
  - string values are lowercased + stripped (so "  PAUSED " and "paused" collide) EXCEPT
    enum/literal fields whose casing is wire-significant (state, matchType) are UPPERCASED
    to the canonical literal;
  - numeric bids are rounded to 2 dp (CAD cents — 0.250000001 and 0.25 are the same bid);
  - dict keys are sorted (json.dumps sort_keys) so key order never changes identity.
The normalization is documented here because it DEFINES which two writes are "the same".

THE SEAM (CLAUDE.md hard rule 1): this module imports no HTTP/socket library and opens no
connection. It only reads/writes the LOCAL append-only jsonl. The `actions_start` /
`actions_get` MCP calls are made by the agent, NOT by Python. Records carry only
entity/action/actionId/marketplace — NEVER the seller UUID or any secret (hard rule 5,
T-08-09). The ledger is append-only: `append` opens "a" and writes one JSON object per line;
it NEVER edits a past line.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

# src/habibos/ledger.py is two levels below the repo root; the ledger lives at <repo>/data/
# (mirrors find_cache.DATA_DIR — parents[2]/"data"). Tests monkeypatch this to tmp_path so
# no real data/actions_ledger.jsonl write happens.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

LEDGER_NAME = "actions_ledger.jsonl"

# Status values that mean a fired write has NOT yet reached a terminal state — a hash match
# on one of these resumes at poll on its action_id, it does not re-fire the start (D-10).
_IN_FLIGHT_STATUSES = frozenset({"PENDING", "IN_PROGRESS", "WAITING", "WAITING_FOR_RETRY"})

# Enum/literal param fields whose casing is wire-significant — canonicalized UPPER, never
# lowercased (e.g. state="PAUSED", matchType="EXACT" per 08-SCHEMA-PIN).
_LITERAL_FIELDS = frozenset({"state", "matchtype"})


@dataclass(frozen=True)
class LedgerHit:
    """A COMPLETED hash match — the caller NO-OPS (never fires a second actions_start, D-10).

    Carries the recorded action_id (and verbatim terminal status) of the already-applied
    write so the caller can surface "already applied as <action_id>" instead of re-firing.
    """

    action_id: str
    status: str  # the verbatim terminal wire status (e.g. "COMPLETED")


@dataclass(frozen=True)
class InFlight:
    """An in-flight hash match — the caller RESUMES at poll on action_id (never re-fires).

    Distinct from LedgerHit: an in-flight entry is NOT a terminal no-op; it carries an
    action_id the caller resumes `actions_get` polling on (D-10). `test_inflight_resumes_at_poll`
    asserts `not isinstance(hit, LedgerHit)` so the two must be independent types.
    """

    action_id: str
    status: str  # the verbatim in-flight wire status (e.g. "IN_PROGRESS")


def _normalize_params(params: dict) -> dict:
    """Canonicalize a write's params so two equivalent payloads hash identically.

    Rules (the load-bearing identity — documented in the module docstring):
      - dict keys are lowercased+stripped to a canonical key;
      - enum/literal fields (state, matchType) are UPPERCASED to the wire literal;
      - other string values are lowercased+stripped (case/space-insensitive identity);
      - bid (and any float) is rounded to 2 dp (CAD cents);
      - booleans/ints pass through.
    The result is a plain dict; `action_hash` sorts keys via json.dumps(sort_keys=True), so
    key ORDER never changes identity.
    """
    normalized: dict = {}
    for raw_key, value in params.items():
        key = str(raw_key).strip().lower()
        if isinstance(value, bool):
            normalized[key] = value  # bool BEFORE int (bool is a subclass of int)
        elif isinstance(value, float):
            normalized[key] = round(value, 2)  # CAD cents — 0.250001 and 0.25 collide
        elif isinstance(value, int):
            normalized[key] = value
        elif isinstance(value, str):
            stripped = value.strip()
            if key in _LITERAL_FIELDS:
                normalized[key] = stripped.upper()  # wire literal (PAUSED / EXACT)
            else:
                normalized[key] = stripped.lower()  # case/space-insensitive identity
        else:
            normalized[key] = value
    return normalized


def action_hash(
    entity_type: str, entity_id: str, action_type: str, params: dict
) -> str:
    """sha256 content hash over a write's IDENTITY — entity+action+params, NEVER date (D-10).

    Returns `"sha256:" + hexdigest` over the canonical, sorted-key JSON of
    `{entity_type, entity_id, action_type, normalized_params}`. Excluding the date is the
    whole point: the same write re-proposed on a later day yields the SAME hash, so a re-run
    is always a no-op (`test_hash_excludes_date`). Param normalization (`_normalize_params`)
    means two equivalent payloads collide on one hash (`test_completed_hash_is_noop`).
    """
    payload = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action_type": action_type,
        "normalized_params": _normalize_params(params),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _ledger_path() -> Path:
    """The append-only jsonl path, resolved against the (monkeypatch-able) DATA_DIR."""
    return DATA_DIR / LEDGER_NAME


def lookup(action_hash_value: str) -> None | LedgerHit | InFlight:
    """Scan the ledger for a record whose RECOMPUTED hash matches; classify by status.

    Reads the append-only jsonl newest-LAST (a later append wins — the most recent status
    for a hash is the live one) and RECOMPUTES each record's identity hash from its
    entity/action/normalized_params (the stored `hash` field is informational provenance,
    never trusted as identity). A match whose status is terminal-COMPLETED -> `LedgerHit`
    (caller no-ops); a match whose status is in-flight (PENDING/IN_PROGRESS/WAITING_*) ->
    `InFlight` (caller resumes at poll); no match (or no ledger file) -> None (proceed).
    NO socket — local read only.
    """
    path = _ledger_path()
    if not path.exists():
        return None

    matched: None | LedgerHit | InFlight = None
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            recomputed = action_hash(
                record["entity_type"],
                record["entity_id"],
                record["action_type"],
                record.get("normalized_params", {}),
            )
            if recomputed != action_hash_value:
                continue
            status = record.get("status", "")
            action_id = record.get("action_id", "")
            # Newest-last: a later record for the same hash supersedes an earlier one.
            if status == "COMPLETED":
                matched = LedgerHit(action_id=action_id, status=status)
            elif status in _IN_FLIGHT_STATUSES:
                matched = InFlight(action_id=action_id, status=status)
            # An unmodeled/terminal-failure status does not become a no-op or a resume — the
            # caller proceeds (None) so a failed action can never read as applied.
    return matched


def append(record: dict) -> None:
    """Append one JSON object per line to the append-only ledger; NEVER edit a past line.

    The Pattern-3 record schema (08-RESEARCH): hash, entity_type, entity_id, action_type,
    normalized_params, action_id, status, ad_product, applied_at, marketplace. Records carry
    only entity/action/actionId/marketplace — NEVER the seller UUID (hard rule 5, T-08-09).
    Creates DATA_DIR if absent, opens "a", writes one compact line. Local I/O only — no socket.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _ledger_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, separators=(",", ":")) + "\n")
