"""Typed trust-spine results — the project's core anti-fabrication guarantee (D-02).

Every no-data / empty / failed / missing-threshold edge returns one of these typed
results, NEVER a bare None, a fabricated 0, a blank, or a swallowed exception
(RESEARCH §Pattern 2, Anti-Patterns; SOUL.md). A missing SKU is a SkuRow with
None ratios ("no data"), an empty/failed export is a Refusal, and a successful answer
is an Answer that always cites its provenance (export_id, source, verbatim definitions).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Verbatim from docs/datadoe-source-map.md §3a — definitions are surfaced, NEVER
# recomputed in Python (D-03). The ratios are READ as the premium source's own columns.
DEFINITIONS: dict[str, str] = {
    "acos": "ad_spend / 14-day ad sales, %",
    "tacos": "ad_spend / total_sales, %",
    "roi": "profit / total_cost, %",
}

# Provenance string for the premium Profit-by-SKU & Date source (D-06).
PREMIUM_SOURCE = "DataDoe premium Profit by SKU & Date (57a0cb319c)"


@dataclass(frozen=True)
class Refusal:
    """A typed refusal surfaced verbatim to the operator — never a substituted number."""

    reason: str  # human-readable, surfaced verbatim to the operator
    code: str  # "empty_export" | "failed_export" | "missing_threshold"
    export_id: str | None = None


@dataclass(frozen=True)
class Proceed:
    """The dryRun PROCEED verdict (WRITE-01).

    Returned by lifecycle.classify_dryrun ONLY when a dryRun is clean
    (status=="VALIDATED" && validation.valid && validation.issues==[]). It is the typed
    positive counterpart to Refusal — never a bare True. action_type carries the
    AMAZON_ADS_*-prefixed action type that validated, so the caller can wire the real run.
    """

    action_type: str


@dataclass(frozen=True)
class PollOutcome:
    """A classified single actions_get response (WRITE-05).

    status is the verbatim wire status; state is the engine's classification, one of
    "done" (ACTION_TERMINAL_SUCCESS), "done_with_issues" (ACTION_TERMINAL_PARTIAL), or
    "in_flight" (ACTION_IN_FLIGHT). A terminal-failure or unmodeled status is NOT a
    PollOutcome — it returns a Refusal (so a failed action can never read as "done").
    issues carries any surfaced messages verbatim (empty for a clean terminal/in-flight).
    """

    status: str
    state: str  # "done" | "done_with_issues" | "in_flight"
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProposedAction:
    """A pure-data PPC write proposal the margin gate evaluates — no Amazon call (D-08).

    delta_spend is the caller-computed CAD before→after spend delta (Open Q3 — the gate
    treats it as given, deferring bid→spend modeling to the Phase 9 queue). >0 is
    spend-increasing (must clear the per-SKU TACOS ceiling); <=0 is spend-decreasing
    (auto-passes per D-06, no projection needed).

    The three trailing fields (entity_type / entity_id / params) are the Phase-8 apply-spine
    extension (RESEARCH Open Q2). They are OPTIONAL with defaults so the Phase-7 margin gate
    ignores them entirely — `gate.evaluate` reads only sku/action_type/delta_spend, so the
    existing gate CLI contract (test_gate_action.py constructs ProposedAction with only the
    first four args) stays GREEN. ONLY the apply spine reads them:
      - entity_type: the FIND entity class — "campaigns" | "targets" | "adGroups" | "ads".
      - entity_id:   the FIND-verified live id (campaignId/targetId/...) the write targets.
      - params:      the build/identity params (target state, keyword text + matchType, bid)
                     — also the {normalized_params} half of the ledger content hash (D-10).
    """

    sku: str
    action_type: str  # e.g. "bid_up" | "budget_up" | "pause" | "negative" | "bid_down"
    delta_spend: float  # CAD; >0 spend-increasing, <=0 spend-decreasing
    marketplace: str = "CA"
    entity_type: str | None = None  # "campaigns" | "targets" | "adGroups" | "ads"
    entity_id: str | None = None  # the FIND-verified live entity id the write targets
    params: dict = field(default_factory=dict)  # build/identity params (state/keyword/bid)

    @property
    def is_spend_increasing(self) -> bool:
        return self.delta_spend > 0


@dataclass(frozen=True)
class GateRefusal:
    """A typed margin-gate refusal — names the breached number and its source (GATE-04).

    Sibling of Refusal, but carries the extra provenance fields a breach refusal needs:
    breached_value (e.g. the projected TACOS that breached), ceiling, and source. The gate
    NEVER clamps a breaching value to the ceiling (D-08); it returns this typed refusal so a
    breach can never be silently rewritten as a pass.

    code is one of:
      "no_threshold_set"   — min_net_margin_pct unset/empty -> refuse the write (D-07)
      "no_margin"          — unreliable/zero COGS or total_sales_sum == 0 -> CM% undefined (D-04)
      "sku_not_in_catalog" — SKU absent from the machine-readable catalog (GATE-05)
      "over_ceiling"       — projected TACOS > the per-SKU ceiling (GATE-04, strict >)
    """

    reason: str  # human-readable, surfaced verbatim to the operator
    code: str
    breached_value: float | None = None  # e.g. the projected TACOS that breached
    ceiling: float | None = None
    source: str | None = None  # PREMIUM_SOURCE provenance


@dataclass(frozen=True)
class GateVerdict:
    """A typed margin-gate PASS — never a bare True (mirror of Proceed).

    projected_tacos is None for an auto-passed spend-decrease (auto_pass=True, D-06):
    a spend-decreasing action cannot breach a TACOS ceiling, so no projection is computed.
    For a spend-increasing pass, projected_tacos <= ceiling (strict-> equal passes).
    """

    projected_tacos: float | None
    ceiling: float | None
    contribution_margin: float | None
    auto_pass: bool = False  # True for spend-decreasing actions (D-06)


@dataclass(frozen=True)
class AppliedResult:
    """The apply spine's typed POSITIVE counterpart to a Refusal — never a bare True (WRITE-03).

    Returned ONLY when a reversible write has fully reconciled: built → denylist/margin/cap
    cleared → dryRun PROCEED → actions_start(dryRun:false) → polled to a terminal status →
    FIND-echo confirmed → recorded in the idempotency ledger + decisions.md/brain (D-11). A
    write that fails ANY step returns a Refusal/GateRefusal instead — so an unapplied or
    failed action can NEVER read as applied (mirrors Proceed/GateVerdict's anti-fabrication
    discipline). Mirrors GateVerdict's frozen-dataclass style.

    Fields:
      - action_id:   the DataDoe actionId of the real (dryRun:false) write that reconciled.
      - status:      the verbatim terminal wire status — one of ACTION_TERMINAL_SUCCESS
                     ("COMPLETED") or ACTION_TERMINAL_PARTIAL ("PARTIALLY_COMPLETED" /
                     "COMPLETED_WITH_ISSUES"); never an in-flight or failure status.
      - hash:        the ledger content hash (sha256 over entity_type+entity_id+action_type+
                     normalized_params, NOT date — D-10) recorded for idempotency.
      - applied_at:  ISO-8601 timestamp the write reconciled.
      - marketplace: the marketplace the write landed on (default CA).

    NEW Phase-8 refusal codes this spine introduces reuse the existing Refusal / GateRefusal
    dataclasses (NO new refusal type), surfaced verbatim per CLAUDE.md hard rule 4:
      - "own_asin_denied"      — payload targets an owned ASIN; hard-refused pre-dryRun (EXEC-01, D-06/D-07).
      - "over_cap"             — a magnitude over the configured reversible cap; refused, never clamped (SC-5/D-02).
      - "stale_find_cache"     — the FIND cache file is older than the staleness window for a write (A2).
      - "canary_unconfirmed"   — the phase's first apply needs the one-time canary confirm (D-08/D-09).
      - "action_type_disabled" — DataDoe Settings→Actions org-disable (412); surfaced, never retried (Pitfall 4).
      - "unresolved_in_flight" — the poll loop exhausted without a terminal status; resumable, never assumed done.
      - "find_echo_mismatch"   — the FIND echo's mutated field disagrees with the intended write; never recorded applied.
    """

    action_id: str
    status: str  # the terminal wire status (COMPLETED / PARTIALLY_COMPLETED / COMPLETED_WITH_ISSUES)
    hash: str  # the ledger content hash (D-10) recorded for idempotency
    applied_at: str  # ISO-8601 timestamp the write reconciled
    marketplace: str = "CA"


@dataclass(frozen=True)
class SkuRow:
    """One per-SKU row.

    None acos/tacos/roi means "no data (not in premium export)" (D-10) — distinct from
    0 (which would mean "no spend"). The flag columns carry "ok" | "breach" |
    "no threshold set" | "no data"; suspect marks a TACOS>ACOS inversion (D-04).
    """

    seller_sku: str
    acos: float | None
    tacos: float | None
    roi: float | None
    acos_flag: str
    tacos_flag: str
    suspect: bool = False


@dataclass(frozen=True)
class Answer:
    """A successful, provenance-cited answer (D-06).

    export_id is non-optional: a successful Answer always names the export it was
    computed from. definitions defaults to the verbatim source-map definitions.
    """

    rows: list[SkuRow]
    export_id: str
    window_from: str
    window_to: str
    source: str = PREMIUM_SOURCE
    definitions: dict[str, str] = field(default_factory=lambda: dict(DEFINITIONS))
