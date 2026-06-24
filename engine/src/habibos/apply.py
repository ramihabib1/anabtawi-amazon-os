"""The reversible-write apply SPINE — the linear, typed orchestration twin of gate.evaluate
(WRITE-03 / WRITE-06 / WRITE-07 / EXEC-01) — CLAUDE.md hard rule 3.

This is the load-bearing new orchestration of Phase 8: it threads a `ProposedAction` through
EVERY gate to a logged, idempotent reversible write. It REUSES every Phase 6/7 primitive
verbatim (classify_dryrun, classify_poll, poll_action_status, find_cache.lookup/write,
gate.evaluate, logged_call) and the Plan-02 gates (denylist, ledger, magnitude). It computes
NO money ratios of its own — the margin math stays in gate.evaluate.

THE SEAM (CLAUDE.md hard rule 1): Python NEVER opens a socket. The agent supplies every MCP
result to `apply()` as plain data / zero-arg callables:
  - start_dryrun: () -> the actions_start(dryRun:true) response dict (gate BEFORE the real run)
  - start_apply:  () -> the actions_start(dryRun:false) response dict (the ONE real account write)
  - get_status:   () -> the latest actions_get response dict (the in-flight->terminal poll loop)
  - find_echo:    () -> the *_FIND response dict (pre-write entity verify + post-write echo confirm)
The spine classifies each via the reused typed primitives and threads the trust grammar.

BRANCH ORDER (mirror gate.evaluate — short-circuit on the FIRST refusal, never clamp/default):
  1. denylist.check        -> GateRefusal(own_asin_denied)   STOP (pre-build, self-cannibalization)
  2. gate.evaluate         -> GateRefusal                     STOP (spend-down auto-passes, D-06)
  3. magnitude.check       -> GateRefusal(over_cap)           STOP (None when seeded permissive)
  4. ledger.lookup         -> LedgerHit no-op / InFlight resume-at-poll (never re-fire start, D-10)
  5. CANARY one-time gate  -> Refusal(canary_unconfirmed)     STOP (D-08/D-09 first-apply confirm)
  6. find_cache.lookup     -> Refusal(find_cache_miss|stale_find_cache) STOP (FIND-before-write)
  7. classify_dryrun       -> Refusal(dryrun_invalid)         STOP BEFORE any dryRun:false (T-08-10)
  8. start_apply()         -> actionId                        (the ONE real write; 412 -> action_type_disabled)
  9. poll loop -> terminal -> Refusal(action_error|unresolved_in_flight) on fail/exhaustion
 10. find_echo confirm     -> Refusal(find_echo_mismatch)     STOP (mutated field != intended)
 11. ledger.append + log_decision -> AppliedResult            (recorded, idempotent, logged)

Every applied write (INCLUDING a standing-approved auto action) appends a decisions.md line +
a brain/raw note carrying what/why/expected-effect/actionId — autonomy is NOT silence (D-11,
WRITE-06, T-08-14). NEVER passes the seller UUID into logged_call / decisions / brain (hard rule 5).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

from . import datadoe, denylist, find_cache, gate, ledger, lifecycle, magnitude
from . import logging as habibos_logging
from .result import (
    AppliedResult,
    GateRefusal,
    GateVerdict,
    PollOutcome,
    Proceed,
    ProposedAction,
    Refusal,
)

# src/habibos/apply.py is two levels below the repo root; the data/log seams live at
# <repo>/data, <repo>/state/decisions.md, <repo>/brain/raw (mirror find_cache/ledger
# DATA_DIR = parents[2]/"data"). Tests monkeypatch ALL FOUR to tmp_path so no real
# ledger/decisions/brain/canary write happens.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = _REPO_ROOT / "data"
DECISIONS_PATH = _REPO_ROOT / "state" / "decisions.md"
BRAIN_RAW_DIR = _REPO_ROOT / "brain" / "raw"

# The phase's one-time canary marker (D-08/D-09): the FIRST apply of the phase requires the
# explicit --confirm-canary; once this marker is written (only after a success), subsequent
# reversible moves auto-apply. The marker lives under DATA_DIR so the test monkeypatch covers it.
CANARY_MARKER_NAME = "phase8_canary_confirmed"

# entity_type -> (action_type-prefixed AMAZON_ADS_* op, FIND result list key, per-item id field).
# Used by build_payload to key the payload + by the FIND-echo confirm. Verified vs 08-SCHEMA-PIN.
_AD_PRODUCT_DEFAULT = "SPONSORED_PRODUCTS"


def _data_dir() -> Path:
    """The (monkeypatch-able) data dir — read at call time, never captured at import."""
    return DATA_DIR


def _point_seams_at_data_dir() -> None:
    """Route the reused find_cache/ledger data seams at the spine's (monkeypatched) DATA_DIR.

    The spine owns ONE data root. The Phase-6/7 modules resolve their own DATA_DIR; in tests
    only `apply.DATA_DIR` is monkeypatched, so the spine re-points find_cache/ledger at it so
    all idempotency + FIND-cache writes land in the same (tmp) root. In production all three
    resolve to <repo>/data anyway — this is a no-op there.
    """
    find_cache.DATA_DIR = _data_dir()
    ledger.DATA_DIR = _data_dir()


# --------------------------------------------------------------------------------------------
# build_payload — the per-action-type write body, against the 08-SCHEMA-PIN field map.
# --------------------------------------------------------------------------------------------
def build_payload(action: ProposedAction) -> dict:
    """Build the `actions_start` `details` payload for a reversible write (08-SCHEMA-PIN).

    Per action_type, sends ONLY the mutable fields the live request-validator accepts:
      - pause     (AMAZON_ADS_CAMPAIGNS_UPDATE): {"campaigns":[{campaignId, state:"PAUSED"}]}
                  — NO `adProduct` key (the live validator rejects adProduct on CAMPAIGNS_UPDATE).
      - negative  (AMAZON_ADS_TARGETS_ADD): a negative exact-match keyword target attached at
                  AD_GROUP level (negative:true, matchType nested under keywordTarget, state
                  REQUIRED on ADD).
      - bid_down  (AMAZON_ADS_TARGETS_UPDATE): {"targets":[{targetId, bid:<flat number>}]}
                  — only mutable fields; the new lower bid is a bare number (not a {bid,currency}).

    A pure builder — no socket, no fabrication. An unknown action_type raises (fail loud).
    """
    params = action.params or {}
    if action.action_type == "pause":
        # PAUSE — send ONLY campaignId + state. NO adProduct (08-SCHEMA-PIN §1).
        return {
            "campaigns": [
                {
                    "campaignId": action.entity_id,
                    "state": params.get("state", "PAUSED"),
                }
            ]
        }
    if action.action_type == "negative":
        # ADD a negative exact-match keyword at AD_GROUP level (08-SCHEMA-PIN §2).
        return {
            "targets": [
                {
                    "campaignId": params.get("campaignId"),
                    "adGroupId": action.entity_id,
                    "adProduct": params.get("adProduct", _AD_PRODUCT_DEFAULT),
                    "state": "ENABLED",
                    "negative": True,
                    "targetType": "KEYWORD",
                    "targetDetails": {
                        "keywordTarget": {
                            "keyword": params.get("keyword"),
                            "matchType": params.get("matchType", "EXACT"),
                        }
                    },
                }
            ]
        }
    if action.action_type == "bid_down":
        # BID-DOWN — send ONLY targetId + the new flat bid number (08-SCHEMA-PIN §3).
        return {"targets": [{"targetId": action.entity_id, "bid": params.get("bid")}]}
    raise ValueError(f"build_payload: unsupported action_type {action.action_type!r}")


# --------------------------------------------------------------------------------------------
# The reversible-write apply SPINE.
# --------------------------------------------------------------------------------------------
def apply(
    action: ProposedAction,
    *,
    owned_source: str | Path,
    start_dryrun,
    start_apply,
    get_status,
    find_echo,
    confirm_canary: bool = False,
    catalog_path: str | Path | None = None,
    gate_frame=None,
    ad_product: str = _AD_PRODUCT_DEFAULT,
) -> AppliedResult | Refusal | GateRefusal:
    """Thread a ProposedAction through every gate to a logged, idempotent reversible write.

    Keyword callables are the agent-supplied MCP results (Python opens NO socket). Returns a
    typed AppliedResult on a fully-reconciled write, or a Refusal/GateRefusal at the FIRST gate
    that stops it — an unapplied/failed write can NEVER read as applied. See module docstring
    for the full branch order. Wraps the live-account `start_apply` in logged_call (no UUID).
    """
    _point_seams_at_data_dir()

    # 1. DENYLIST — pre-build hard refuse if the payload targets one of our OWN ASINs (EXEC-01).
    deny = denylist.check(action, owned_source)
    if isinstance(deny, GateRefusal):
        return deny

    # 2. MARGIN GATE — the spine sets delta_spend<=0 for reversible (Open Q3) so a spend-down
    #    auto-passes (D-06); a spend-up that breaches its ceiling STOPs. The reversible actions
    #    (pause/negative/bid_down) are all spend-DOWN, so gate.evaluate auto-passes with NO
    #    frame/catalog read. If a caller hands a positive delta_spend + a frame, evaluate gates it.
    verdict = _evaluate_margin(action, gate_frame, catalog_path)
    if isinstance(verdict, GateRefusal):
        return verdict

    # 3. MAGNITUDE CAP — over-cap reversible move refused (never clamped); None when the cap is
    #    unset (seeded permissive, D-01/D-02). The caller may pass params["pct_change"]; absent -> pass.
    cap = magnitude.check(action, _max_reversible_pct(action))
    if isinstance(cap, GateRefusal):
        return cap

    # 4. LEDGER — content-hash idempotency. A COMPLETED hash match is a no-op (return the
    #    recorded actionId, never re-fire start); an in-flight match resumes at poll (D-10).
    normalized = ledger._normalize_params(action.params or {})
    action_hash = ledger.action_hash(
        action.entity_type, action.entity_id, action.action_type, normalized
    )
    hit = ledger.lookup(action_hash)
    if isinstance(hit, ledger.LedgerHit):
        return AppliedResult(
            action_id=hit.action_id,
            status=hit.status,
            hash=action_hash,
            applied_at=_now_iso(),
            marketplace=action.marketplace,
        )
    resume_action_id: str | None = None
    if isinstance(hit, ledger.InFlight):
        # D-10: SKIP start, resume at poll on the recorded action_id (never re-fire).
        resume_action_id = hit.action_id

    # 5. CANARY one-time confirm (D-08/D-09): the phase's FIRST apply requires the explicit
    #    confirm; once the marker exists, subsequent reversible moves auto-apply.
    marker = _data_dir() / CANARY_MARKER_NAME
    canary_was_unconfirmed = not marker.exists()
    if canary_was_unconfirmed and not confirm_canary:
        return Refusal(
            "phase-8 first apply requires the one-time canary confirm (--confirm-canary)",
            "canary_unconfirmed",
        )

    # 6. FIND-before-write — the write must target an entity a PRIOR FIND actually returned.
    #    Seed the cache from the agent's FIND result, then a write-bearing lookup verifies the
    #    entity_id is present + the cache is fresh (A2). A miss/stale STOPs (never a guessed ID).
    find_result = find_echo()
    find_cache.write(action.entity_type, ad_product, find_result)
    cached = find_cache.lookup(
        action.entity_type, ad_product, action.entity_id, write_bearing=True
    )
    if isinstance(cached, Refusal):
        return cached  # find_cache_miss | stale_find_cache

    # 7. DRYRUN gate — classify the agent's dryRun:true response. An invalid dryRun STOPs
    #    BEFORE any dryRun:false fires (T-08-10 — the real write never runs on a bad dryRun).
    #    A drifted/untrusted dryRun shape (classify_dryrun raises on schema drift) is ALSO a
    #    STOP, never an exception that escapes past the guard: surface it as a typed refusal so
    #    the real write can never fire on an unvalidatable dryRun (Pitfall 1 / T-08-10).
    try:
        dryrun = lifecycle.classify_dryrun(start_dryrun())
    except ValueError as exc:  # schema drift -> refuse, never let dryRun:false fire
        return Refusal(f"dryRun response could not be validated: {exc}", "dryrun_invalid")
    if isinstance(dryrun, Refusal):
        return dryrun
    assert isinstance(dryrun, Proceed)  # noqa: S101 - typed positive narrowing

    # 8. THE REAL WRITE — actions_start(dryRun:false). Wrapped in logged_call (op + marketplace
    #    only; NEVER the seller UUID). A 412/disabled response -> action_type_disabled, no retry.
    if resume_action_id is not None:
        # InFlight resume (D-10): skip the start, poll the recorded action_id.
        action_id = resume_action_id
    else:
        started = _logged_start_apply(start_apply, action.marketplace)
        if isinstance(started, Refusal):
            return started
        action_id = started

    # 9. POLL loop — drive get_status through in-flight to a terminal status (reuse
    #    poll_action_status + classify_poll). ERROR/CANCELED/BLOCKED_* -> action_error;
    #    20 attempts without terminal -> unresolved_in_flight (resumable, carries actionId).
    poll = _poll_to_terminal(get_status)
    if isinstance(poll, Refusal):
        if poll.code == "unresolved_in_flight":
            # Carry the actionId on the resumable refusal (export_id reused as the id slot).
            return Refusal(poll.reason, poll.code, export_id=action_id)
        return poll
    terminal_status = poll.status

    # 10. FIND-echo confirm — re-lookup the mutated entity and compare the action-type's mutated
    #     field against build_payload's intended value (08-SCHEMA-PIN). ANY mismatch STOPs —
    #     never record an unconfirmed write as applied (SC-1 / WRITE-03).
    echo = find_echo()
    if not _echo_confirms(action, echo):
        return Refusal(
            "FIND echo's mutated field disagrees with the intended write — not applied",
            "find_echo_mismatch",
        )

    # 11. RECORD + LOG — append the idempotency record (with the REAL computed hash) and log the
    #     decisions.md line + brain note (carry the actionId; never the seller UUID, D-11).
    applied_at = _now_iso()
    ledger.append(
        {
            "hash": action_hash,
            "entity_type": action.entity_type,
            "entity_id": action.entity_id,
            "action_type": action.action_type,
            "normalized_params": normalized,
            "action_id": action_id,
            "status": terminal_status,
            "ad_product": ad_product,
            "applied_at": applied_at,
            "marketplace": action.marketplace,
        }
    )
    result = AppliedResult(
        action_id=action_id,
        status=terminal_status,
        hash=action_hash,
        applied_at=applied_at,
        marketplace=action.marketplace,
    )
    # D-08/D-09: write the canary marker ONLY after a successful apply (so a failed first apply
    # does not silently arm auto-apply for the rest of the phase).
    if canary_was_unconfirmed and confirm_canary:
        _write_canary_marker()
    log_decision(action, action_id, result)
    return result


# --------------------------------------------------------------------------------------------
# Internal helpers — each a thin, typed seam (no money math, no socket).
# --------------------------------------------------------------------------------------------
def _evaluate_margin(
    action: ProposedAction, gate_frame, catalog_path: str | Path | None
) -> GateVerdict | GateRefusal:
    """Run the margin gate. A spend-down (the reversible default) auto-passes with NO read; a
    spend-up requires the caller to have supplied the export frame + catalog so the gate can
    project. The spine never computes the ratio itself (gate.evaluate owns the money math).
    """
    if not action.is_spend_increasing:
        # Spend-down auto-pass — gate.evaluate returns GateVerdict(auto_pass=True) with no read.
        return gate.evaluate(_empty_frame(), action, _no_catalog(), action.marketplace)
    return gate.evaluate(gate_frame, action, catalog_path, action.marketplace)


def _empty_frame():
    """An empty polars frame for the spend-down auto-pass path (gate reads nothing from it)."""
    import polars as pl

    return pl.DataFrame(
        {"sku": [], "profit_sum": [], "ad_spend_sum": [], "total_sales_sum": []}
    )


def _no_catalog() -> Path:
    """A path the spend-down path never reads (gate.evaluate returns before the catalog read)."""
    return _REPO_ROOT / "config" / "sku_catalog.toml"


def _max_reversible_pct(action: ProposedAction) -> float | None:
    """The configured magnitude cap (None = seeded permissive). The caller may inject a cap via
    params['max_reversible_pct_change']; absent -> None -> magnitude.check passes at any size.
    """
    return (action.params or {}).get("max_reversible_pct_change")


def _logged_start_apply(start_apply, marketplace: str) -> str | Refusal:
    """Fire the ONE real account write inside logged_call; return its actionId or a typed refusal.

    A 412/disabled response (DataDoe Settings->Actions org-disable) -> Refusal(action_type_disabled),
    surfaced and NEVER retried (Pitfall 4 / T-08-12). NEVER passes the seller UUID into the log.
    """
    habibos_logging.configure()
    with habibos_logging.logged_call("apply_action.start", marketplace=marketplace) as end_fields:
        resp = start_apply()
        disabled = _disabled_response(resp)
        if disabled is not None:
            end_fields["status"] = "refused"
            return disabled
        action_id = resp.get("actionId")
        if not action_id:
            end_fields["status"] = "refused"
            return Refusal(
                "actions_start returned no actionId — the real write did not start",
                "action_start_failed",
            )
        end_fields["status"] = "started"
        return action_id


def _disabled_response(resp: dict) -> Refusal | None:
    """Detect a 412/disabled actions_start response -> action_type_disabled (no retry).

    DataDoe surfaces an org-level action-type disable as a 412 (statusCode/httpStatus == 412)
    or a disabled marker. Treated as a clean typed refusal, NEVER a bug/retry (Pitfall 4).
    """
    code = resp.get("statusCode") or resp.get("httpStatus") or resp.get("code")
    status = str(resp.get("status", "")).upper()
    if code == 412 or status in {"DISABLED", "ACTION_TYPE_DISABLED"}:
        message = resp.get("message") or "action type disabled in DataDoe Settings->Actions (412)"
        return Refusal(message, "action_type_disabled")
    return None


def _poll_to_terminal(get_status) -> PollOutcome | Refusal:
    """Drive get_status through in-flight to a terminal status; classify the terminal response.

    Reuses datadoe.poll_action_status (the tenacity 20-attempt loop) by handing it a status-
    extracting wrapper that captures each FULL response, then classify_poll the captured
    terminal one. A terminal ERROR/CANCELED/BLOCKED_* -> Refusal(action_error); the loop
    exhausting 20 attempts without terminal -> Refusal(unresolved_in_flight) — resumable, never
    assumed done. An unknown status from classify_poll surfaces verbatim.
    """
    from tenacity import RetryError

    captured: dict = {}

    def _status_str() -> str:
        captured["resp"] = get_status()
        return str(captured["resp"].get("status", ""))

    try:
        datadoe.poll_action_status(_status_str)
    except RetryError:
        # Exhausted 20 attempts without a terminal status — resumable, never assumed success.
        return Refusal(
            "poll loop exhausted without a terminal status — in-flight, resumable",
            "unresolved_in_flight",
        )

    # The captured response is now terminal (or an unmodeled status). classify_poll buckets it:
    # COMPLETED/PARTIALLY_* -> PollOutcome; ERROR/CANCELED/BLOCKED_* -> Refusal(action_error);
    # anything unmodeled -> Refusal(unknown_status).
    return lifecycle.classify_poll(captured["resp"])


def _echo_confirms(action: ProposedAction, echo: dict) -> bool:
    """Confirm the FIND echo's mutated field equals build_payload's intended value (08-SCHEMA-PIN).

    Per action type:
      - pause     -> the campaign's `state` == "PAUSED" (the intended state).
      - bid_down  -> the target's nested `bid.bid` == the intended new bid (08-SCHEMA-PIN §3 asymmetry).
      - negative  -> the negated target is PRESENT (negative:true + matching keywordTarget keyword).
    ANY mismatch / absent expected field -> False (the caller refuses find_echo_mismatch). Never
    treats an unconfirmed write as applied.
    """
    params = action.params or {}
    if action.action_type == "pause":
        intended_state = params.get("state", "PAUSED")
        for campaign in echo.get("campaigns", []):
            if campaign.get("campaignId") == action.entity_id:
                return campaign.get("state") == intended_state
        return False
    if action.action_type == "bid_down":
        intended_bid = params.get("bid")
        for target in echo.get("targets", []):
            if target.get("targetId") == action.entity_id:
                # A TARGETS_FIND echoes bid as a nested object {bid, currencyCode} -> read .bid.bid.
                bid_obj = target.get("bid")
                echoed = bid_obj.get("bid") if isinstance(bid_obj, dict) else bid_obj
                return _floats_equal(echoed, intended_bid)
        return False
    if action.action_type == "negative":
        intended_keyword = (params.get("keyword") or "").strip().lower()
        for target in echo.get("targets", []):
            if not target.get("negative"):
                continue
            keyword = (
                target.get("targetDetails", {})
                .get("keywordTarget", {})
                .get("keyword", "")
            )
            if keyword.strip().lower() == intended_keyword and intended_keyword:
                return True
        return False
    # Unknown action type — never silently confirm.
    return False


def _floats_equal(a, b, tol: float = 0.005) -> bool:
    """Cent-tolerant float equality for the bid-down echo confirm (CAD cents)."""
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def _now_iso() -> str:
    """ISO-8601 UTC timestamp the write reconciled."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_canary_marker() -> None:
    """Write the phase-8 one-time canary marker under DATA_DIR (D-08/D-09)."""
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / CANARY_MARKER_NAME).write_text(
        f"phase-8 canary confirmed {_now_iso()}\n", encoding="utf-8"
    )


