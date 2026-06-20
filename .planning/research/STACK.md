# Stack Research — Milestone v2.0 (Gated PPC Write Path)

**Researched:** 2026-06-20 · **Mode:** Ecosystem (subsequent-milestone, build-on-existing)
**Scope note:** This is the v2.0 milestone stack research. The v1.0 milestone STACK.md lives at
`.planning/research/STACK.md` (dated 2026-06-09) and was intentionally **not** overwritten.

**Headline:** This milestone needs **near-zero new third-party libraries**. The write path is a
new *module + CLI* inside the existing `engine/`, reusing the already-pinned stack
(`pydantic 2.13.4`, `polars 1.41.2`, `tenacity 9.1.4`, `structlog 26.1.0`). The work is
**code-shaped, not dependency-shaped** — extend the proven typed-result / refusal / logged-call
pattern to writes. Resisting new dependencies *is* the architecturally correct answer here.

Files read to ground this: `.planning/PROJECT.md`,
`engine/pyproject.toml` · `engine/uv.lock` · `engine/config/thresholds.toml` ·
`engine/src/habibos/{result,tacos,thresholds,logging,datadoe}.py` · `engine/scripts/answer_tacos.py`,
`deliverables/ppc-rebuild-execution-plan_2026-06-20.md`,
`brain/raw/2026-06-20_datadoe-write-path-gating.md`,
`.claude/skills/ppc-analysis/SKILL.md` · `.claude/skills/datadoe-query/SKILL.md`,
`state/decisions.md`.

---

## Stack Additions (what to add, why, version)

The honest finding: **no new PyPI dependency is required.** Everything maps to a library already
pinned in `engine/pyproject.toml` / `engine/uv.lock`. The "additions" are new engine modules +
CLIs, not packages.

| Need | Use (already pinned) | Version | Why no new dep |
|------|----------------------|---------|----------------|
| Typed write request / result / refusal | `pydantic` | 2.13.4 (HIGH, lockfile) | Same `BaseModel` + frozen-dataclass pattern as `result.py`/`tacos.py`. A `WriteAction` / `WriteResult` / `WriteRefusal` mirror `Answer`/`SkuRow`/`Refusal`. |
| Async poll of `actions_get` (start→COMPLETED) | `tenacity` | 9.1.4 (HIGH, lockfile) | `datadoe.poll_status()` already polls a terminal-status set with `wait_exponential_jitter`; extend `TERMINAL` to the action lifecycle. |
| Read SKU components for the margin gate | `polars` | 1.41.2 (HIGH, lockfile) | Same CSV→frame parse + window-sum the gate consumes from the premium Profit-by-SKU export (reuse `tacos.parse`). |
| One-event-in/one-out call logging | `structlog` | 26.1.0 (HIGH, lockfile) | `logging.logged_call` already gives the `*.start`/`*.end` JSON-line contract; wrap each `actions_start`/`actions_get` the same way. |
| Idempotency key generation | Python **stdlib** `hashlib`/`uuid` | 3.12 stdlib | Deterministic key = `sha256(action_type|entity_id|field|proposed_value|date)`; no library. |
| Config / thresholds | stdlib `tomllib` via `thresholds.read()` | 3.12 stdlib | Add per-tier margin/TACOS keys to `config/thresholds.toml`; the reader already refuses on missing. |
| CLI wiring | stdlib `argparse` + `json` | 3.12 stdlib | Mirror `scripts/answer_tacos.py` exactly. |
| Tests | `pytest` (dev) | ≥9.0.3 (HIGH, lockfile) | Money-logic contract stays green; the gate is the new tested core. |

**The write call itself is NOT a Python HTTP client.** Per the seam already documented in
`datadoe.py` ("A parallel Python HTTP client is FORBIDDEN"), the Hermes **agent** invokes the
DataDoe MCP `actions_start` / `actions_get` tools. Python's job is to **build the validated
payload, gate it, and interpret the returned status** — never to open a socket. Keep that seam.

> Do **not** add: an Amazon Ads SDK, `python-amazon-sp-api`, `boto3`, an HTTP client
> (`httpx`/`requests`), or an async framework. The MCP is the transport; adding one re-introduces
> the exact write surface the constitution forbids (PROJECT.md "Out of Scope": no custom SP-API MCP).

