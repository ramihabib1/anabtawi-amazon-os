# Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed - Research

**Researched:** 2026-06-22
**Domain:** Gated Amazon Ads write execution (DataDoe `actions_start`) — the apply spine wrapping the Phase 6 lifecycle + Phase 7 margin gate; idempotent ledger; own-ASIN denylist; stop-the-bleed batch
**Confidence:** HIGH (engine substrate, patterns, idempotency design — all read directly from the repo) / MEDIUM (DataDoe payload schemas — pinned by tool name + repo evidence, must be confirmed live via `actions_details_schema_get` at plan/execute time, NOT reachable read-only in this research session)

## Summary

Phase 8 lands the first **real** Amazon Ads writes, but only reversible ones (pause campaign, add exact-match negative keyword, lower a bid). The work is **almost entirely orchestration of substrate that already exists** — `lifecycle.classify_dryrun` / `classify_poll`, `datadoe.poll_action_status` (the in-flight→terminal primitive, built in Phase 6 explicitly "for Phase 8's apply spine"), `find_cache.write/lookup`, `gate.evaluate` (auto-passes spend-decreasing), `logging.logged_call`, and the typed `Refusal`/`Proceed`/`PollOutcome` grammar in `result.py`. The new code is: an `apply.py` module that drives BUILD → denylist gate → margin gate → dryRun classify → `actions_start(dryRun:false)` → poll loop → FIND-echo confirm → idempotent ledger + log; two new pre-dryRun gates (own-ASIN denylist + the seeded-permissive magnitude cap); a `data/actions_ledger.jsonl` idempotency store; and a thin `apply_action.py` CLI mirroring `gate_action.py` / `classify_poll.py`.

The single architecturally-important unknown is the **exact DataDoe `actions_start` payload schema per reversible action type** (pause-campaign state write, negative-keyword create, bid-down target write). This research could NOT reach the live schema read-only — the DataDoe MCP is not in this session's toolset, and the connected `agentcentral` MCP reports Amazon Ads not connected for its scope. The repo's own evidence (`datadoe-query` SKILL §"Write actions", Phase 6 fixtures, the live-confirmed `CAMPAIGNS_UPDATE` caveat) strongly constrains the shapes, but every payload MUST be pinned via `actions_details_schema_get` + a `dryRun:true` round-trip before the real apply. This is a documented plan/execute-time step, not a fabricated field.

**Primary recommendation:** Build `apply.py` as a linear, typed, hand-written spine that **reuses every Phase 6/7 primitive verbatim** and adds only the ledger, the two pre-dryRun gates, and the log seam. Pin all three payload schemas via `actions_details_schema_get` + `dryRun:true` in a Wave-0 reconnaissance task before writing the build functions. Seed the magnitude cap permissive (D-02) and the denylist from `sku_catalog.toml` ASINs (D-06). Surface the DataDoe Settings→Actions org-enable precondition as a runtime refusal, not a silent failure.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (magnitude cap posture):** Standing approval is **permissive for all reversible actions** — pause, negative-keyword add, bid-down **auto-apply at any magnitude** after a clean dryRun. Only spend-**increasing** actions (Phase 9) require explicit approval. Reversibility is the protection.
- **D-02 (SC-5 reconciliation):** The magnitude-cap **mechanism is built and pytest-tested** (a configurable bounded-% gate that *would* route an over-cap reversible move to explicit review) but **seeded permissive** (effectively unlimited for reversible actions) so live behavior matches D-01. Mirrors Phase 7 D-07 (build-the-refusal-path-then-seed-the-live-value). Tightening later is a **config change** in `thresholds.toml` / `sku_catalog.toml`, not a code change. Verifier treats SC-5 as "mechanism exists + tested, seeded permissive by operator decision."
- **D-03 (first batch):** Pause the **whole campaigns** for the 4 dead SKUs (**FX-M8MA, 9Z-KUHZ, VH-ZTOC, ZK-4NDS**) **+** apply the **exact-match** negative-keyword harvest per-campaign, all in **one batch**, gated behind the canary verify (D-08).
- **D-04 (negative harvest):** **Exact-by-default**. Keep-positive allowlist protects **`baklava gift box`** (never negated). "Watch-don't-negate" terms are **bid-down, not negated**. Phrase/broad negatives are **not** in this batch (exact only).
- **D-05 (pause whole campaigns):** Chosen deliberately — the cleanest fully-reversible stop; leaves **no empty ENABLED shell** that can re-accrue spend.
- **D-06 (denylist scope):** Covers the **full set of ~30 owned ASINs**, read from **`engine/config/sku_catalog.toml`** (single source of truth, mirrors 07 D-04). **B07TV972JT is one row in that set, not a special case.** Any payload pointing an ad at an owned ASIN is refused.
- **D-07 (denylist placement):** Enforcement sits in Python **before BUILD→DRYRUN** (a pre-dryRun refuse-gate beside the margin gate), is a **hard refusal** (not warn-and-confirm), and uses the existing typed-refusal grammar surfaced verbatim.
- **D-08 (canary debut):** Run exactly ONE reversible write (a single pause) end-to-end — apply → poll to COMPLETED → FIND-echo confirm — with a **one-time manual confirm on that first apply**; verify it reconciles cleanly. Only after the canary confirms does the standing-approved batch (D-03) run under D-01's permissive auto-apply.
- **D-09 (canary scope):** The manual confirm is a **one-time gate for the first apply of the phase**, not per-action. After the canary, reversible moves auto-apply.
- **D-10 (idempotency identity):** Two actions are "the same" (no-op re-run) when their **content hash over {entity type + entity ID + action type + normalized params}** matches a COMPLETED entry in `data/actions_ledger.jsonl`. An **in-flight `actionId` resumes at poll**, never re-fires `actions_start`. Identity is keyed on entity + action + params, **NOT on date** — re-pausing an already-paused campaign is always a no-op.
- **D-11 (logging):** Every applied write logs a dated line to **`state/decisions.md`** AND a **`brain/raw/`** note (what changed, why, expected effect, `actionId`). **Standing-approved (auto) actions log too** — autonomy ≠ silence.

### Claude's Discretion

- Poll-loop interval/backoff and max-attempts before an in-flight action is surfaced as unresolved (reuse `datadoe.poll_action_status` terminal-on-FAILED).
- `find_cache` staleness-window value (Assumption A2) — pick a sane documented default (e.g. same-day / 24h), not a silent hard-code.
- Exact `actions_ledger.jsonl` format, hash field set, apply-spine module/function layout, CLI shape (mirror `answer_tacos.py` / `gate_action.py`).
- Whether a negative is added via a dedicated negative-create action vs a target-state write — pin against `actions_details_schema_get`.

### Deferred Ideas (OUT OF SCOPE)

