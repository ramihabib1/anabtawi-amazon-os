# Research Summary — Milestone v2.0 (Gated PPC Write Path)

**Synthesized:** 2026-06-20
**Sources:** STACK.md · FEATURES.md · ARCHITECTURE.md · PITFALLS.md (all dated 2026-06-20)
**Feeds:** requirements definition and roadmap phase structure

---

## The One-Paragraph Picture

Milestone v2.0 builds a PPC execution engine that sells through existing FBA stock via the DataDoe `actions_start` write path, governed by a per-SKU margin-tiered TACOS gate, with standing approval for reversible moves and explicit approval for any spend increase. The architecture is a direct extension of M1's proven discipline: the agent does I/O over MCP, hand-written Python owns the money truth. Three cross-cutting facts shape every design decision. First, the margin gate is the load-bearing safety core — a per-SKU TACOS ceiling derived from each SKU's own contribution margin (not a flat 25%) — and it must ship and be pytest-covered before any spend-up write is possible. Second, SP's 7-day and SB/SD's 14-day attribution windows versus DataDoe's ≤24h reporting lag force a two-class verdict model: act-now (stop-loss on obviously-dead campaigns, reversible, standing approval) versus judge-later (efficiency writes that require a matured attribution window before evaluation). Third, the safest build order follows the execution-plan waves in risk-ascending order — FIND/lifecycle substrate first (zero account risk), then the margin gate, then reversible writes (stop the bleed), then ranked spend-up with explicit approval, then new campaign chains, then archive hygiene last — because each wave is a hard predecessor to the next. The system adds zero new PyPI dependencies; it grows four to five new engine modules and four thin CLIs, all wired the same way as `answer_tacos.py`. (Sources: all four research files.)

---

## Stack Decisions (what to add / what to forbid)

### Add (new engine modules + CLIs, no new PyPI packages)

| Artifact | Role | Mirrors existing |
|---|---|---|
| `engine/src/habibos/actions.py` | Typed `ProposedAction` / `ActionBatch` / `ValidationResult` / `ApplyResult` | `result.py` |
| `engine/src/habibos/gate.py` | Margin gate: `evaluate(action, sku_margin, tier_ceiling) -> Allowed | GateRefusal` | `tacos.py` + `thresholds.py` |
| `engine/src/habibos/payload.py` | Build schema-valid `actions_start` JSON per action type from a `ProposedAction` | (new pure function) |
| `engine/src/habibos/lifecycle.py` | Classify dryRun response and `actions_get` poll status; reuses `datadoe.poll_status` terminal semantics | `datadoe.py` |
| `engine/src/habibos/queue.py` | Daily dollar-ranked action queue assembly | `tacos.classify` sort |
| `engine/src/habibos/idempotency.py` | Content-hash dedup; in-flight `actionId` resume vs re-fire | (new) |
| `engine/scripts/gate_action.py` | Thin CLI: proposed action + margin -> `Allowed`/`GateRefusal` JSON | `answer_tacos.py` pattern |
| `engine/scripts/build_payload.py` | Thin CLI: proposed action -> validated `actions_start` payload JSON | same |
| `engine/scripts/rank_queue.py` | Thin CLI: candidate actions -> dollar-ranked queue JSON | same |
| `engine/scripts/log_action.py` | Thin CLI: `ApplyResult` -> `decisions.md` line + `brain/raw/` note | same |
| `.claude/skills/ppc-execute/SKILL.md` | Write playbook: FIND -> build -> gate -> dryRun -> approve -> start -> poll -> reconcile -> log | extends `ppc-analysis` |
| `data/actions_ledger.jsonl` | Persistent idempotency-key -> actionId map (survives desktop sessions) | `data/*.csv` cache pattern |

### Modify (existing files)

