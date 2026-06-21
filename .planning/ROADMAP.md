# Roadmap: Habib OS — Milestone 1

**Created:** 2026-06-08
**Milestone:** 1 — Foundation + read-only PPC/profit intelligence (conversational, on the Hermes Mac desktop app)
**Core Value:** From the desktop workspace I can ask real PPC/profit questions and get correct answers against live DataDoe data — with zero risk of the system changing anything on Amazon.
**Granularity:** standard
**Project Mode:** mvp (Vertical MVP)

## Shape

A shared **Foundation** (connections, source map, Supabase schema, `~/.hermes` context, seeded config) followed by four **vertical acceptance-question slices**, each delivering ONE end-to-end answerable question against live data and ending with a manual Seller-Central spot-check. The DataDoe wrapper, persistence/store layer, FX-reconciled margin, and the full trust spine (provenance, config-driven thresholds, wrapped/logged calls) are built as part of the FIRST slice (TACOS by SKU) so they are proven on a real question, then reused by every later slice. No phase introduces a write path to Amazon.

## Supabase deferral (2026-06-08 — operator decision)

Supabase is **deferred**, not removed (operator lacked account/MCP access at build time, and DataDoe premium "Profit by SKU" being live-verified ENABLED means correct margin/ACOS/TACOS answers come straight from DataDoe without the DB). Consequences:

- **Phase 1 plans 01-02 (schema) and 01-04 (config seed) are DEFERRED.** Foundation is otherwise complete.
- **Thresholds live in a local file** `config/thresholds.toml` (operator-confirmed values; the "never invent a threshold → refuse" rule still holds) instead of the `config` table.
- **No persistence / decision_ledger yet** — early slices answer live-only. This is acceptable through Phase 3 (read-only questions). The **decision ledger becomes load-bearing at Phase 4** (negative-keyword *proposals*), so Supabase must be re-inserted before Phase 4.
- A new **Phase 3.5: Supabase truth store** (the deferred 01-02 + 01-04 work, plus migrating `config/thresholds.toml` → `config` table) will be inserted before Phase 4 once account/MCP access is sorted.

## Phases

- [ ] **Phase 1: Foundation** - Connections verified read-only, seller UUID cached, DataDoe source map recorded, Supabase truth schema + seeded config, `~/.hermes` persona/context loaded and backed up
- [x] **Phase 2: Slice — TACOS by SKU (+ trust spine)** - Operator asks "what's my TACOS by SKU" and gets correct, provenance-cited ACOS/TACOS/ROI from live data, spot-checked against Seller Central; builds the reusable wrapper/store/reconcile/spine (completed 2026-06-09)
- [ ] **Phase 3: Slice — Wasted ad spend** - Operator asks "where am I wasting ad spend" and gets a ranked, provenance-cited answer from live data, 2500-row cap handled, spot-checked
- [ ] **Phase 4: Slice — Search terms to negate** - Operator asks "which search terms should I negate" and gets a proposal-only candidate list with the spend/conversion data behind each, spot-checked
- [ ] **Phase 5: Slice — Budget-capped campaigns** - Operator asks "which campaigns are budget-capped" and gets flagged campaigns (approximate, labelled as such) from live data, spot-checked

## Phase Details