- **External precondition (blocker, not scope):** Rami (org owner) must **enable the required Ads action types in DataDoe → Settings → Actions** (OFF by default) before any real write lands. The phase can BUILD + dryRun without it; the canary apply (D-08) and batch (D-03) are blocked until enabled. Surface clearly at execution time.
- Spend-increasing writes + explicit-approval daily ranked queue + dollar-ranked rendering → **Phase 9**.
- Act-now vs judge-later attribution boundary → **Phase 9** (QUEUE-04).
- Tightening the magnitude cap → config change (D-02 dial).
- New-campaign chains, portfolios, `CAMPAIGNS_REMOVE` → **Phase 10**.
- Migrating `thresholds.toml` + SKU catalog → Supabase → **Phase 3.5**.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WRITE-03 | Execute a reversible PPC write end-to-end (pause/negative/bid-down) — build → dryRun → apply → poll `actions_get` → confirm | The apply spine drives `lifecycle.classify_dryrun` → `actions_start(dryRun:false)` → `datadoe.poll_action_status` loop + `lifecycle.classify_poll` per response → `find_cache` echo. All primitives exist; the spine is new orchestration. Payload schemas pinned via `actions_details_schema_get` (§Standard Stack, §Code Examples). |
| WRITE-06 | Every applied write logs a dated line to `state/decisions.md` + a `brain/raw/` note (what changed, why, effect, `actionId`) | New log seam in `apply.py` appends one `decisions.md` line + writes one `brain/raw/` note. Pattern: existing `decisions.md` format (§Architecture Patterns); `inbox.py` already appends to `decisions.md`. Distinct from `logged_call` (external-call telemetry). |
| WRITE-07 | Apply is idempotent — re-running the same approved action does not double-apply | New `data/actions_ledger.jsonl` content-hash ledger keyed {entity type + entity ID + action type + normalized params} (D-10). COMPLETED match → no-op; in-flight `actionId` → resume at poll, never re-fire start. Schema in §Architecture Patterns Pattern 3. |
| EXEC-01 | Stop-the-bleed — pause dead-SKU campaigns + per-campaign negative harvest; enforce EXCLUDE-own-ASIN denylist | The batch (D-03/D-04) drives the spine N times. Denylist gate reads owned ASINs from `sku_catalog.toml` (§Pattern 4). **Open gap:** 2 of 4 dead SKUs are absent from the catalog (§Runtime State Inventory, §Open Questions) — campaignIds come from FIND cache, not the SKU catalog. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| FIND live entity IDs (campaignId/targetId) | Agent (MCP `*_FIND`) | Engine `find_cache.write` | The seam: Python never opens a socket; the agent makes the MCP call and hands the result to `find_cache.write` to persist (CLAUDE.md hard rule 1). |
| dryRun validation | Agent (MCP `actions_start dryRun:true`) | Engine `lifecycle.classify_dryrun` | Agent fires the MCP call; hand-written `classify_dryrun` owns the PROCEED/STOP verdict (WRITE-01, never classified in chat). |
| Margin gate (auto-pass spend-down) | Engine `gate.evaluate` | — | Money logic; hand-written + pytest-covered (CLAUDE.md hard rule 3). Reversible writes route through and auto-pass (07 D-06). |
| Own-ASIN denylist | Engine (new, in/beside `apply.py`) | `sku_catalog.toml` | Pure typed refuse-gate, no network — must be hand-written + tested (it gates a real write). |
| Magnitude cap | Engine (new, seeded permissive) | `thresholds.toml` | Bounded-% gate, hand-written + tested; config-seeded so tightening is a dial (D-02). |
| Real apply (`dryRun:false`) | Agent (MCP `actions_start`) | Engine spine orchestrates | The one real account mutation. Agent makes the call; Python classifies the response + drives the loop. |
| Poll in-flight→terminal | Agent (MCP `actions_get`, repeated) | Engine `poll_action_status` + `classify_poll` | `poll_action_status` is the tenacity loop primitive (built Phase 6 for this); `classify_poll` classifies each response. |
| Idempotency ledger | Engine (new `apply.py` + `data/actions_ledger.jsonl`) | — | Local file I/O only (the seam); content-hash identity (D-10). |
| decisions.md / brain log | Engine/Agent (new log seam) | `state/decisions.md`, `brain/raw/` | Operator-facing decision record, distinct from `logged_call` telemetry (D-11). |

### System Architecture Diagram

```
                         ProposedAction (sku, action_type, entity_type,
                         entity_id, delta_spend, params)
                                  │
                                  ▼
                   ┌──────────────────────────────┐
                   │  apply.py  (NEW — the spine)  │   pure typed, no socket
                   └──────────────────────────────┘
                                  │
        ┌─────────────────────────┼──────────────────────────────────┐
        ▼                         ▼                                    ▼
  [1] DENYLIST GATE         [2] MARGIN GATE                    [3] MAGNITUDE CAP
  target ASIN ∈ owned?      gate.evaluate(...)                 bounded-% (D-02
  → GateRefusal             spend-down → auto_pass             seeded permissive)
  (own_asin_denied)         (07 D-06)                          → pass for reversible
        │  pass                   │  pass                              │  pass
        └─────────────────────────┴──────────────────────────────────┘
                                  ▼
                   [4] IDEMPOTENCY LEDGER LOOKUP   ── content hash {entity_type +
                   data/actions_ledger.jsonl          entity_id + action_type +
                        │                              normalized_params}  (D-10)
          ┌─────────────┼──────────────────────────┐
          ▼             ▼                          ▼
   COMPLETED match   in-flight actionId       no entry
   → NO-OP return    → skip start, resume     → proceed
                       at poll [8]
                                  ▼ (no entry)
                   [5] FIND-before-write   ── find_cache.lookup(entity_type,
                        │ HIT                  ad_product, entity_id)
                        │ MISS → Refusal(find_cache_miss)  STOP
                        ▼
                   [6] dryRun  ── agent: actions_start(dryRun:true)
                        │           engine: lifecycle.classify_dryrun
                        │ Proceed
                        │ Refusal(dryrun_invalid) → STOP
                        ▼
                   [7] APPLY   ── agent: actions_start(dryRun:false) → actionId
                        │           (canary: one-time manual confirm, D-08)
                        ▼
                   [8] POLL LOOP ── datadoe.poll_action_status + classify_poll
                        │              per response until terminal
          ┌─────────────┼──────────────────────────┐
          ▼             ▼                          ▼
      done          done_with_issues         Refusal(action_error)
   (COMPLETED)      (PARTIALLY_*)             / unknown_status → surface
          │             │
          ▼             ▼
                   [9] FIND-echo confirm ── agent: *_FIND again; engine: assert
                        │                    changed entity reflects the write
                        ▼
                   [10] LEDGER WRITE + LOG ── append actions_ledger.jsonl (COMPLETED
                         actionId + hash) + decisions.md line + brain/raw note (D-11)
```

## Standard Stack

### Core (all already in the repo — REUSE, do not rebuild)

