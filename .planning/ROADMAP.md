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