### Phase 1: Foundation
**Goal**: A trustworthy substrate exists — verified read-only connections, an empirically-confirmed DataDoe source map, the Supabase truth store with real seeded thresholds, and the agent's persona/business context loaded locally and backed up — so the first acceptance question can be answered against live data.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: CONN-01, CONN-02, CONN-03, DATA-01, DATA-02, DATA-03, DATA-04, CTX-01, CTX-02, CTX-03
**Success Criteria** (what must be TRUE):
  1. From the Hermes desktop workspace, the operator can verify DataDoe, Supabase, and Gmail/Drive MCP connections respond and DataDoe is confirmed read-only; the amazon.ca seller UUID is resolved and cached to `.env` as `AMAZON_CA_SELLER_ID` (never inlined).
  2. A DataDoe source map exists recording, per confirmed source, its columns, ad-program scope (which of SP/SB/SD), date-column timezone basis, and whether premium "Profit by SKU & Date" is enabled — produced empirically via `exports_sources_get`, not assumed.
  3. The five Supabase tables (`sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config`) exist via reviewed Alembic migrations with `pgvector` enabled, marketplace a first-class dimension; `metric_snapshots` is unique on `(marketplace, seller_sku, snapshot_date)` and carries `captured_at` + `datadoe_export_id`; `cogs` is an SCD with per-row FX (`unit_cost`, `cost_currency`, `fx_rate`, `fx_as_of`).
  4. `config` is seeded with the operator's real thresholds (min margin %, ACOS ceiling, days-of-cover) keyed by `(key, marketplace)` — an empty config is treated as a fabrication invitation and is not allowed to stand.
  5. `~/.hermes` holds the version-controlled business context and SOUL.md persona (numbers-first, terse, recommends-never-acts, never invents pricing/thresholds); the `~/.hermes` + Supabase backup target and schedule are decided and documented.
**Plans**: 4 plans (2 complete, 2 deferred to Phase 3.5)
- [x] 01-01-PLAN.md — Project scaffold + Wave 0 pytest stubs, verify read-only MCP connections, cache seller UUID, empirical DataDoe source map (CONN-01/02/03)
- [~] 01-02-PLAN.md — **DEFERRED (Supabase)** → Phase 3.5. Alembic five-table truth schema (pgvector-first), push to live Supabase, schema verification (DATA-01/02/03)
- [x] 01-03-PLAN.md — SOUL.md persona + business context to `~/.hermes`, backup target/cadence decided + documented + restore tested (CTX-01/02/03)
- [~] 01-04-PLAN.md — **DEFERRED (Supabase)** → Phase 3.5. Seed thresholds — interim home is `config/thresholds.toml`; migrates to `config` table in Phase 3.5 (DATA-04)

### Phase 2: Slice — TACOS by SKU (+ trust spine)
**Goal**: The operator can ask "what's my TACOS by SKU" in the workspace and get correct, provenance-cited ACOS/TACOS/ROI against live DataDoe data — and in delivering it, the reusable DataDoe wrapper, persistence layer, FX-reconciled margin, and the full anti-fabrication trust spine are built and proven on a real question.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: DATA-05, PROF-01, PROF-02, TRUST-01, TRUST-02, TRUST-03, TRUST-04
**Supabase-deferral note:** Until Phase 3.5, this slice runs **live-only** — per-SKU ACOS/TACOS/ROI come directly from the DataDoe premium Profit-by-SKU source (already enabled), thresholds from `config/thresholds.toml`, and provenance = DataDoe export id. The `metric_snapshots` persistence, `cogs` FX-reconciliation, and `decision_ledger` parts of criteria 2–4 move to Phase 3.5 (they need the DB). The user-facing answer + anti-fabrication refusal + wrapped/logged calls still apply.
**Success Criteria** (what must be TRUE):
  1. From the workspace, asking "what's my TACOS by SKU" returns per-SKU ACOS/TACOS/ROI read from the DataDoe premium Profit-by-SKU source (never hand-rolled in prose), each ratio labelled with its definition and its source; the sanity guard holds (TACOS ≤ ACOS for the same SKU).
  2. A DataDoe export is persisted end-to-end into `metric_snapshots` against live data (idempotent re-pull, stamped with `captured_at` + export id), and per-SKU true margin reconciles DataDoe Profit against `cogs` with FX — stamping which source was authoritative (`datadoe_profit` vs `cogs_fallback`) and falling back cleanly, labelled, when premium is unavailable or misses a SKU.
  3. Every numeric answer cites provenance (DataDoe export id + config row); on a failed/empty export the system refuses ("no data") rather than substituting a number; every threshold is read from Supabase `config` and a missing threshold yields refusal, not a default.
  4. Every external call (DataDoe export, Supabase) is wrapped and logged.
  5. The TACOS-by-SKU answer is spot-checked manually against Seller Central and signed off; numbers match the known ~30-SKU CA catalog (no marketplace bleed).