| Module / asset | Purpose | Why reuse |
|----------------|---------|-----------|
| `habibos.lifecycle.classify_dryrun` | dryRun → `Proceed`/`Refusal` | The WRITE-01 gate; the spine calls it before the real run. |
| `habibos.lifecycle.classify_poll` | one `actions_get` → `PollOutcome`/`Refusal` | The per-response classifier the poll loop calls each iteration. |
| `habibos.datadoe.poll_action_status` | tenacity in-flight→terminal loop primitive | Built in Phase 6 explicitly "driven end-to-end by Phase 8's apply spine." stop_after_attempt(20), `wait_exponential_jitter(initial=1, max=15)`, terminal on `ACTION_TERMINAL`. |
| `habibos.datadoe.ACTION_*` sets | pinned status enum | `ACTION_IN_FLIGHT`/`_TERMINAL_SUCCESS`/`_TERMINAL_PARTIAL`/`_TERMINAL_FAIL`. There is **no `FAILED`** (it is `ERROR`); `CANCELED` has one L. |
| `habibos.find_cache.write` / `lookup` | FIND-before-write + FIND-echo | `lookup` returns the cached entity dict on HIT or `Refusal(find_cache_miss)`; the spine uses `lookup` to gate the build and `write`+compare for the echo. |
| `habibos.gate.evaluate` | margin gate | Reversible (spend-down, `delta_spend <= 0`) → `GateVerdict(auto_pass=True)` with NO config/catalog read (07 D-06). |
| `habibos.logging.logged_call` | one `.start`/`.end` per external call | Wraps every `actions_start`/`actions_get` op; NEVER passes the seller UUID. |
| `habibos.result` types | `ProposedAction`, `GateVerdict`, `GateRefusal`, `Refusal`, `Proceed`, `PollOutcome` | The typed grammar the denylist + cap + ledger reuse. **`ProposedAction` needs new fields** (see Open Questions). |
| `engine/config/sku_catalog.toml` | owned-ASIN set (D-06) + per-SKU cogs/tier | Denylist reads the `asin` column from every `[sku."..."]` row. |
| `engine/config/thresholds.toml` | magnitude-cap dial (D-02) | Add a seeded-permissive `max_reversible_pct_change` (or absent → permissive) per the build-refusal-seed-live pattern. |

### Supporting (existing CLIs to mirror)

| Asset | Purpose | When to use |
|-------|---------|-------------|
| `engine/scripts/gate_action.py` | thin argv→`gate.evaluate`→JSON, `logged_call`-wrapped | The template for the new `apply_action.py` CLI shape (argparse, `dataclasses.asdict`, `end_fields["status"]` from `isinstance(result, Refusal)`). |
| `engine/scripts/classify_poll.py` / `classify_dryrun.py` | thin response→typed JSON | Pattern for serializing a typed result to stdout. |
| `engine/scripts/inbox.py` | already appends a line to `state/decisions.md` | Reference for the decisions.md append pattern (D-11 log seam). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `data/actions_ledger.jsonl` (append-only JSONL) | SQLite / Supabase | JSONL mirrors the repo's existing `data/*.json` + `logs/*.jsonl` convention; Supabase is deferred to Phase 3.5. JSONL is the right call now. |
| `poll_action_status` (tenacity, 20 attempts) | hand-rolled `while` loop | The primitive already exists, is tested, and terminal-on-FAILED. Do NOT rebuild. |
| New `ProposedAction` fields | a separate `WriteRequest` type | `ProposedAction` is already the gate's input; extend it (entity_type, entity_id, params) so one type threads denylist → gate → build. |

**Installation:** No new dependencies. Everything needed (`pydantic 2.13.4`, `tenacity 9.1.4`, `polars 1.41.2`, `structlog 26.1.0`) is pinned in `engine/pyproject.toml`. `cd engine && uv run pytest` is the test command.

**Version verification:** No new packages installed → no registry verification or slopcheck required for this phase (see Package Legitimacy Audit).

## Package Legitimacy Audit

> This phase installs **no** external packages. All code is hand-written engine Python reusing already-pinned deps (`pydantic`, `tenacity`, `polars`, `structlog`, `pytest`).

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | No new installs — audit N/A. |

**Packages removed due to slopcheck [SLOP] verdict:** none (no installs).
**Packages flagged as suspicious [SUS]:** none (no installs).

## Architecture Patterns

### Recommended Module / File Layout

```
engine/src/habibos/
├── apply.py            # NEW — the apply spine: build → denylist → gate → cap → ledger
│                       #       lookup → FIND → dryRun → apply → poll → echo → log
├── denylist.py         # NEW (or a function in apply.py) — owned-ASIN refuse-gate
├── ledger.py           # NEW (or in apply.py) — actions_ledger.jsonl read/write + hash
├── result.py           # EXTEND — ProposedAction gains entity_type/entity_id/params;
│                       #          add AppliedResult + any new Refusal codes
├── gate.py             # reuse verbatim (margin gate auto-passes spend-down)
├── lifecycle.py        # reuse verbatim (classify_dryrun / classify_poll)
├── find_cache.py       # reuse verbatim (write / lookup); enforce the A2 staleness dial here
├── datadoe.py          # reuse verbatim (poll_action_status, ACTION_* enum)
└── logging.py          # reuse verbatim (logged_call)

engine/scripts/
└── apply_action.py     # NEW — thin CLI mirroring gate_action.py

data/
└── actions_ledger.jsonl  # NEW — append-only idempotency ledger (gitignored like logs/?)

engine/tests/
├── test_apply.py       # NEW — the spine, canary, batch-step contract
├── test_denylist.py    # NEW — own-ASIN refusal (or in test_apply.py)
├── test_ledger.py      # NEW — idempotency no-op + in-flight resume
└── fixtures/           # NEW — actions_start_dryrun_pause.json, negative-create dryRun,
                        #       bid-down dryRun, *_FIND echo fixtures, a seed ledger
```

**Decision the planner must make:** whether to keep the denylist + ledger as separate modules or as functions inside `apply.py`. Recommendation: **separate `ledger.py` and `denylist.py`** so each has its own focused `test_*.py` (mirrors the one-module-one-test convention: `gate.py`/`test_gate.py`, `find_cache.py`/`test_find_cache.py`). The spine in `apply.py` orchestrates them.

### Pattern 1: The Apply Spine (linear, typed, refuse-or-proceed at every step)