---

## Integration Pattern: actions_start lifecycle (start → poll actions_get → reconcile)

Verified surface (from `brain/raw/2026-06-20_datadoe-write-path-gating.md` and execution-plan §A):
`actions_start` is the single write entry point; companions `actions_get` (one action status),
`actions_list` (history), `actions_details_schema_get` (payload schema per type). It supports
`dryRun:true` → returns `status:VALIDATED, valid:true/false, issues:[]` **without executing**. The
real run (`dryRun:false`) returns an `actionId` (async) → poll `actions_get` to `COMPLETED`.

**The seven-step loop (engine-gated version of execution-plan §A):**

1. **FIND (read-only, agent/MCP).** `*_FIND` (one `adProduct` per request) → resolve live
   `campaignId / adGroupId / targetId / adId`. Cache to `data/` like the existing campaign pull
   (`data/ads_sp_campaigns_live_2026-06-20.json`).
2. **BUILD + GATE (Python engine — new).** Construct the typed `WriteAction`; run it through the
   **margin-gate** + **reversibility classifier**. A breach → `WriteRefusal` (never a clamped
   number — same discipline as `tacos._present_flag` returning "no threshold set").
3. **DRY-RUN (agent/MCP).** `actions_start(..., dryRun:true)` → expect `VALIDATED / valid:true`.
   The engine **interprets** the returned `issues:[]` (non-empty → refusal surfaced verbatim).
   This is the rehearsal the brain note proved works for `AMAZON_LISTINGS_UPDATE`.
4. **APPROVE.** Reversible (pause / negative / bid-down / budget-down) → **standing approval**,
   auto-proceed after a clean dry-run. Spend-up (bid-up / budget-up / new campaign / archive) →
   **explicit human approval** required (PROJECT.md autonomy decision).
5. **APPLY (agent/MCP).** `actions_start(..., dryRun:false, idempotencyKey:…)` → capture `actionId`.
6. **POLL (engine `tenacity` primitive).** `actions_get(actionId)` until terminal
   (`COMPLETED`/`FAILED`/`CANCELLED`) — extend `datadoe.poll_status`. **Never** retry a `FAILED`
   action forever (the existing `_not_terminal` terminal-set guard already encodes this).
7. **RECONCILE — via `actions_get` + console, NOT next-day exports.** Writes hit Amazon
   immediately but **DataDoe reporting lags ≤24h** (execution-plan §A.4). The source of truth that
   "it landed" is the `actionId` reaching `COMPLETED`, cross-checked against a live `*_FIND` echo
   and (operator) the Amazon console — **not** a next-day DataDoe export. Effect on ACOS/TACOS is
   measured later, once the lag clears, by the existing `answer_tacos` path.

**Error / retry / idempotency rules (design for these explicitly):**
- **Idempotency key on every `dryRun:false`.** A network hiccup between APPLY and the captured
  `actionId` must not double-apply a bid/budget. Deterministic key (stdlib `hashlib`). Persist a
  key→actionId map (append to `data/actions_ledger.jsonl`), and **check `actions_list` before
  re-firing** a key whose `actionId` was lost.