**Plans**: 3 plans
- [x] 02-01-PLAN.md — Trust-spine substrate (result/thresholds/logging/datadoe) + Wave 0 install/pythonpath/gitignore + seed thresholds.toml (TRUST-02, TRUST-03)
- [x] 02-02-PLAN.md — Money-logic core tacos.py (read-not-recompute ratios, sanity guard, no-data sentinels, refusal, flagging) + answer_tacos.py CLI + fixture + tests (PROF-01, PROF-02, TRUST-01)
- [x] 02-03-PLAN.md — tacos-by-sku SKILL.md + DataDoe MCP wiring + live acceptance pull (locks A1/A2/A3, re-points real fixture) + TRUST-04 spot-check (DATA-05, PROF-01, TRUST-04)

### Phase 3: Slice — Wasted ad spend
**Goal**: The operator can ask "where am I wasting ad spend" and get a correct, provenance-cited, ranked answer against live data — reusing the spine from Phase 2 and standing up the first PPC primitive, which handles the DataDoe 2500-row cap by design.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: PPC-01, PPC-04, TRUST-04
**Success Criteria** (what must be TRUE):
  1. From the workspace, asking "where am I wasting ad spend" returns zero-conversion / high-ACOS spend ranked by spend, each line citing provenance (export id + the config threshold applied) and stating its program scope (e.g. "SP per Search-Term Performance") rather than implying "all advertising."
  2. The PPC search-term/spend export handles the 2500-row cap without silent truncation — via server-side `groupBy`/aggregation or `skip` pagination, detecting an exactly-2500-row result as "more exist" — so totals are not undercounted.
  3. Thresholds (e.g. zero-conversion spend trigger, ACOS ceiling) are read from `config`, never invented; a failed/empty export refuses rather than substituting a number.
  4. The wasted-spend answer is spot-checked manually against Seller Central (spend reconciles to Campaign Manager for the window) and signed off.
**Plans**: TBD

### Phase 4: Slice — Search terms to negate
**Goal**: The operator can ask "which search terms should I negate" and get a proposal-only candidate list with the spend/conversion data behind each — reusing the spine and PPC substrate, with strict proposal (never autopilot) phrasing.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: PPC-02, TRUST-04
**Success Criteria** (what must be TRUE):
  1. From the workspace, asking "which search terms should I negate" returns a candidate list drawn from Search Term Performance only (customer search term, its matched keyword, the campaign, and the spend/orders behind each) — not confusing customer search terms with targeting keywords.
  2. Every candidate is phrased as a proposal requiring human approval (recommendation voice, never "I negated…"), and is recorded to `decision_ledger` as a read-only recommendation; no write path to Amazon exists.
  3. The spend threshold gating a candidate is read from `config` and cited; a failed/empty export refuses rather than substituting numbers; provenance (export id) accompanies every candidate.
  4. The negative-keyword candidate list is spot-checked manually against Seller Central and signed off.
**Plans**: TBD

### Phase 5: Slice — Budget-capped campaigns
**Goal**: The operator can ask "which campaigns are budget-capped" and get flagged campaigns — approximate and explicitly labelled as such (no native Lost-IS column in DataDoe) — against live data, completing the four Milestone-1 acceptance questions.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: PPC-03, TRUST-04
**Success Criteria** (what must be TRUE):
  1. From the workspace, asking "which campaigns are budget-capped" returns flagged campaigns derived from campaign budget (CAMP-RAW) vs daily spend pattern (PERF-CAMP), each flag explicitly labelled "approximate — no native Lost-IS column" so the operator is not misled into treating it as exact.
  2. Each flag cites provenance (export id + the budget/spend rows behind it) and reads any threshold from `config`; a failed/empty export refuses rather than guessing.
  3. The budget-capped flags are spot-checked manually against Seller Central (campaign budgets and spend) and signed off — completing manual sign-off across all four M1 acceptance questions.
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 active (01-02, 01-04 deferred → P3.5) | ✓ Complete (DB deferred) | 2026-06-08 |
| 2. Slice — TACOS by SKU (+ trust spine) | 3/3 | Complete   | 2026-06-09 |
| 3. Slice — Wasted ad spend | 0/0 | Not started | - |
| 4. Slice — Search terms to negate | 0/0 | Not started | - |
| 5. Slice — Budget-capped campaigns | 0/0 | Not started | - |