| File | Change |
|---|---|
| `engine/config/thresholds.toml` | Add `[marketplace.CA.tiers]`: per-tier TACOS ceilings (hero <=~25%, maintain ~28%, thin <=~12%) + set `min_net_margin_pct` (currently empty "" — gate refuses until filled) |
| `anabtawi-context/SKILL.md` | SKU->tier/margin table must become machine-readable (gate hard dependency) |
| `.claude/skills/datadoe-query/SKILL.md` | Add write-action reference: `actions_start`/`actions_get`/`actions_list`/`actions_details_schema_get`, FIND-before-write, dryRun discipline |
| `.claude/skills/ppc-analysis/SKILL.md` | Hand off flagged waste/negatives/bid-downs as `ProposedAction`s rather than ending at prose |
| `state/decisions.md` | Fed by `log_action.py` with `actionId` + before/after on every applied write |
| `engine/tests/` | Add `test_gate.py`, `test_payload.py`, `test_lifecycle.py`, `test_queue.py`, `test_idempotency.py` |

### Forbid (the anti-scope is binding)

| Forbidden | Why |
|---|---|
| Amazon Ads SDK / `python-amazon-sp-api` / `boto3` | DataDoe `actions_start` IS the write path; direct API re-opens the forbidden autonomous-write surface |
| Any HTTP client (`httpx`/`requests`) in Python | Violates the seam in `datadoe.py`: agent/MCP makes the call; Python builds, gates, interprets |
| SQLite / Supabase schema for action ledger | Supabase deferred; use `data/actions_ledger.jsonl` |
| Web UI / Next.js | Superseded by Hermes desktop; queue is a `deliverables/` artifact |
| Listing writes, price writes | PPC-only milestone |
| Portfolio creation via API | No portfolio action exists in DataDoe |
| Async framework / job scheduler | Mac desktop constraint; no unattended cron; `tenacity` + on-demand suffices |
| Auto-generated money logic | Constitution hard rule 3; gate is hand-written + pytest-covered |

(Source: STACK.md "What NOT to Add"; FEATURES.md "Anti-Features")

---

## Capabilities: Table Stakes vs Differentiators vs Anti-Features

### Table Stakes (the spine — must exist before this milestone is real)

| # | Capability | DataDoe action(s) |
|---|---|---|
| T1 | propose -> dryRun -> approve -> apply -> reconcile loop | `actions_start dryRun:true/false` -> `actions_get(actionId)` |
| T2 | FIND primitives (live entity IDs before any write) | `CAMPAIGNS_FIND`, `AD_GROUPS_FIND`, `TARGETS_FIND`, `ADS_FIND` |
| T2b | Pause campaign / ad / keyword | `CAMPAIGNS_UPDATE`, `ADS_UPDATE`, `TARGETS_UPDATE` state:PAUSED |
| T3 | Add negative keyword / product target | `TARGETS_ADD negative:true` (per campaign; no shared-list object) |
| T4 | Bid change | `TARGETS_UPDATE bid` (down = standing; up = explicit + gated) |
| T5 | Budget change | `CAMPAIGNS_UPDATE budgets` (up = explicit + gated) |
| T6 | Placement bid adjustments | `CAMPAIGNS_UPDATE placementBidAdjustments` (gate hard: <=+900%) |
| T7 | Retarget product ad (swap dead-SKU ad for live SKU) | `ADS_REMOVE` + `ADS_ADD` |
| T8 | Build new campaign (chained) | `CAMPAIGNS_ADD` -> `AD_GROUPS_ADD` -> `ADS_ADD` -> `TARGETS_ADD` |
| T9 | Match-type-aware keyword targeting | `TARGETS_ADD` EXACT/PHRASE/BROAD; SP Auto close+loose |
| T10 | Archive graveyard campaigns | `CAMPAIGNS_REMOVE` (recoverable in console; NOT via API) |
| T11 | Reconcile via action status, NOT next-day exports | `actions_get(actionId)` + console; DataDoe lags <=24h |
| T12 | Log every applied action | append `state/decisions.md` + `brain/raw/` |

### Differentiators (where this milestone earns its keep)