- **Org-enable is a hard precondition (gate #4).** The real run is rejected with *"Action is
  disabled for this organization"* unless the org owner enabled that action type in
  DataDoe → Settings → Actions (proven live 2026-06-20). Treat a disabled-action rejection as a
  **typed refusal with a clear unblock message**, not a retryable error.
- **Retry only transient statuses** (timeouts / poll-not-yet-terminal). `valid:false` from a
  dry-run, a disabled-action rejection, or a `FAILED` terminal status are **refusals, not retries**.
- **Low-reversibility actions (`CAMPAIGNS_REMOVE` = archive) get their own approved batch, last**
  (execution-plan §C Wave 5 / §E).

---

## Engine Margin-Gate Module (inputs, outputs, where it sits)

A new hand-written, pytest-covered module — **the v2.0 analogue of `tacos.py`**. It closes the
"write-safety gap" flagged in both the brain note (§Open engineering gap) and execution-plan §A.5
("No engine bid/budget gate yet").

**Where it sits:** `engine/src/habibos/margin_gate.py`, called by a new
`engine/scripts/gate_ppc_write.py` CLI (mirrors `answer_tacos.py`'s thin-wiring shape). It runs at
**loop step 2**, before any dry-run, so a sub-floor move never even reaches Amazon's validator.

**Inputs:**
- The proposed `WriteAction` (type, entity id, field, current→proposed value, SKU/ASIN it funds).
- Per-SKU contribution margin + TACOS components from the **premium Profit-by-SKU export**
  (`57a0cb319c`) — the same `*_sum` window components `tacos.py` already consumes (reuse `parse()`).
- Per-tier ceilings from `config/thresholds.toml` (**new keys to add**): margin-derived TACOS
  ceilings per tier — e.g. `tacos_ceiling_hero_pct`, `tacos_ceiling_maintain_pct`,
  `tacos_ceiling_thin_pct`, and a `min_net_margin_pct` floor (the ≥~15% net target). The SKU→tier
  map lives in `anabtawi-context` (already referenced by `thresholds.toml` comments).

**The gate logic (hand-written, the only money math here):**
- Derive each SKU's **TACOS ceiling from its own contribution margin** so net margin stays
  ≥ floor — *not* a flat 25%. (PROJECT.md: portfolio break-even ≈39% t30; winners up to ~25%;
  thin SKUs ≤~12%.) The $2,500→$10,000/25% instinct survives only as the aggressive-winner ceiling.
- **Refuse** any write that would push the SKU's projected TACOS over its tier ceiling, or any
  bid/budget increase that breaches the net-margin floor → typed `WriteRefusal` (reason + code,
  e.g. `over_tier_ceiling` / `sub_floor_margin`), surfaced **verbatim**, never silently clamped —
  the exact mirror of the TACOS breach refusal (`_present_flag`).
- **Missing threshold → refuse the write**, never a default (constitution hard rule 4; same as
  `thresholds.read()` returning `None`). A SKU absent from the export → "no data" → refuse to fund.

**Outputs:** a typed `GateResult` = `Approved(action, projected_tacos, tier, ceiling)` or
`WriteRefusal(reason, code)`. JSON on stdout (like `answer_tacos`), for the agent to render and the
approval spine to consume. The gate **decides eligibility**; it does **not** call Amazon.

---

## Daily Action Queue + Approval/Logging

**Daily ranked action queue (new generator).** A `tasks/ppc-queue-daily.md` prompt +
`engine/scripts/build_action_queue.py` helper that, each day:
1. Pulls the live PPC + profit windows (existing DataDoe sources, via the agent/MCP),
2. Runs the existing PPC analysis to produce candidate moves (pause / negative / bid / budget /
   new-campaign — the moves in execution-plan §A capability map),
3. Passes each candidate through the **margin-gate**, dropping/flagging refusals,
4. Emits a **dollar-ranked queue** (rank by $ impact, CLAUDE.md golden rule 4) tagged reversible vs
   spend-up, written to `deliverables/ppc-action-queue_{date}.md` (or `.xlsx`).

Each queue row: SKU/ASIN · campaign/entity id · action type · current→proposed · trailing
ACOS/TACOS (from the engine) · tier ceiling · projected effect · reversibility class · gate
verdict · idempotency key. The queue is **dry-run-first** — nothing in it has been applied.

**Approval spine (extends the existing reviewed-artifact pattern):**
- **Standing approval** for reversible moves (pause, add-negative, bid-down, budget-down): clean
  dry-run + passing gate → auto-apply. **Explicit approval** for bid-up / budget-up / new campaign /
  archive (`CAMPAIGNS_REMOVE`). Encode as a `reversibility` field on each `WriteAction`, set by a
  small classifier in the gate module.
- The approval token (which moves Rami OK'd) records in the ledger alongside the `actionId`.

**Logging spine (reuse, don't rebuild):**
- Wrap each `actions_start` / `actions_get` in `logging.logged_call` ("one in, one out" JSON line
  to `engine/logs/external-calls.jsonl`) — satisfies constitution rule 6 (every external call logged).
- On `COMPLETED`, append **one line to `state/decisions.md`** in the existing format
  (`date | ppc | campaign | change | rationale | expected impact | result`) — exactly as the 06-17
  retargeting/pause/launch rows already do — plus a durable `brain/raw/` note. Put the `actionId` +
  idempotency key in the `result` column so an applied write is traceable end-to-end.

---

## What NOT to Add (anti-scope)

| Don't add | Why (and what to do instead) |
|-----------|------------------------------|
| **A new database** (SQLite / Supabase tables for the action ledger) | Supabase is *deferred* (PROJECT.md). Use the existing file ledger: `state/decisions.md` + `brain/raw/` + a `data/actions_ledger.jsonl` for key→actionId. Don't pull schema work into this milestone. |
| **SP-API direct / Amazon Ads SDK / `python-amazon-sp-api` / `boto3`** | Explicitly superseded — DataDoe `actions_start` *is* the gated write path (PROJECT.md Key Decisions). A direct API re-opens the forbidden autonomous-write surface. |
| **Any HTTP client (`httpx`/`requests`) in Python** | Violates the documented seam in `datadoe.py`: the **agent/MCP** makes the call; Python builds+gates+interprets. |
| **A web UI / dashboard / Next.js** | Superseded by the Hermes desktop surface (PROJECT.md "Prior build note"). The queue is a `deliverables/` artifact, not an app. |
| **Listing writes (`AMAZON_LISTINGS_UPDATE`) / price writes** | PROJECT.md scope: **PPC writes only** this milestone. The validated baklava-bullets write stays queued for later; price needs its own margin gate first. |
| **Restock / inventory / catalog-refresh moves** | Out of scope — work existing FBA stock only (PROJECT.md). |
| **Portfolio objects** | No portfolio action exists in the API (execution-plan §A). Encode tier in campaign **name + tags**, or assign a manually-created `portfolioId` on create. Don't build around a capability the API lacks. |
| **An async framework / job scheduler** | The Mac-desktop runtime has no unattended cron (PROJECT.md constraints). The queue is on-demand/on-open; `tenacity` polling within a single agent turn suffices. |
| **Auto-generated money logic** | Constitution hard rule 3. The margin gate is hand-written + pytest-tested, like `tacos.py`. |

---

## Open Questions for Planning

1. **Margin-gate ceiling formula — exact derivation.** PROJECT.md gives the *posture* (net ≥~15%,
   break-even ≈39% t30, winners ≤25%, thin ≤12%) but not the closed-form TACOS-ceiling-from-margin
   equation, nor whether contribution margin comes from the premium export
   (`profit_sum/total_sales_sum`) or the `cogs` reconciliation. Pin both before coding the gate.
   *(The brain note flags two baklava ASINs already below the floor.)*
2. **New threshold keys + SKU→tier table.** `config/thresholds.toml` currently has only flat
   `acos_ceiling_pct`/`tacos_ceiling_pct`. Per-tier keys require the SKU→tier map in
   `anabtawi-context` to be **filled** (its comment says tier ceilings "activate once the SKU→tier
   table is filled"). Confirm it is filled.
3. **Idempotency-key persistence shape.** A `data/actions_ledger.jsonl`, or a new `state/` file? It
   must survive across desktop sessions, since APPLY→actionId can be interrupted.
4. **Reconciliation definition of "done."** Confirm policy: an action is "applied" when
   `actions_get → COMPLETED` (+ optional `*_FIND` echo), explicitly **not** when a next-day export
   reflects it (≤24h lag). Who/what closes the loop on the desktop — agent re-poll on next open?
5. **`actions_get` terminal-status enum.** The brain note confirms `VALIDATED` (dry-run) and the
   disabled-action rejection, but the full real-run terminal set (`COMPLETED`/`FAILED`/`CANCELLED`/
   `PENDING`?) should be confirmed via `actions_details_schema_get` and pinned into the extended
   `datadoe.TERMINAL` set in Phase 1 (empirical, like the DataDoe column verification was).
6. **Org-enable sequencing.** Real Ads writes are blocked until the org owner enables each Ads
   action type in DataDoe Settings > Actions. Which to enable first (recommend the reversible set:
   `CAMPAIGNS_UPDATE`, `TARGETS_UPDATE`, `TARGETS_ADD`, `ADS_UPDATE`), and is that a planning
   prerequisite or a Wave-0 step?
7. **Standing-approval boundary precision.** "Budget-down" is reversible but still moves spend —
   confirm it's standing-approval, and confirm bid-down has no floor where it silently kills a
   converting term (execution-plan flags "watch, don't negate" terms — bid-down, not pause).