---
*Roadmap created: 2026-06-08*
*All 21 v1 requirements mapped. No write path to Amazon in any phase.*

---

# Roadmap: Habib OS — Milestone v2.0 (Execution Era — Gated PPC Write Path)

**Created:** 2026-06-20
**Milestone:** v2.0 — Turn reviewed PPC artifacts into real, approval-gated account changes via the DataDoe Ads write actions (`actions_start`), selling through existing FBA stock at a per-SKU margin-tiered TACOS. PPC writes only.
**Core Value:** Move the units already in FBA at a healthy, margin-derived TACOS (not a flat number) — every account change is `dryRun` → approve → apply → reconcile → log, governed by a per-SKU margin gate that protects net margin ≥ ~15%.
**Granularity:** standard
**Numbering:** Continues from Milestone 1 (which ended at Phase 5). Phases 6–10. M1 phases 1–5 above are preserved intact.

## Shape (M2)

A **risk-ascending** build: a zero-account-risk async substrate (FIND + lifecycle) is proven first, then the **margin gate** ships as the load-bearing safety core (a hard predecessor to any spend increase, refusing while the min-margin threshold is empty), then the first **real writes** are only reversible stop-the-bleed moves under standing approval, then a **daily ranked queue** wires explicit-approval spend-up through the passing gate, and finally the **lowest-reversibility** moves (new-campaign chains, then graveyard archive in its own separately-approved batch) run last. The seam from M1 is reused verbatim: the agent does all MCP I/O; hand-written, pytest-covered Python builds the payload, gates on margin, classifies the async responses, and writes the decision log. No autonomous spend-up; every write logs to `state/decisions.md` + `brain/raw/`.

## Constitution constraints (binding across all M2 phases)

- **DataDoe data layer stays READ-ONLY** for *analysis*; the only write surface is the gated `actions_start` path. Python never opens a socket (the agent does MCP).
- **Money math is hand-written + pytest-covered** (`engine/`); the gate is the new money-logic contract and `cd engine && uv run pytest` must stay green. Never auto-generate gate logic.
- **Never invent a number or a threshold.** Missing min-margin / tier ceiling / SKU margin → typed refusal ("no threshold set"), never a default 25%.
- **No autonomous writes.** Reversible moves (pause / negative / bid-down) ride *standing* approval within a magnitude cap and still log; spend-up / new campaigns / archive require *explicit* approval.
- **Every write follows** FIND → build → gate → dryRun → approve → apply → poll `actions_get` → reconcile (via `actions_get` COMPLETED + console, **never** next-day DataDoe ≤24h exports) → log.

## Blocking preconditions (operator must clear before the phases they gate)

| Precondition | Gates | Phase |
|---|---|---|
| Operator sets `min_net_margin_pct` (~15%) in `thresholds.toml` (currently empty `""`) | Gate passes on nothing until set | **Phase 7** (and any spend-up in 9–10) |
| SKU→tier/contribution-margin table made machine-readable in `anabtawi-context` | Gate refuses any unfiled SKU | **Phase 7** (binding before spend-up in Phase 9) |
| Org-enable each Ads action type in DataDoe Settings → Actions (reversible set first; hold CAMPAIGNS_ADD/REMOVE) | A real run against a disabled type is rejected | **Phase 8** (reversible set), **Phase 10** (ADD/REMOVE) |
| Portfolios decision resolved (tier in name+tags, or Rami creates 3 console portfolios) | Clean new-campaign structure | **Phase 10** |
| Per-tier ceiling formula + contribution-margin source pinned (Q2) | `gate.py` cannot be written without it | **Phase 7** |

## Phases (M2)