| # | What | Why it matters |
|---|---|---|
| D1 | Per-SKU margin-tiered TACOS gate | A flat 25% is loss-making on thin SKUs. Two baklava ASINs already below the 20% floor. This closes the write-safety gap flagged in execution plan A.5. |
| D2 | Daily dollar-ranked action queue (pre-dry-run'd, gated) | Turns a one-off teardown into a standing operating rhythm. |
| D3 | Harvest loop (auto -> exact graduation + same-session source negation) | Root finding: no harvest loop, all AUTO paused. Campaign E is the seed. |
| D4 | Inventory-paced spend (6-week cover gate before any fund/scale) | GG-0DC1 at 1 FBA unit is the live example of what this prevents. |
| D5 | Reversibility-classed autonomy (standing vs explicit) | Fast on safe high-frequency moves; human on every dollar of new spend. |
| D6 | Partial-build detection + rollback for chained campaign writes | No atomicity guarantee across async chain; orphan ENABLED empty campaign spends. |

### Anti-Features (explicitly OUT)

- Listing-content writes, restock/catalog moves, SB/SD builds this milestone
- Autonomous spend-up without explicit human OK
- Portfolio creation via API (does not exist); shared-negative-list object (does not exist)
- Trusting next-day DataDoe exports to confirm a write landed
- Dynamic bidding up-and-down as default (default: down-only)
- Inventing a bid, budget, or threshold — missing threshold -> refuse with "no threshold set"

(Source: FEATURES.md "Table Stakes", "Differentiators", "Anti-Features")

---

## Architecture & Build Order (the seed for phases)

### Component seam (unchanged from M1, extended to writes)

```
Agent (Hermes) -- MCP --> DataDoe
       |                      |
       |  actions_start/get   |  (transport layer; agent-owned)
       |                      |
       v
  Python engine (truth layer; hand-written, tested)
  +-- payload.py     build the schema-valid JSON
  +-- gate.py        check margin ceiling BEFORE dryRun  <-- enforcement point
  +-- lifecycle.py   classify dryRun / poll responses
  +-- idempotency.py dedup + in-flight resume
  +-- queue.py       daily dollar-ranked candidate list
  +-- log_action.py  write COMPLETED result to decisions.md + brain/raw/
```

The seam is binding: Python never opens a socket. The agent does all I/O. Python builds, gates, and interprets.

### Write action lifecycle (8 steps)

```
0. FIND (read-only)  -> cache live entity IDs -> data/ads_*_find_*.json
1. BUILD  payload.build(action)        ProposedAction -> actions_start JSON
2. GATE   gate.evaluate(...)           margin ceiling check <- BEFORE dryRun, BEFORE Amazon sees it
3. DRYRUN actions_start(dryRun:true)   expect VALIDATED / valid:true / issues:[]
4. APPROVE reversible -> standing auto-proceed; spend-up / new-campaign / archive -> explicit human OK
5. START  actions_start(dryRun:false)  -> actionId; wrap in logged_call; record idempotency hash
6. POLL   actions_get(actionId)        until COMPLETED|FAILED|CANCELLED (no infinite spin)
7. RECONCILE via actions_get + console (NOT next-day DataDoe export)
8. LOG    log_action.py -> state/decisions.md line + brain/raw/ note
```

### Build order (5 phases, risk-ascending — mirrors execution-plan waves)

**Phase A — FIND + lifecycle substrate (zero account risk)**
Build `lifecycle.py` (dryRun/poll classifiers) + FIND wrappers + cache to `data/`. Extend `datadoe-query` SKILL with write-action reference. Confirms async loop works on no-ops; no write lands. Runbook Wave 0.

**Phase B — Margin gate (the safety core; hard prerequisite for any real write)**
Build `gate.py` + `actions.py` types + per-tier ceilings in `thresholds.toml` + machine-readable SKU->margin/tier + `gate_action.py` CLI + `test_gate.py`. Also build the attribution-maturity guard (two-class verdict model: act-now vs judge-later). Gate must refuse a sub-floor spend before `dryRun:false` is ever permitted. Closes the write-safety gap flagged in brain note and execution plan A.5.

**Phase C — Payload + apply spine + logging (reversible writes only)**
Build `payload.py` + `idempotency.py` + `log_action.py` + `ppc-execute` SKILL with standing approval for pause/negative/bid-down. First real writes = Runbook Wave 1 (stop the bleed): pause dead-SKU ads (~$279/mo, ~43% of spend, zero sales loss), negatives, bid-downs. Every action logs to `decisions.md` + `brain/raw/`.

**Phase D — Daily ranked queue + explicit-approval spend-up**
Build `queue.py` + `rank_queue.py`. Wire bid-up / budget-up / placement-up through explicit approval and the passing margin gate. Runbook Waves 2-3 (tune survivors, fund winners).

**Phase E — New campaign chains + archive hygiene (lowest reversibility, last)**
`CAMPAIGNS_ADD` chain with D6 partial-build rollback. `CAMPAIGNS_REMOVE` graveyard archive in its own separately-approved, last-run batch. Runbook Waves 4-5.

Ordering rationale: read-only substrate -> safety gate -> reversible writes -> ranked spend -> irreversible last. The gate is inserted as a hard predecessor to any spend increase. (Source: ARCHITECTURE.md "Suggested Build Order"; STACK.md "Engine Margin-Gate Module")

---

## Top Pitfalls and Their Prevention (ranked)

**1. Judging campaigns before attribution settles (CRITICAL)**
SP attributes up to 7 days after click; SB/SD up to 14 days. DataDoe's <=24h lag makes data look final when it is not. A daily standing-approval queue is exactly the cadence that destroys converting campaigns mid-window.
Prevention: engine tags every metric with window-age vs program type; refuses any pause/cut verdict on an immature window. Two-class verdict model: act-now (obviously-dead campaigns with inactive listings or zero lifetime orders) vs judge-later (efficiency verdicts requiring matured data). "3 clean days" means 3 days of matured data, not calendar days. (Source: PITFALLS.md #1)

**2. Flat TACOS bleeds margin on thin-margin SKUs (CRITICAL)**
Portfolio blended margin ~39% t30; two baklava ASINs already below the 20% contribution floor. A flat 25% TACOS is a guaranteed per-unit loss on thin SKUs, masked by fat-margin blended reporting.
Prevention: per-SKU TACOS ceiling derived from each SKU's own contribution margin to hold net >=~15%. Refuse any bid/budget write that would breach. Missing margin -> "no threshold set" -> refuse, never default. (Source: PITFALLS.md #2; FEATURES.md D1)

**3. Archive treated as reversible (HIGH)**
`CAMPAIGNS_REMOVE` = Amazon "archived." Recoverable only by hand in console, not via API. The graveyard cleanup touches 75+ IDs; one stale ID archives a live earner with no API undo.
Prevention: archive always last, always its own explicitly-approved batch. Pre-check: PAUSED + zero-spend >=30d before eligible. Two ENABLED graveyard candidates go pause -> observe -> archive across separate batches. (Source: PITFALLS.md #4)

**4. Skipping org-enable gate / firing dryRun:false blind (HIGH)**
Each action type is OFF by default in DataDoe Settings -> Actions. A real run against a disabled type is rejected with "Action is disabled for this organization."
Prevention: dryRun -> approve -> apply -> reconcile mandatory for every write. Pre-flight: confirm org-enable for each action type; queue marks blocked actions "blocked: org-enable required." Enable reversible set first. (Source: PITFALLS.md #10; STACK.md "Org-enable")

**5. Negative-keyword collateral damage (HIGH)**
`chocolate gift box` must be negated but `baklava gift box` converts and must stay positive. A phrase negative kills both.
Prevention: explicit keep-positive allowlist checked before any `TARGETS_ADD negative:true`. Default: negate EXACT only. "Watch, don't negate" terms (pistachio baklava, arabic sweets) -> bid-down, never negate. (Source: PITFALLS.md #5)

**6. Bidding against yourself (MEDIUM)**
"baklava" EXACT live in >=4 campaigns simultaneously; brand terms in 3. Internal auctions raise your own CPC.
Prevention: Wave-0 FIND builds a keyword->campaign inventory; duplicate-keyword check before any bid-up; consolidate to one owning campaign per term. (Source: PITFALLS.md #3)

**7. Targeting owned ASIN B07TV972JT (MEDIUM)**
Binding EXCLUDE rule: all owned ASINs on a hard never-target denylist. Any `TARGETS_ADD` payload containing an owned ASIN refused at validation, before dryRun. (Source: PITFALLS.md #7)

**8. Partial-build failure in chained campaign creation (MEDIUM)**
3-4 async actions in sequence; no atomicity. Mid-chain failure leaves an orphan ENABLED campaign that spends.
Prevention: dryRun the full chain; gate each step on prior COMPLETED + returned ID; on failure, pause/rollback the partial build immediately. (Source: PITFALLS.md #6; FEATURES.md D6)

---

## Blocking Preconditions Before Any Real Write (the gates the operator must clear)

These are hard blockers. No `dryRun:false` fires until each is resolved.

**Precondition 1 — `thresholds.toml` `min_net_margin_pct` is empty.**
The margin gate reads this value and refuses every write while it is "". Rami must set the real net-margin floor (~15%) before Phase B can pass the gate on anything. This is the single highest-priority config action before Phase B. (Source: ARCHITECTURE.md OQ7; STACK.md "Engine Margin-Gate Module")

**Precondition 2 — SKU->tier/margin table must become machine-readable.**
`anabtawi-context/SKILL.md` currently holds tier and margin data partly as prose. The gate needs a parseable structure (JSON/TOML row per SKU) to derive per-SKU ceilings. A SKU absent from this table causes a gate refusal on funding it — correct behavior, but the table must be complete before Wave 2 spend-up. (Source: ARCHITECTURE.md component map; STACK.md "Inputs"; FEATURES.md D1)

**Precondition 3 — Per-tier ceiling formula pinned.**
PROJECT.md gives the posture (net >=~15%, break-even ~39% t30, winners <=25%, thin <=~12%) but not the closed-form TACOS-ceiling-from-margin equation, nor whether contribution margin comes from the premium Profit-by-SKU export or a COGS reconciliation. Pin both before writing `gate.py`. (Source: STACK.md OQ1)

**Precondition 4 — Org-enable each Ads action type in DataDoe Settings -> Actions.**
Each type is OFF by default. Recommended sequence: enable CAMPAIGNS_UPDATE, TARGETS_UPDATE, TARGETS_ADD, ADS_UPDATE before Wave 1; hold CAMPAIGNS_ADD and CAMPAIGNS_REMOVE until their respective phases. (Source: STACK.md OQ6; PITFALLS.md #10)

**Precondition 5 — Portfolios decision resolved before Phase E.**
No portfolio-create action exists in DataDoe. Options: encode tier in campaign name + tags, or Rami creates 3 tier portfolios in Amazon Ads console once and the engine assigns `portfolioId` on new-campaign creation. Does not block Phase A-C; must be decided before Phase E. (Source: STACK.md OQ6; FEATURES.md "Anti-Features"; PITFALLS.md #9)

---

## Consolidated Open Questions for Requirements / Roadmap

**Q1 — Two-class verdict model: exact act-now vs judge-later boundary.**
Where is the line? Recommended: act-now = obviously-dead campaigns (inactive listing, zero lifetime orders, ENABLED on discontinued SKU); judge-later = efficiency verdicts (ACOS/TACOS trends needing a matured window). Formalize act-now criteria before building the attribution-maturity guard in Phase B. (PITFALLS.md OQ1; FEATURES.md OQ5)

**Q2 — Margin-gate ceiling formula and contribution-margin source.**
Closed-form TACOS-ceiling-from-margin equation not yet specified. Which export column is the authoritative per-SKU margin? Pin before `gate.py`. (STACK.md OQ1; ARCHITECTURE.md OQ2)

**Q3 — SKU->tier table completeness and machine-readable format.**
Confirm the table in `anabtawi-context` is filled; define the parseable format the gate reads. A gap means a gate refusal on every unfiled SKU. (STACK.md OQ2; ARCHITECTURE.md OQ2)

**Q4 — Standing-approval magnitude cap on bid-down and negatives.**
A -80% bid cut on a converting term is not meaningfully reversible in practice (rank/momentum loss). Define a magnitude ceiling (e.g. auto-apply <=30% cuts; route larger cuts to explicit review). Also confirm whether phrase/broad negatives require explicit approval while only exact negatives ride standing approval. (STACK.md OQ7; FEATURES.md OQ8; PITFALLS.md OQ5)

**Q5 — Projected TACOS input for new campaigns (no historical TACOS).**
The gate evaluates a proposed write against a SKU's margin ceiling. A new campaign has no historical TACOS. Define the spend assumption that seeds the projection before Phase E. (ARCHITECTURE.md OQ6; PITFALLS.md OQ4)

**Q6 — Idempotency-key persistence shape and dedup window.**
`data/actions_ledger.jsonl` is the recommended form. Define whether dedup is per-day or persistent cross-day and the `actions_list` lookback bound. (STACK.md OQ3; ARCHITECTURE.md OQ4)

**Q7 — Reconciliation definition of "done."**
Confirm binding standard: applied = `actions_get` COMPLETED (+ optional FIND echo), explicitly NOT the next-day DataDoe export. Define who/what closes the loop on the desktop (agent re-poll on next open). (STACK.md OQ4; ARCHITECTURE.md OQ5)

**Q8 — `actions_get` terminal-status enum.**
Full real-run terminal set should be confirmed via `actions_details_schema_get` and pinned into `datadoe.TERMINAL` in Phase A. (STACK.md OQ5)

**Q9 — Harvest-loop graduation thresholds.**
Operator dials, not invented constants. Set in `state/targets.md` before Phase D/E. Practitioner norm: >=3 orders, ACOS <= tier target, >=5 weekly searches. (FEATURES.md OQ3)

**Q10 — Inventory-cover threshold binding value and velocity source.**
Rebuild says "6 weeks." Confirm as binding gate value in `state/targets.md` and define the velocity source and window for the cover calculation. (FEATURES.md OQ4)

---

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Stack | HIGH | All additions map to already-pinned lockfile deps; write-path seam verified live 2026-06-20 |
| Features / action map | HIGH | DataDoe action surface verified in execution plan; T1-T12 each maps to a real proven action type |
| Architecture | HIGH | Grounded in read source + verified write-path facts; extends M1 proven seam |
| Pitfalls (account-specific) | HIGH | Sourced from our own audit with live dollar figures and IDs |
| Pitfalls (engineering patterns) | MEDIUM | Practitioner-consensus + our own flagged gaps |
| Margin-gate formula | MEDIUM | Posture documented; closed-form equation and margin source not yet pinned (Q2 is Phase B prerequisite) |
| Harvest loop thresholds | MEDIUM | Mechanics confirmed; exact graduation criteria are operator dials not yet set in `state/targets.md` |

**Overall: HIGH on what to build and in what order; MEDIUM on two gate inputs (margin formula Q2, graduation thresholds Q9) that must be resolved in requirements before Phase B and Phase D can be fully specified.**

---

## Sources

- `.planning/PROJECT.md` — milestone scope, mission metric, key decisions, hard rules, out-of-scope
- `deliverables/ppc-rebuild-execution-plan_2026-06-20.md` — DataDoe action map A, hard limits, execution waves
- `deliverables/ppc-rebuild_2026-06-12.md` — teardown: waste, negatives, internal competition, dependency order, change sheet
- `deliverables/ppc-new-campaigns_2026-06-16.md` — 5 coverage-gap campaigns A-E, harvest loop, gated set
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` — 4-gate chain, org-enable block, dryRun discipline, open engineering gap
- `engine/src/habibos/{tacos,result,thresholds,datadoe,logging}.py` — M1 engine patterns to mirror
- `engine/scripts/answer_tacos.py` — thin-CLI-over-MCP seam (template for all new scripts)
- `engine/config/thresholds.toml` — current state (per-tier ceilings not yet added; `min_margin_pct` empty)
- `.claude/skills/{ppc-analysis,datadoe-query}/SKILL.md` — existing skill surface
- Amazon Ads attribution windows: SP 7-day, SB/SD 14-day (Bidx, Intentwise, Feedvisor; multi-source; HIGH)