# --------------------------------------------------------------------------------------------
# log_decision — the decisions.md + brain/raw operator-record seam (D-11 / WRITE-06).
# --------------------------------------------------------------------------------------------
def _slug(text: str) -> str:
    """Filesystem-safe slug for a brain-note filename."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "action"


def log_decision(action: ProposedAction, action_id: str, result: AppliedResult) -> None:
    """Record EVERY applied write to decisions.md + a brain/raw note (D-11, WRITE-06).

    Appends ONE dated pipe-delimited line to DECISIONS_PATH (cloning inbox._log_decision's
    append seam) AND writes ONE brain/raw note carrying what/why/expected-effect/actionId.
    STANDING-APPROVED auto actions log too — autonomy is NOT silence (T-08-14). NEVER inlines
    the seller UUID in either record (hard rule 5). Repo-root-relative; tests monkeypatch paths.
    """
    today = date.today().isoformat()
    change = _change_phrase(action)
    why = "reversible move applied via the gated write spine"
    expected = "spend reduced on the targeted entity (reversible)"

    # decisions.md — one dated line: YYYY-MM-DD | area | SKU/entity | change | rationale |
    # expected impact | terminal status.
    line = (
        f"{today} | ppc | [{action.sku}] {action.entity_type} ({action.entity_id}) | "
        f"{change} via apply spine (actionId {action_id}) | {why} | "
        f"{expected} | {result.status}"
    )
    DECISIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DECISIONS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    # brain/raw note — what changed, why, expected effect, actionId.
    BRAIN_RAW_DIR.mkdir(parents=True, exist_ok=True)
    note_name = f"{today}_apply-{_slug(action.action_type + '-' + (action.entity_id or ''))}.md"
    note_body = (
        f"# Applied reversible write — {action.action_type} ({action.entity_id})\n\n"
        f"- **date:** {today}\n"
        f"- **sku:** {action.sku}\n"
        f"- **entity:** {action.entity_type} {action.entity_id}\n"
        f"- **what changed:** {change}\n"
        f"- **why:** {why}\n"
        f"- **expected effect:** {expected}\n"
        f"- **actionId:** {action_id}\n"
        f"- **terminal status:** {result.status}\n"
        f"- **marketplace:** {result.marketplace}\n"
    )
    (BRAIN_RAW_DIR / note_name).write_text(note_body, encoding="utf-8")


def _change_phrase(action: ProposedAction) -> str:
    """A short human change phrase for the decisions/brain record (no money math)."""
    params = action.params or {}
    if action.action_type == "pause":
        return "paused campaign (state -> PAUSED)"
    if action.action_type == "bid_down":
        return f"bid lowered to {params.get('bid')}"
    if action.action_type == "negative":
        return f"added negative-exact keyword '{params.get('keyword')}'"
    return f"{action.action_type} applied"