- [ ] **Phase 6: FIND + Lifecycle Substrate** - Prove the async write loop on no-ops: dryRun harness, `*_FIND` ID caching, `actions_get` poll classification, reconcile-not-via-export discipline — zero account risk
- [ ] **Phase 7: Margin-Tiered Safety Gate** - The engine safety core ships and is pytest-covered: per-SKU margin → TACOS ceiling, refuses any spend-up that breaches the net-margin floor, refuses while min-margin threshold empty (hard predecessor to any real spend)
- [ ] **Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed** - First real writes land: pause / negative / bid-down under standing approval, idempotent, every action logged to `decisions.md` + `brain/raw/`; the dead-SKU spend bleed is stopped and the own-ASIN denylist enforced
- [ ] **Phase 9: Daily Ranked Queue + Explicit-Approval Spend-Up** - A daily dollar-ranked, dry-run'd queue surfaces moves; gate-passed bid/budget raises fund verified winners under explicit approval, respecting attribution lag and inventory cover
- [ ] **Phase 10: New Coverage-Gap Campaigns + Archive Hygiene** - The lowest-reversibility moves run last: chained new-campaign builds (paced to in-stock inventory, with partial-build rollback), then the graveyard `CAMPAIGNS_REMOVE` archive in its own separately-approved final batch

## Phase Details (M2)

### Phase 6: FIND + Lifecycle Substrate
**Goal**: The async write loop is proven end-to-end on operations that cannot change the account — live entity IDs are pulled and cached, dryRun and `actions_get` responses are classified by hand-written code, and reconciliation discipline (status-not-export) is established — so every later write rides a verified substrate. (Runbook Wave 0.)
**Depends on**: Phase 5 (M1 read primitives + trust spine) complete enough to feed proposals later; no M2 predecessor.
**Requirements**: WRITE-01, WRITE-02, WRITE-05
**Success Criteria** (what must be TRUE):
  1. A PPC write can be validated as a `dryRun` (`actions_start dryRun:true`) and the response is classified by hand-written `lifecycle.py` (VALIDATED / valid / issues[]) into proceed-vs-stop — proving the harness without any real write landing (WRITE-01).
  2. Live `campaignId` / `adGroupId` / `targetId` / `adId` are pulled via `*_FIND` (one ad-product per request) and cached to `data/ads_*_find_*.json`; a write whose IDs are not in cache is refused at build ("stale/missing entity ID") — FIND-before-write is enforced, not assumed (WRITE-02).
  3. An applied action's status is reconciled via `actions_get` polled to a terminal state (COMPLETED / FAILED / CANCELLED, no infinite spin, reusing `datadoe.poll_status` terminal-on-FAILED) plus a `*_FIND` echo — and the code explicitly refuses to treat a next-day DataDoe export (≤24h lag) as confirmation; a FAILED/blocked action surfaces the returned error cleanly (WRITE-05).
  4. The `actions_get` terminal-status enum is confirmed via `actions_details_schema_get` and pinned into the engine's terminal set; `datadoe-query` SKILL gains the write-action reference (the four `actions_*` tools, FIND-before-write, dryRun discipline).
  5. Every `actions_start`/`actions_get` call is wrapped by `logged_call` into `external-calls.jsonl` (never logging the seller UUID).
**Plans**: 4 plans (3 waves)
- [x] 06-01-PLAN.md — Wave 0: pin the verified ACTION_* status enum + add Proceed/PollOutcome; write the RED test_lifecycle/test_find_cache + sanitized fixtures (WRITE-01/02/05)
- [x] 06-02-PLAN.md — lifecycle.py classify_dryrun + classify_poll + the two thin logged_call CLIs (WRITE-01/05)
- [x] 06-03-PLAN.md — find_cache.py write/lookup with missing→refuse, FIND-before-write enforced at build (WRITE-02)
- [ ] 06-04-PLAN.md — datadoe-query SKILL write-action reference + live read-only actions_get/schema confirmation (SC-4)