**What:** A single `apply(action: ProposedAction, ...) -> AppliedResult | Refusal | GateRefusal` function that threads the action through each gate, short-circuiting on the first refusal (mirrors `gate.evaluate`'s branch-order discipline). The agent supplies the MCP-call results (dryRun response, actionId, poll responses, echo) — Python never opens a socket.

**When to use:** Every reversible write. The batch (D-03) calls it once per campaign-pause and once per negative-keyword add.

**Decomposition (each a small, separately-testable function):**
```
build_payload(action)            -> dict        # per action_type; schema-pinned
denylist_check(action, owned)    -> None|GateRefusal(own_asin_denied)   # D-06/D-07
magnitude_check(action, cfg)     -> None|GateRefusal(over_cap)          # D-02 seeded permissive
ledger_lookup(action)            -> None|LedgerHit(actionId)|InFlight(actionId)  # D-10
# (agent: actions_start dryRun:true) -> resp
classify_dryrun(resp)            -> Proceed|Refusal   # reuse lifecycle
# (agent: actions_start dryRun:false) -> {actionId}   # the real write
poll_to_terminal(get_status)     -> PollOutcome|Refusal  # poll_action_status + classify_poll
# (agent: *_FIND echo) -> resp
confirm_echo(action, find_resp)  -> None|Refusal
ledger_write(action, actionId, status)  -> None        # WRITE-07
log_decision(action, actionId)   -> None               # WRITE-06 (decisions.md + brain/raw)
```

### Pattern 2: The Poll Loop (drive the Phase 6 primitive to terminal)

**What:** The spine calls `datadoe.poll_action_status(get_status)` where `get_status` is a zero-arg callable that the agent re-invokes (`actions_get(actionId)`) and `classify_poll` buckets. The loop already caps at 20 attempts with exponential jitter backoff (`initial=1, max=15` seconds) and terminates on the pinned `ACTION_TERMINAL` set — so an in-flight status never spins forever and an unmodeled status refuses.

**Recommended documented defaults (Claude's discretion):**
- **Interval/backoff/max-attempts:** reuse `poll_action_status` exactly as built — `stop_after_attempt(20)`, `wait_exponential_jitter(initial=1, max=15)`. Do not invent new numbers. After 20 attempts without terminal, surface an `unresolved_in_flight` refusal carrying the `actionId` so it can be resumed (D-10 in-flight resume) — never silently assume success.
- **Resume:** if `ledger_lookup` finds an in-flight `actionId` for the same hash, **skip `actions_start` entirely** and re-enter the poll loop on that `actionId` (D-10).

### Pattern 3: Idempotency Ledger (`data/actions_ledger.jsonl`, content-hash identity D-10)

**Identity:** `sha256` over a canonical JSON of `{entity_type, entity_id, action_type, normalized_params}` — **NOT date** (so re-pausing an already-paused campaign is always a no-op).

**"Normalized params" per action type (recommendation — pin exact field names against `actions_details_schema_get`):**
| action_type | normalized_params (the params that define identity) |
|-------------|------------------------------------------------------|
| pause campaign | `{"state": "PAUSED"}` (the target state; entity_id = campaignId) |
| add exact negative kw | `{"keyword": "<lowercased trimmed text>", "matchType": "NEGATIVE_EXACT"}` (entity_id = the owning campaignId/adGroupId) |
| bid-down | `{"bid": <new bid, rounded to cents>}` (entity_id = targetId/keywordId) |

Normalize: lowercase + strip whitespace on keyword text; round bids to 2 dp; sort dict keys before hashing. Document the normalization in the module docstring (it is load-bearing — a different normalization changes identity).

**Recommended record schema (one JSON object per line):**
```json
{
  "hash": "sha256:…",
  "entity_type": "campaigns",
  "entity_id": "CMP-1000000000003",
  "action_type": "pause",
  "normalized_params": {"state": "PAUSED"},
  "action_id": "ACT-…",
  "status": "COMPLETED",
  "ad_product": "SPONSORED_PRODUCTS",
  "applied_at": "2026-06-23T14:02:11Z",
  "marketplace": "CA"
}
```

**Lookup semantics:**
- hash → COMPLETED entry present → **no-op** (`LedgerHit`), do not re-fire.
- hash → entry with an in-flight `status` (PENDING/IN_PROGRESS/WAITING_*) → **resume at poll** on its `action_id`, never re-fire start (D-10).
- no entry → proceed.

Append-only (mirrors `logs/external-calls.jsonl`); newest-wins on duplicate hash; never edit past lines (mirrors `state/decisions.md` discipline).

### Pattern 4: Own-ASIN Denylist Gate (EXEC-01, D-06/D-07)

**What:** Before BUILD→DRYRUN, extract the target ASIN(s) from the proposed write and refuse (hard `GateRefusal`, code e.g. `own_asin_denied`) if any is in the owned set read from `sku_catalog.toml`.

**Owned set source:** every `[sku."..."]` row's `asin` value in `engine/config/sku_catalog.toml` (read with `tomllib`, same as `gate._load_catalog`). Today that file has 16 rows / 16 ASINs.

**The extraction challenge (planner must resolve):** a *pause* or *bid-down* on an owned campaign does NOT carry a target ASIN to deny — the denylist's real job (EXEC-01) is to refuse **advertising an owned product on our own product page** (a Sponsored Display product-target / a product-attribute target whose target value is an owned ASIN). So the denylist applies to **ad-creation / targeting writes**, not pauses. For Phase 8's reversible set the denylist is mostly a **guard rail that will fire on a future ADD**, plus B07TV972JT (the named exclusion). The plan should: (a) define how an ASIN is extracted from each payload shape (target `expression`/`value` fields — pin against `actions_details_schema_get`), (b) refuse if extracted ASIN ∈ owned set, (c) for pause/bid-down where no ASIN is present, pass cleanly (nothing to deny). **Note:** B07TV972JT is NOT currently a row in `sku_catalog.toml` (the file has 16 owned ASINs, none is B07TV972JT) — see Open Questions Q4.

### Pattern 5: Canary One-Time Confirm (D-08/D-09)

**What:** The very first real apply of the phase requires a one-time manual confirm; subsequent applies auto-apply. The cleanest mechanism that does NOT make every apply interactive:

**Recommendation — a ledger/marker file, not a per-call prompt:** a one-row marker file `data/phase8_canary_confirmed` (or a `canary_confirmed` sentinel entry in the ledger). The CLI takes a `--confirm-canary` flag:
- If the marker is absent and `--confirm-canary` is NOT passed → refuse with `canary_unconfirmed` ("first reversible apply of the phase requires --confirm-canary; this is the one-time canary gate, D-08").
- If `--confirm-canary` is passed → proceed, then write the marker.
- If the marker is present → auto-apply, no confirm needed (D-09).

This keeps the gate **one-time and explicit** (the operator passes the flag once for the canary pause) without prompting on every batch action. Document the marker location as the dial.

### Anti-Patterns to Avoid

- **Re-rolling the poll loop / classifier:** `poll_action_status` + `classify_poll` exist and are tested. Drive them; do not rewrite.
- **Confirming via DataDoe export:** reconcile ONLY via `actions_get`→terminal + `*_FIND` echo. A next-day export (≤24h lag) is NEVER a confirmation — `classify_poll` already refuses an export "FAILED" status as `unknown_status`.
- **Clamping an over-cap move:** the magnitude cap refuses (typed `GateRefusal`), never clamps to the limit (mirror GATE-04).
- **Date in the idempotency hash:** identity is entity+action+params, NOT date (D-10) — a date would defeat the no-op-on-rerun guarantee.
- **Logging the seller UUID:** `logged_call` never receives it; decisions.md / brain notes never inline it (CLAUDE.md hard rule 5).
- **Silent org-disabled failure:** a `412 disabled` HTTP refusal must surface as a typed refusal at execution time, not a retry or a swallow (`datadoe-query` SKILL §5).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| In-flight→terminal polling | a `while True` poll loop | `datadoe.poll_action_status` | Tested tenacity primitive built in Phase 6 for exactly this; terminal-on-FAILED, capped, backoff+jitter. |
| dryRun PROCEED/STOP decision | inline `if status == ...` | `lifecycle.classify_dryrun` | Hand-written, pytest-covered, validates nested `validation.{valid,issues}` shape, refuses on drift. |
| actions_get status bucketing | inline status compare | `lifecycle.classify_poll` | Pinned enum, refuses unmodeled status, surfaces error message verbatim. |
| FIND-before-write / echo | re-reading FIND JSON ad hoc | `find_cache.lookup` / `write` | Newest-wins, drift-on-missing-id, typed miss refusal. |
| External-call telemetry | bare `print`/log | `logging.logged_call` | One `.start`/`.end`, no-secret guarantee, error-still-emits. |
| Margin verdict | recompute TACOS in the spine | `gate.evaluate` | Money logic must be the one hand-written core (CLAUDE.md hard rule 3). |
| Typed refusals | bare `None`/`raise` | `result.Refusal` / `GateRefusal` | The anti-fabrication grammar; the verifier checks for it. |

**Key insight:** Phase 8 is ~80% wiring of proven substrate. The genuinely-new, must-be-hand-written-and-tested pieces are narrow: the ledger hash + lookup, the denylist extraction+refuse, the seeded-permissive cap, the canary marker, and the decisions.md/brain log seam. Everything else is calling Phase 6/7 functions in the right order.

## Runtime State Inventory

> Phase 8 is a **rename/refactor-adjacent execution phase** that creates new runtime state (the ledger) and depends on external service config (DataDoe Settings→Actions). Inventory below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `data/actions_ledger.jsonl` (NEW) — the idempotency ledger; created on first apply. `data/ads_*_find_*.json` (existing) — FIND-cache files the spine reads for IDs + echo. | New file: define schema (Pattern 3), decide gitignore (recommend gitignore like `logs/`, since it carries `actionId`s — but it is the idempotency truth, so the planner must decide tracked-vs-runtime; **recommend tracked or backed-up** so idempotency survives a clone). |
| Live service config | **DataDoe → Settings → Actions** org-enable for: campaign-state (pause), negative-keyword create, target-state (bid-down). **OFF by default.** This is a UI/DB setting NOT in git. The real applies (canary + batch) are BLOCKED until Rami enables them. | **Blocking precondition** — surface as a runtime `412 disabled` refusal at execute time; plan a `checkpoint:human` task for Rami to flip the switches before the canary. |
| OS-registered state | None — the desktop app runs while the Mac is open; no cron, no scheduler, no OS-registered tasks (unattended scheduling is explicitly out of scope per REQUIREMENTS.md). | None — verified by REQUIREMENTS.md "Out of Scope: Unattended cron scheduling". |
| Secrets/env vars | `$AMAZON_CA_SELLER_ID` (the seller UUID, in `.env`, gitignored) — passed to `actions_start`/`actions_get` by the AGENT, never by Python, never logged. No new secret introduced. | None — code change only ensures the UUID never enters `logged_call` fields / decisions.md / brain notes (existing hard rule). |
| Build artifacts | `engine/` is an editable `uv`/setuptools package; new modules (`apply.py`, `ledger.py`, `denylist.py`) are picked up via `pythonpath = ["src"]` — no reinstall needed. New scripts are run via `uv run python scripts/apply_action.py`. | None — no egg-info / compiled artifact rename. |

**Live campaignIds / entity IDs:** come from the **FIND cache** (`data/ads_campaigns_*_find_*.json`), NOT from `sku_catalog.toml`. The batch must FIND the 4 dead-SKU campaigns live (the agent runs `*_FIND`, caches, then the spine `lookup`s) before pausing. The campaign IDs in `state/decisions.md` (the 2026-06-17 manual moves) are prose, not machine IDs — they are NOT a substitute for a live FIND.

## Common Pitfalls

### Pitfall 1: Fabricating the payload schema
**What goes wrong:** Writing `build_payload` against guessed field names (`{"campaign_state": "paused"}` vs the real `{"state": "PAUSED"}`).
**Why it happens:** The live schema was NOT reachable read-only in this research session.
**How to avoid:** A Wave-0 reconnaissance task: for each action type, call `actions_details_schema_get` (read-only) AND a `actions_start dryRun:true` round-trip, capture the validated payload as a fixture, THEN write `build_payload` against it. The `datadoe-query` SKILL already documents the live-confirmed `CAMPAIGNS_UPDATE` caveat (send only mutable fields; do NOT echo `adProduct` — the validator rejects it even though the schema lists it).
**Warning signs:** A `dryRun` returning `validation.valid:false` with a field-name issue.

### Pitfall 2: The negative-keyword action shape (dedicated create vs target-state write)
**What goes wrong:** Assuming a negative is a `TARGETS_UPDATE` state write when it may be a dedicated negative-create (`AMAZON_ADS_TARGETS_ADD` with `NEGATIVE_EXACT` match, or a campaign/ad-group-level negative target).
**Why it happens:** Amazon Ads models negatives as negative *targets* (campaign- or ad-group-level), not as a "state" on an existing positive keyword. The `datadoe-query` SKILL lists `TARGETS_ADD` but does not pin the negative-match payload.
**How to avoid:** Pin via `actions_details_schema_get` for the targets action type; confirm whether the match type is `NEGATIVE_EXACT` / `negativeExact` and whether it attaches at campaign or ad-group level. Document the answer before building the harvest step. (Claude's discretion item — must be pinned, not guessed.)
**Warning signs:** A negative "applied" but the search term still serves (wrong level/shape).

### Pitfall 3: Stale FIND cache shadowing a fresh entity (the A2 staleness window)
**What goes wrong:** A days-old `ads_campaigns_*_find_*.json` satisfies a `lookup` whose campaign was since changed in-console; the spine writes against a stale ID/state.
**Why it happens:** `find_cache.lookup` is newest-wins but Phase 6 deliberately deferred the staleness *rejection* window to Phase 8 (Assumption A2 — the docstring says so).
**How to avoid (Claude's discretion — recommended default):** enforce a **24h (same-day) staleness window** — reject a cache file whose date tail is older than `today` for write-bearing lookups (reversible writes still want a fresh FIND). Make the window a documented dial (e.g. `find_cache_staleness_hours = 24` in `thresholds.toml`, or a module constant with a comment). Surface a `stale_find_cache` refusal when exceeded — never a silent accept. Implement the check in `find_cache.lookup` (or a thin wrapper) so it is one tested place.
**Warning signs:** A FIND-echo (step 9) that does NOT reflect the just-applied change.

### Pitfall 4: The org-disabled wall (412) treated as a code failure
**What goes wrong:** The canary apply errors with "Action is disabled for this organization" and the spine treats it as a bug.
**Why it happens:** DataDoe Settings→Actions is OFF by default (verified live 2026-06-20, `brain/raw/2026-06-20`); this is a 4th gate beyond our own approval.
**How to avoid:** The spine must classify a `412` as a clean typed refusal (`action_type_disabled`) that surfaces the org-enable instruction verbatim and does NOT retry (`datadoe-query` SKILL §5). Plan a `checkpoint:human` for Rami to enable the reversible set before the canary.
**Warning signs:** `actions_start dryRun:false` rejected while `dryRun:true` validated cleanly.

### Pitfall 5: Two of the four dead SKUs are absent from `sku_catalog.toml`
**What goes wrong:** The plan assumes the denylist or any catalog read covers all four dead SKUs; in fact only `9Z-KUHZ-FU2I` and `FX-M8MA-MMSA` are in `sku_catalog.toml`. `ZK-4NDS` is in the documented "inactive remnant group (no COGS)" and is intentionally ABSENT; `VH-ZTOC` is not in the file at all.
**Why it happens:** The catalog only includes SKUs with a reviewed landed COGS (D-04 reconciliation, 16 SKUs).
**How to avoid:** The stop-the-bleed batch pauses **campaigns** (found via live FIND), which does NOT require those SKUs to be in the catalog — a pause is spend-decreasing and the gate auto-passes without a catalog read. So this is fine for the pause. But the plan must NOT route the dead-SKU identity through the catalog. The denylist (own-ASIN) is a separate concern. Document that the batch's campaign list comes from FIND + the runbook (`brain/raw/2026-06-16`, the 5 manual moves in `decisions.md`), not from a catalog lookup.
**Warning signs:** A `sku_not_in_catalog` refusal on a pause (would be a bug — pauses must not read the catalog).

## Code Examples

> All examples below are PATTERNS from the existing repo. The DataDoe payload shapes are **placeholders to be pinned** via `actions_details_schema_get` + `dryRun:true` (Pitfall 1/2).

### Reuse: the poll loop primitive (already built — drive it)
```python
# Source: engine/src/habibos/datadoe.py:65-82 (VERIFIED in repo)
@retry(
    stop=stop_after_attempt(20),
    wait=wait_exponential_jitter(initial=1, max=15),
    retry=retry_if_result(_action_not_terminal),
)
def poll_action_status(get_status) -> str:
    """Poll until ACTION_TERMINAL. get_status is a zero-arg callable returning the status."""
    return get_status()
# The spine: agent re-runs actions_get(actionId); each response → classify_poll for the typed
# PollOutcome; poll_action_status owns the loop/backoff/cap.
```

### Reuse: spend-down auto-passes the margin gate (no config read)
```python
# Source: engine/src/habibos/gate.py:149-156 (VERIFIED in repo)
if not action.is_spend_increasing:           # delta_spend <= 0  (pause/negative/bid-down)
    return GateVerdict(projected_tacos=None, ceiling=None,
                       contribution_margin=None, auto_pass=True)
```

### New: ledger hash + lookup (recommended)
```python
# Pattern — NEW in engine/src/habibos/ledger.py
import hashlib, json
def action_hash(entity_type: str, entity_id: str, action_type: str, params: dict) -> str:
    canonical = json.dumps(
        {"entity_type": entity_type, "entity_id": entity_id,
         "action_type": action_type, "normalized_params": params},
        sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
# lookup scans data/actions_ledger.jsonl newest-last; COMPLETED hash → no-op,
# in-flight hash → resume at poll on its action_id (D-10).
```

### New: thin CLI shape (mirror gate_action.py)
```python
# Pattern — engine/scripts/apply_action.py mirrors gate_action.py:72-102 (VERIFIED template)
with habibos_logging.logged_call("apply_action", marketplace=args.marketplace) as end_fields:
    result = apply.apply(action, ...)        # the spine
    end_fields["status"] = "refused" if isinstance(result, (Refusal, GateRefusal)) else "applied"
json.dump(dataclasses.asdict(result), sys.stdout)
```

### Reference: the decisions.md log line format (D-11)
```
# Source: state/decisions.md (VERIFIED — existing format)
YYYY-MM-DD | area | SKU/campaign | change | rationale | expected impact | result
# Phase 8 appends, e.g.:
2026-06-23 | ppc | [SKW] Baklava (CMP-…) | Paused whole campaign via apply spine (actionId ACT-…) | dead FX-M8MA, $8.83/0 orders t90 | stops ~$9/mo dead spend | COMPLETED
```

## State of the Art

| Old (Phases 6-7) | Current (Phase 8) | Impact |
|------------------|-------------------|--------|
| `classify_poll` classifies ONE response | `apply.py` drives the in-flight→terminal LOOP via `poll_action_status` | The full async write loop finally runs end-to-end (Phase 6 built the primitive "for Phase 8"). |
| `gate.evaluate` evaluates in isolation (CLI) | `gate.evaluate` is one step inside the spine | Reversible writes route through it and auto-pass (07 D-06). |
| No idempotency (read-only / proposal-only) | `data/actions_ledger.jsonl` content-hash ledger | Re-runs are no-ops; in-flight resumes (WRITE-07). |
| Writes were manual (Rami in chat, 2026-06-17) | Writes are engine-driven, gated, logged | The first autonomous-but-standing-approved reversible writes (D-01). |

**Deprecated/outdated:** nothing — this is additive. The manual 2026-06-17 PPC moves in `decisions.md` are the runbook precedent, not code to replace.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is REQUIRED.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.3 (dev dep in `engine/pyproject.toml`) |
| Config file | `engine/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["src"]`, `addopts="-ra"`) |
| Quick run command | `cd engine && uv run pytest tests/test_apply.py -x` |
| Full suite command | `cd engine && uv run pytest` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| WRITE-03 | end-to-end reversible write: build→dryRun(Proceed)→apply→poll-to-COMPLETED→echo | unit (mocked agent responses via fixtures) | `pytest tests/test_apply.py::test_reversible_write_end_to_end -x` | ❌ Wave 0 |
| WRITE-03 | poll loop drives in-flight→terminal via `poll_action_status` | unit | `pytest tests/test_apply.py::test_poll_loop_to_terminal -x` | ❌ Wave 0 |
| WRITE-03 | dryRun STOP short-circuits before any `dryRun:false` | unit | `pytest tests/test_apply.py::test_dryrun_refusal_blocks_apply -x` | ❌ Wave 0 |
| WRITE-06 | applied write appends a decisions.md line + brain/raw note with actionId | unit (tmp_path-monkeypatched paths) | `pytest tests/test_apply.py::test_apply_logs_decision_and_brain -x` | ❌ Wave 0 |
| WRITE-07 | a COMPLETED-hash re-run is a no-op (no second actions_start) | unit | `pytest tests/test_ledger.py::test_completed_hash_is_noop -x` | ❌ Wave 0 |
| WRITE-07 | an in-flight actionId resumes at poll, never re-fires start | unit | `pytest tests/test_ledger.py::test_inflight_resumes_at_poll -x` | ❌ Wave 0 |
| WRITE-07 | hash is identity over entity+action+params, NOT date | unit | `pytest tests/test_ledger.py::test_hash_excludes_date -x` | ❌ Wave 0 |
| EXEC-01 | own-ASIN payload → hard GateRefusal(own_asin_denied) pre-dryRun | unit | `pytest tests/test_denylist.py::test_own_asin_refused -x` | ❌ Wave 0 |
| EXEC-01 | a pause (no target ASIN) passes the denylist cleanly | unit | `pytest tests/test_denylist.py::test_pause_passes_denylist -x` | ❌ Wave 0 |
| EXEC-01 | denylist reads owned ASINs from sku_catalog.toml | unit | `pytest tests/test_denylist.py::test_owned_set_from_catalog -x` | ❌ Wave 0 |
| SC-5 (D-02) | magnitude-cap mechanism exists + refuses over-cap when cap is set | unit | `pytest tests/test_apply.py::test_magnitude_cap_refuses_when_set -x` | ❌ Wave 0 |
| SC-5 (D-02) | seeded permissive: reversible passes the cap at any magnitude | unit | `pytest tests/test_apply.py::test_magnitude_cap_seeded_permissive -x` | ❌ Wave 0 |
| WRITE-03 | canary one-time confirm gates the first apply, then auto | unit | `pytest tests/test_apply.py::test_canary_one_time_confirm -x` | ❌ Wave 0 |
| WRITE-05 (reuse) | a 412/disabled or ERROR poll surfaces a clean typed refusal, no retry | unit | `pytest tests/test_apply.py::test_disabled_action_refuses -x` | ❌ Wave 0 |
| A2 | a stale FIND cache file is rejected for a write-bearing lookup | unit | `pytest tests/test_find_cache.py::test_stale_cache_refused -x` | ❌ Wave 0 (extend existing) |

### Sampling Rate
- **Per task commit:** `cd engine && uv run pytest tests/test_apply.py tests/test_ledger.py tests/test_denylist.py -x` (sub-second).
- **Per wave merge:** `cd engine && uv run pytest`.
- **Phase gate:** full suite green before `/gsd:verify-work`; plus the **live canary** (D-08) — one real pause applied → polled to COMPLETED → FIND-echo confirmed → reconciled — which is a manual acceptance step gated behind the org-enable precondition, NOT an automated test.

### Wave 0 Gaps
- [ ] `tests/test_apply.py` — the spine, poll loop, canary, log, cap, disabled-action (WRITE-03/06, SC-5)
- [ ] `tests/test_ledger.py` — idempotency no-op + in-flight resume + date-excluded hash (WRITE-07)
- [ ] `tests/test_denylist.py` — own-ASIN refusal + pause-passes + owned-set-from-catalog (EXEC-01)
- [ ] `tests/fixtures/` — `actions_start_dryrun_pause.json`, negative-create dryRun, bid-down dryRun, `*_FIND` echo fixtures, a seed `actions_ledger.jsonl` (all sanitized, no seller UUID; mirror the existing `dryrun_validated.json` / `actions_get_completed.json` style). **These payload fixtures must be captured from a live `actions_details_schema_get` + `dryRun:true` round-trip in a Wave-0 reconnaissance task — not fabricated.**
- [ ] Extend `tests/test_find_cache.py` for the A2 staleness window.
- No framework install needed (pytest present).

## Security Domain

> `security_enforcement` not explicitly `false` in config → included.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | The agent (MCP) holds auth; Python opens no socket. |
| V4 Access Control | yes | The 4-gate chain (connection, dryRun, our approval, org-enable) + the denylist + the canary are the access controls on real writes. |
| V5 Input Validation | yes | `pydantic` validate-or-raise on every agent-handed response (`lifecycle`, `find_cache`); the gate refuses on missing/zero inputs. |
| V6 Cryptography | partial | `hashlib.sha256` for the idempotency hash — a non-secret content hash, standard library, not hand-rolled crypto. |
| V7/V8 Logging & Secrets | yes | `logged_call` NEVER receives the seller UUID; decisions.md / brain notes never inline it; `$AMAZON_CA_SELLER_ID` stays in `.env` (gitignored). |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Double-apply on re-run (over-spend or repeated mutation) | Tampering | content-hash idempotency ledger (D-10) — COMPLETED hash → no-op. |
| Writing against a stale/fabricated entity ID | Spoofing/Tampering | FIND-before-write + A2 staleness window → `stale_find_cache` refusal. |
| Advertising an owned ASIN on our own page | Tampering (self-cannibalization) | own-ASIN denylist hard refusal pre-dryRun (EXEC-01). |
| Seller-UUID leak into logs/notes | Information Disclosure | `logged_call` no-secret guarantee; reviewed log fields. |
| Reversible move killing a winner | Denial of (own) Service | magnitude-cap mechanism (seeded permissive now, tightenable dial — D-02). |
| Treating a stale export as write confirmation | Tampering (false reconcile) | reconcile ONLY via `actions_get`→terminal + FIND-echo (WRITE-05). |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The DataDoe `actions_start` payload for a campaign pause is a campaign-state write `{"campaignId", "state": "PAUSED"}` sending only mutable fields (no `adProduct`). [ASSUMED — from `datadoe-query` SKILL live-confirmed `CAMPAIGNS_UPDATE` caveat; MUST pin via `actions_details_schema_get` + dryRun] | Standard Stack, Code Examples | A wrong field name → dryRun `valid:false`; caught at dryRun, not in production, but blocks the spine. |
| A2 | A negative keyword is added via a TARGETS_ADD-style negative-target create (campaign- or ad-group-level, `NEGATIVE_EXACT` match), NOT a state write on a positive keyword. [ASSUMED — Amazon Ads models negatives as negative targets; MUST pin via `actions_details_schema_get`] | Pitfall 2 | Wrong shape → negative "applies" but term still serves; wastes a batch step. |
| A3 | A bid-down is a target/keyword `bid` write on a targetId/keywordId. [ASSUMED — MUST pin via schema] | Pattern 3 | Wrong field → dryRun fails. |
| A4 | The reusable poll loop (`stop_after_attempt(20)`, `wait_exponential_jitter(initial=1,max=15)`) is the right cadence for Amazon action settlement. [VERIFIED: repo `datadoe.py` — but the *adequacy* of 20 attempts for a slow action is ASSUMED] | Pattern 2 | A genuinely slow action could exhaust 20 attempts → surfaces `unresolved_in_flight` (resumable), not a silent failure — acceptable. |
| A5 | 24h / same-day is a sane `find_cache` staleness window for write-bearing lookups (A2 / Assumption A2). [ASSUMED — Claude's discretion] | Pitfall 3 | Too long → stale ID risk; too short → needless re-FIND. Documented dial mitigates. |
| A6 | `data/actions_ledger.jsonl` should be tracked/backed-up (not gitignored) so idempotency survives a clone. [ASSUMED — recommendation; planner/operator decides] | Runtime State Inventory | If gitignored and lost, a re-run could double-apply. Recommend tracked or backed up. |
| A7 | The own-ASIN denylist primarily guards future ADD/targeting writes; for Phase 8's pause/bid-down set it passes cleanly (no target ASIN present). [ASSUMED — from EXEC-01 intent + payload semantics] | Pattern 4 | If a reversible payload DOES carry an owned ASIN target, extraction logic must catch it — pin extraction against schema. |

## Open Questions

1. **Exact payload schema per reversible action type (HIGH priority).**
   - Known: the action types are `AMAZON_ADS_CAMPAIGNS_UPDATE` (pause-state), a TARGETS action for negatives, a TARGETS/keyword action for bid-down; send only mutable fields; do NOT echo `adProduct` on `CAMPAIGNS_UPDATE`.
   - Unclear: the exact field names + nesting per type, and the negative-match attachment level (campaign vs ad-group).
   - Recommendation: a **Wave-0 reconnaissance task** — agent calls `actions_details_schema_get` (read-only) for each of the three action types AND runs a `actions_start dryRun:true` round-trip, captures the validated payloads as sanitized fixtures, then `build_payload` is written against them. This is the documented pin point; do NOT fabricate fields.

2. **`ProposedAction` shape extension.**
   - Known: today `ProposedAction(sku, action_type, delta_spend, marketplace)` — no entity_id, no entity_type, no params.
   - Unclear: how to thread the campaignId/targetId + params for the build without breaking the existing gate CLI contract (`test_gate_action.py`).
   - Recommendation: ADD optional fields (`entity_type`, `entity_id`, `params: dict`) with defaults so the Phase 7 gate CLI still passes (the gate ignores them; only the spine reads them). Verify `test_gate.py` / `test_gate_action.py` stay green.

3. **`delta_spend` for a pause / negative.**
   - Known: the gate auto-passes any `delta_spend <= 0`. A pause/negative is spend-decreasing.
   - Recommendation: the spine sets `delta_spend = 0` (or a negative estimate) for pause/negative so `is_spend_increasing` is False and the gate auto-passes. Bid-down likewise ≤ 0. Document that the spine, not the operator, sets the sign for reversible actions.

4. **B07TV972JT is not in `sku_catalog.toml`.**
   - Known: D-06 says "B07TV972JT is one row in that set, not a special case" — but the file's 16 owned ASINs do NOT include B07TV972JT.
   - Unclear: is B07TV972JT an owned ASIN that should be ADDED to `sku_catalog.toml`, or is the denylist's owned set a *superset* (all ~30 owned ASINs, some without COGS) sourced differently?
   - Recommendation: the planner should confirm with Rami whether B07TV972JT (and the full ~30-ASIN owned set) belongs in `sku_catalog.toml` or in a dedicated `owned_asins` list. D-06 says "full set of ~30 owned ASINs" but the catalog has 16 (COGS-gated). **The denylist owned-set source may need to be broader than the gate's catalog** — flag for discuss/plan. This is the single most important pre-plan clarification.

5. **Dead-SKU campaign identity (2 of 4 SKUs absent from catalog).**
   - Resolved by Pitfall 5: the batch pauses *campaigns* found via live FIND, not SKUs via catalog. The plan must route campaign identity through FIND + the runbook (`brain/raw/2026-06-16`, `decisions.md` 2026-06-17), never through `sku_catalog.toml`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pytest | all tests | ✓ | >=9.0.3 (dev dep) | — |
| tenacity | poll loop | ✓ | 9.1.4 (pinned) | — |
| pydantic | response validation | ✓ | 2.13.4 (pinned) | — |
| polars | gate frame parse | ✓ | 1.41.2 (pinned) | — |
| structlog | logged_call | ✓ | 26.1.0 (pinned) | — |
| uv | run/test runner | ✓ (repo uses `uv run`) | — | — |
| DataDoe MCP (`actions_start`/`_get`/`_details_schema_get`/`*_FIND`) | live dryRun, schema pin, real apply | ✗ in THIS research session (DataDoe MCP not in the researcher's toolset) | — | Schema pinned at plan/execute time by the agent that HAS the DataDoe MCP. |
| DataDoe Settings→Actions org-enable | the real canary + batch apply | ✗ (OFF by default — operator must enable) | — | None — **blocking precondition**; surface as `412` refusal + a human checkpoint. |

**Missing dependencies with no fallback:**
- DataDoe Settings→Actions org-enable for the reversible action set — Rami must flip it before the canary apply (D-08) and the batch (D-03). The BUILD + dryRun + all automated tests do NOT need it.

**Missing dependencies with fallback:**
- Live DataDoe schema read in *this* session — fallback is the documented `actions_details_schema_get` + `dryRun:true` Wave-0 task run by the executing agent (which has the MCP). The repo's SKILL + Phase 6 fixtures already constrain the shapes enough to plan.

## Project Constraints (from CLAUDE.md)

- **DataDoe data layer is READ-ONLY** for analysis; the ONLY write surface is the gated `actions_start` path. Python NEVER opens a socket — the agent makes all MCP calls (the seam).
- **Money/write logic is hand-written, reviewed, and pytest-covered** (`engine/`). The apply spine, ledger, denylist, and cap are money/write-touching → must be hand-written + tested. `cd engine && uv run pytest` stays green. NEVER auto-generated, NEVER computed in prose.
- **Never invent a number or a threshold.** Missing → typed refusal (`no_threshold_set`, `find_cache_miss`, `sku_not_in_catalog`, `own_asin_denied`, `stale_find_cache`, `canary_unconfirmed`, `action_type_disabled`). NEVER a default, NEVER a clamp.
- **No autonomous writes to Amazon without approval.** Reversible moves ride STANDING approval (D-01) within the (seeded-permissive) cap and STILL log (D-11). The canary (D-08) is a one-time explicit confirm. Every applied action logs to `state/decisions.md`.
- **Secrets in `.env`** — `$AMAZON_CA_SELLER_ID` (the seller UUID) NEVER inlined in code/skills/committed files, NEVER passed into `logged_call`, decisions.md, or brain notes.
- **Every external call (`actions_start`/`actions_get`/`*_FIND`) is logged + cited** via `logged_call` (one `.start` + one `.end`).

## Sources

### Primary (HIGH confidence — read directly from the repo this session)
- `engine/src/habibos/lifecycle.py`, `find_cache.py`, `datadoe.py`, `gate.py`, `result.py`, `logging.py` — the substrate signatures + patterns the spine reuses.
- `engine/scripts/gate_action.py`, `answer_tacos.py`, `classify_poll.py`, `classify_dryrun.py` — the thin-CLI template.
- `engine/tests/test_gate_action.py`, `test_find_cache.py`, `test_lifecycle.py` — the RED→GREEN test style + fixture conventions.
- `engine/config/sku_catalog.toml`, `thresholds.toml` — the owned-ASIN set + cap dial (and the 16-vs-30 ASIN gap).
- `engine/tests/fixtures/*.json` — the pinned dryRun / actions_get / FIND response shapes.
- `engine/pyproject.toml` — pinned deps + pytest config.
- `.planning/phases/08-.../08-CONTEXT.md` — locked decisions D-01..D-11.
- `.planning/ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md` — phase scope, SC-1..5, WRITE/EXEC reqs.

### Secondary (MEDIUM confidence — repo operational intel)
- `.claude/skills/datadoe-query/SKILL.md` §"Write actions" — the four `actions_*` tools, the live-confirmed terminal enum, the `CAMPAIGNS_UPDATE` "no adProduct" caveat, the 412/402/429 HTTP refusal rules, reconcile-via-status discipline.
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` — the 4-gate chain + Settings→Actions org-enable precondition (verified live 2026-06-20).
- `brain/raw/2026-06-16_ppc-coverage-gap.md` + `state/decisions.md` (2026-06-17 manual moves) — the dead-SKU runbook the batch executes.

### Tertiary (LOW confidence — must be pinned at plan/execute time)
- The exact `actions_start` payload schema per reversible action type — NOT reachable read-only this session; pin via `actions_details_schema_get` + `dryRun:true` (Open Question 1, Assumptions A1-A3).

## Metadata

**Confidence breakdown:**
- Standard stack (reuse map): HIGH — every primitive read directly from the repo.
- Architecture (spine, ledger, gates, canary): HIGH — design follows the established refuse-never-default grammar; idempotency design pinned to D-10.
- Payload schemas: MEDIUM — constrained by SKILL + fixtures, but the live schema was not reachable this session; flagged for a Wave-0 pin task.
- Pitfalls: HIGH — three of five are verified facts from the repo (catalog gap, org-enable wall, A2 deferral).

**Research date:** 2026-06-22
**Valid until:** 2026-07-22 (stable substrate) — but re-pin the DataDoe payload schemas at execute time (the live API spec can change; the SKILL was last live-verified 2026-06-21).