### Phase 7: Margin-Tiered Safety Gate
**Goal**: The load-bearing safety guardrail exists, is hand-written and pytest-covered, and refuses before Amazon ever sees a spend-increasing write — each SKU's TACOS ceiling derived from its own contribution margin to hold net margin ≥ ~15%, refusing (never defaulting, never silently clamping) when a threshold, ceiling, or SKU margin is missing. This phase must pass the gate on nothing until the operator sets the real floor. (Runbook safety prerequisite; the gap flagged in execution-plan §A.5.)
**Depends on**: Phase 6
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, GATE-05
**Success Criteria** (what must be TRUE):
  1. The engine computes each SKU's contribution margin from DataDoe window-summed components as a typed, tested result — never prose, never auto-generated (`gate.py` + `test_gate.py`, mirroring `tacos.py`) (GATE-01).
  2. From that margin the engine derives a per-SKU TACOS ceiling that protects the configured `min_net_margin_pct`; while that threshold is empty (`""` today) the gate returns a typed refusal ("no threshold set") on every write — never a default 25% (GATE-02).
  3. A spend-increasing write (bid-up / budget-up / placement-up / new-campaign) passes only when its projected TACOS ≤ that SKU's ceiling; a spend-decreasing write (pause / negative / bid-down) always passes the gate (GATE-03).
  4. An over-ceiling bid/budget or sub-floor price is **refused** (a typed `GateRefusal` naming the breached number and its source), never silently clamped to the limit (GATE-04).
  5. The SKU→tier/contribution-margin table is machine-readable (a parseable per-SKU row the gate consumes directly); a SKU absent from the table yields a gate refusal on funding it — correct behavior, surfaced as such (GATE-05).
**Plans**: TBD

### Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed
**Goal**: The first real account writes land — but only reversible ones (pause campaign/keyword/ad, add negative keyword, lower a bid) under standing approval within a magnitude cap — each built, gated (auto-pass as spend-decreasing), dry-run'd, applied, polled to COMPLETED, reconciled, and logged idempotently. Applying this spine to the runbook stops the dead-SKU spend bleed (~$279/mo, ~43% of spend, ~$0 sales loss) and enforces the own-ASIN denylist. (Runbook Wave 1.)
**Depends on**: Phase 7 (gate must exist; reversible writes auto-pass but route through it)
**Requirements**: WRITE-03, WRITE-06, WRITE-07, EXEC-01
**Success Criteria** (what must be TRUE):
  1. A reversible PPC write runs end-to-end — pause campaign/keyword/ad, add negative keyword, lower a bid — via build → dryRun → apply (`dryRun:false` → `actionId`) → poll `actions_get` to COMPLETED → confirm with a `*_FIND` echo (WRITE-03).
  2. Every applied write logs a dated line to `state/decisions.md` and a `brain/raw/` note capturing what changed, why, expected effect, and the `actionId` — standing-approved actions log too (autonomy ≠ silence) (WRITE-06).
  3. Re-running the same approved action does not double-apply: a content-hash idempotency key (persisted in `data/actions_ledger.jsonl`) maps to its COMPLETED `actionId` and re-runs are a no-op; an in-flight `actionId` resumes at poll, never re-fires the start (WRITE-07).
  4. The stop-the-bleed batch is applied: remaining dead/exiting-SKU ad spend and mis-scoped keywords are paused, the negative-keyword harvest is applied per-campaign (exact-by-default, keep-positive allowlist protecting `baklava gift box`, "watch don't negate" terms bid-down not negated), and the EXCLUDE-own-ASIN denylist (B07TV972JT) refuses any payload targeting an owned ASIN before dryRun (EXEC-01).
  5. Standing approval is bounded by a magnitude cap (a bounded % change per action) so a "reversible" bid-down cannot kill a winner; phrase/broad negatives and over-cap cuts route to explicit review.
**Plans**: TBD
**UI hint**: no

### Phase 9: Daily Ranked Queue + Explicit-Approval Spend-Up
**Goal**: A daily, dollar-ranked, dry-run-validated queue of proposed PPC changes becomes the standing operating rhythm — each line showing current → proposed → expected effect with provenance — and gate-passed bid/budget raises fund the engine-verified efficient winners under explicit approval, never scaling onto immature attribution data, internal keyword competition, sub-cover stock, or below-benchmark conversion. (Runbook Waves 2–3.)
**Depends on**: Phase 8 (apply spine) and Phase 7 (gate must *pass*, not just exist, for spend-up)
**Requirements**: WRITE-04, QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-04, EXEC-02, EXEC-05
**Success Criteria** (what must be TRUE):
  1. A daily queue (on-open / on-demand) renders dollar-ranked proposed PPC changes, each dry-run-validated and showing current → proposed → expected effect with provenance (`rank_queue.py` + `queue.py`, reusing the `tacos.classify` sort idiom, no-$-estimate rows last) (QUEUE-01).
  2. The queue applies reversibility-classed autonomy: reversible moves carry standing approval (auto-apply after dryRun, within the magnitude cap from Phase 8); spend-increases and new campaigns are held for explicit approval (QUEUE-02, QUEUE-03).
  3. Efficiency verdicts respect attribution lag via a two-class model — act-now (reversible stop-loss on obviously-dead campaigns: inactive listing / zero lifetime orders / ENABLED on discontinued SKU) vs judge-later (efficiency verdicts that wait for a matured window: ≥7d SP / ≥14d SB/SD); "3 clean days" means 3 days of *matured* data (QUEUE-04).
  4. A spend-increasing write (raise bid/budget; the create-chain in Phase 10) executes only after passing the margin gate AND receiving explicit approval; an over-ceiling raise is refused, not clamped (WRITE-04).
  5. Engine-verified efficient winners are funded up to their gate ceiling and internal keyword competition is consolidated (a term live in >1 ENABLED campaign is flagged and blocked from a bid-up until consolidated to one owning campaign) (EXEC-02); and no budget is scaled onto a SKU below the ≥6-week stock-cover or below-benchmark-conversion threshold — restock-gated SKUs (e.g. GG-0DC1 at 1 FBA unit) are refused until stock is confirmed (EXEC-05).
**Plans**: TBD

### Phase 10: New Coverage-Gap Campaigns + Archive Hygiene
**Goal**: The lowest-reversibility moves run last and separately — chained new-campaign builds (paced to in-stock inventory, with partial-build detection and rollback so no orphan ENABLED empty campaign spends), then the campaign-graveyard archive via `CAMPAIGNS_REMOVE` in its own explicitly-approved final batch with per-ID pre-checks. (Runbook Waves 4–5.)
**Depends on**: Phase 9 (gate-passed spend-up + queue) and the resolved portfolios decision; org-enable of CAMPAIGNS_ADD then CAMPAIGNS_REMOVE
**Requirements**: EXEC-03, EXEC-04
**Success Criteria** (what must be TRUE):
  1. New coverage-gap campaigns are built via the chained `CAMPAIGNS_ADD` → `AD_GROUPS_ADD` → `ADS_ADD` → `TARGETS_ADD` sequence, each step gated on the prior `actions_get` COMPLETED + returned ID, the whole chain dry-run'd first, and any mid-chain failure rolled back (the partial build paused) so no orphan campaign spends (EXEC-03).
  2. New-campaign budgets are paced to in-stock inventory and pass the margin gate on projected spend, and only build once the gate + apply spine are live (EXEC-03); the projected-TACOS seed assumption for a no-history campaign is pinned before any build.
  3. The campaign graveyard is archived via `CAMPAIGNS_REMOVE` in a separate, explicitly-approved, dead-last batch — never bundled with reversible moves — with a per-ID pre-check (PAUSED + zero-spend ≥30d), and any still-ENABLED graveyard candidate goes pause → observe → archive across separate batches, never ENABLED→REMOVE in one step (EXEC-04).
  4. The portfolios decision is honored (tier encoded in campaign name + tags, or `portfolioId` assigned on create if Rami created console portfolios), and shared negatives are re-added to each new campaign at launch (no shared-list object exists).
**Plans**: TBD

## Progress (M2)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. FIND + Lifecycle Substrate | 3/4 | In Progress|  |
| 7. Margin-Tiered Safety Gate | 0/0 | Not started | - |
| 8. Reversible-Write Apply Spine + Stop-the-Bleed | 0/0 | Not started | - |
| 9. Daily Ranked Queue + Explicit-Approval Spend-Up | 0/0 | Not started | - |
| 10. New Coverage-Gap Campaigns + Archive Hygiene | 0/0 | Not started | - |

---
*Milestone v2.0 roadmap created: 2026-06-20*
*All 21 v2.0 requirements mapped to exactly one phase (6–10). Every write is dryRun→approve→apply→reconcile→log; the margin gate is a hard predecessor to any spend increase.*
