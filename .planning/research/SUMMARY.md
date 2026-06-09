# Project Research Summary

**Project:** Habib OS — Milestone 1 (Read-only Amazon FBA PPC & Profit Intelligence)
**Domain:** Single-operator AI analytics workspace on Hermes Mac desktop app (DataDoe read-only sense layer, Supabase numeric truth store)
**Researched:** 2026-06-08
**Confidence:** HIGH overall — stack, features, and architecture grounded in authoritative project docs + verified library versions; Hermes desktop preview (v0.15.2, ~6 days old as of research date) is MEDIUM given fast-moving preview status; DataDoe column-level specifics are MEDIUM and resolve empirically in Phase 0.

---

## Executive Summary

Habib OS Milestone 1 is not a standard web dashboard — it is a **conversational, read-only analytics agent** that answers four concrete acceptance questions ("where am I wasting ad spend", "which search terms to negate", "what's my TACOS by SKU", "which campaigns are budget-capped") against live Amazon data, from the Hermes Mac desktop workspace, with a hard structural guarantee that it cannot change anything on Amazon. The data layer (DataDoe MCP) is physically read-only, which eliminates the autonomous-spend risk that motivated the project. That shifts the entire residual risk onto a single concern: **number correctness and trust**. A metric that is silently wrong is indistinguishable from the fabricated reporting the prior agency produced, and it destroys trust the same way. Every architectural and implementation decision in Milestone 1 flows from this throughline.

The recommended build approach is bottom-up and strictly dependency-ordered. Nothing can compute until there is schema to persist into; nothing can persist reliably until the DataDoe source map is confirmed empirically; nothing can be trusted until every number carries provenance (export id, source label, threshold read from `config`, not invented). The four research streams converge on the same phase ordering: **connections + source map → Supabase schema (parallel with `~/.hermes` context load) → DataDoe read/compute primitives → the four acceptance analyses → FX-reconciled margin**, with provenance logging and config-driven thresholds woven throughout every layer rather than bolted on at the end.

The dominant architecture is a strict three-tier separation: Hermes **skills** (markdown) orchestrate intent and formatting; hand-written **Python primitives** hold all money-touching computation; a **DataDoe wrapper** isolates the read-only MCP call pattern; **Supabase** holds the only numeric truth. The critical anti-pattern is letting the agent freestyle margin math in skill prose — that is the precise failure mode the guardrails exist to prevent. Concrete schema decisions are already resolved by research: `metric_snapshots` at daily × SKU × marketplace grain with `captured_at` + export id for restatement reconciliation; `cogs` as a slowly-changing dimension with FX per cost row. Two items remain open for Phase 0 empirical resolution: exact DataDoe column names + source timezone per program, and confirmation that the premium Profit-by-SKU source is enabled on the current plan.

---

## Key Findings

### Recommended Stack

The stack is largely project-locked. Python 3.12 (within the 3.11+ floor) is the sweet spot for all helpers, reconciliation work, and money logic. The Hermes desktop app (v0.15.2 public preview) is both the runtime and workspace surface — it runs only while the Mac is awake, which means Milestone 1 must be on-demand/conversational, not clock-cron. DataDoe is accessed exclusively as an MCP by the Hermes agent; Python handles only the downloaded export artifact. Supabase serves two distinct clients: SQLAlchemy 2.0 + psycopg3 + Alembic for direct Postgres (migrations, money math, bulk upserts) and supabase-py for ergonomic app-style row writes (ledger entries from skills).

**Core technologies:**
- **Python 3.12:** All helpers, reconciliation, compute primitives — 3.12 is the compatibility sweet spot for psycopg3/tenacity/structlog.
- **Hermes Desktop v0.15.2:** Runtime workspace; skills in `~/.hermes/skills/`, MCP in `~/.hermes/config.yaml`; cron deferred (Mac-awake constraint means on-demand only for M1).
- **agentskills.io SKILL.md format:** YAML frontmatter + Markdown body; thin `SKILL.md`, rich `references/` subdirectory; orchestration only, no math.
- **DataDoe MCP (live, authenticated):** Single read-only Amazon source; agent calls `sellers_and_vendors_list → exports_sources_get → exports_create → poll exports_get → exports_raw_download`; Python handles the downloaded artifact only. Hard 2500-row cap; must paginate via `skip` or pre-aggregate via `groupBy`.
- **Supabase (Postgres 15+ + pgvector):** Numeric truth store; schema + migrations via Alembic (never dashboard click-ops).
- **SQLAlchemy 2.0 + Alembic 1.18.4 + psycopg 3.3.4 [binary]:** Direct Postgres path for money math, migrations, bulk upserts.
- **pydantic 2.13.4:** Validate DataDoe export columns and config thresholds before they touch money math.
- **tenacity 9.1.4 + structlog 26.1.0:** Retry/backoff on the export poll loop; structured JSON logging on every external call.
- **polars 1.41.2:** Fast export transforms on the downloaded CSV/JSON.
- **uv:** Reproducible env + dependency management.

### Expected Features

All features are questions the agent answers — none writes to Amazon.

**Must have (table stakes — Milestone 1 launch):**
- Supabase truth store + business context in `~/.hermes` — every analysis depends on this; thresholds/FX/SKU map live here; must exist before any analysis is trustworthy.
- DataDoe read/compute primitives (STP, KWT, PERF-CAMP, PERF-ASIN, PLACE, CAMP-RAW) — substrate for all PPC answers.
- Wasted-spend detection — STP-led, zero-conversion and high-ACOS spend ranked by spend desc.
- Search-term harvesting + negative-keyword identification — STP, config-driven spend threshold; output is a proposal list, never auto-applied.
- ACOS / TACOS / ROI by SKU — prefer DataDoe premium Profit-by-SKU precomputed values; reconstruct from PERF-ASIN + ORDERS only if premium unavailable.
- Campaign budget-cap detection — CAMP-RAW budget + PERF-CAMP daily spend pattern; approximate (no native Lost-IS column in DataDoe).
- FX-reconciled margin / profit-by-SKU — PROFIT is authority, `cogs` with per-row FX fills gaps and validates.
- Provenance + run-logging — every numeric claim traceable to a DataDoe export id + config row; persisted to `metric_snapshots`.

**Should have (v1.x after core Q&A validated):**
- Keyword/target bid context surfacing (KWT).
- Placement analysis: TOS vs rest-of-search vs product-page (PLACE + CAMP-RAW).
- Margin-aware PPC reasoning (explicit PROFIT × PPC join).
- Budget-cap impact quantification.

**Defer (v2+ / later milestones):**
- Repeat-purchase / CLV reconstruction, US-specific logic, scheduled review, PPC change proposals, gated write-MCP.

**Anti-features (structurally forbidden):**
- Any autonomous Amazon write; invented thresholds; hand-rolled ACOS/TACOS when a premium column exists.

### Architecture Approach

The system is a read-only analytics pipeline in a strict four-layer model: SURFACE (conversation) → THINK (one agent: SOUL.md + skills + Python primitives) → STATE (Supabase) → SENSE (DataDoe read MCP). No ACT layer in M1. The single most important boundary: **all money-touching computation in hand-written Python primitives, never in skill prose**.

**Major components:**
1. **`datadoe.py` wrapper** — sources → create → poll → download; tenacity retry; structlog on every call; 2500-row cap handled; read-only contract isolated here.
2. **Python compute primitives** (`margin.py`, `ppc.py`, `reconcile.py`) — all money-touching math; hand-written, version-controlled, pytest-tested against real export fixtures.
3. **`store.py` / Supabase persistence layer** — idempotent upserts to `metric_snapshots` on `(marketplace, seller_sku, snapshot_date)`; the only Postgres writer; enforces marketplace dimension and provenance.
4. **Hermes skills (markdown)** — orchestration only; zero math; deployed to `~/.hermes/skills/`.
5. **`~/.hermes/` memory + SOUL.md** — business context, persona; version-controlled in `.hermes-context/` in git; deployed locally; never holds numeric truth.

**Concrete schema decisions (locked):**
- `metric_snapshots` grain = daily per SKU per marketplace; unique on `(marketplace, seller_sku, snapshot_date)`; carries `captured_at` + `datadoe_export_id` for restatement reconciliation.
- `cogs` = slowly-changing dimension (SCD) with `effective_from`/`effective_to` and per-row `unit_cost`, `cost_currency`, `fx_rate`, `fx_as_of`, `marketplace_currency`.
- `config` keyed `(key, marketplace)` so CA and US thresholds can differ without schema change.
- `decision_ledger` ships in M1 with approval/write columns present but NULL — audit spine for M2/M3 without a migration.

### Critical Pitfalls

All top pitfalls feed the same failure mode: a silently wrong number is operationally identical to a fabricated one.

1. **ACOS/TACOS computed or labeled wrong** — Read the premium column as single authority; never recompute in a prompt. Every ratio carries definition + source inline. Verify: TACOS must be ≤ ACOS for the same SKU.
2. **The agent invents numbers or thresholds** — All thresholds from Supabase `config`; on failed/empty export return "no data," never a substitute. Seed `config` with real values before any primitive is tested.
3. **SP/SB/SD double-counting + attribution-window overlap** — Document per-source program scope and attribution window in Phase 0. Never sum attributed sales across programs; use premium TACOS instead. (SD's 14-day brand-halo attribution is the worst offender; the Ad-Performance-by-ASIN source mixes SP+SD.)
4. **DataDoe 2500-row cap silently truncates results** — Server-side `groupBy + aggregations` preferred; paginate with `skip` when exactly 2500 rows returned; built into `datadoe.py` by design.
5. **Date/timezone misalignment** — Pin one canonical timezone (Amazon PST) system-wide; record each source's timezone basis in Phase 0; stamp every snapshot with the basis used.
6. **Amazon restatement** — Point-in-time exports are provisional (attribution updates over ~60 days); snapshots must be versioned with `captured_at` + export id, not stored as final truth.

---

## Implications for Roadmap

Build order is **dependency-forced**. All four research files independently arrived at the same sequence. Suggested phases: **4**.

### Phase 0: Connections + DataDoe Source Map
**Rationale:** Everything downstream is blocked until (a) MCP connections are verified read-only and responding, (b) amazon.ca seller UUID is resolved and cached, and (c) `exports_sources_get` empirically confirms which DataDoe sources are available, their columns, program scope, and timezone basis. Resolves the two main LOW-confidence gaps.
**Delivers:** Verified MCP connections; `.env` with `AMAZON_CA_SELLER_ID`; source-map document recording confirmed DataDoe sources, columns, program scope, timezone, and premium Profit-by-SKU enablement status.
**Avoids:** wrong seller scope, timezone misalignment, premium-source surprises, credential scoping.
**Research flag:** Empirical hands-on task. No research phase needed.

### Phase 1: Supabase Truth Schema + `~/.hermes` Context
**Rationale:** Schema must exist before any data can be persisted; `~/.hermes` context must be loaded before skills have a persona and thresholds. **These two tracks are parallelizable.** Both complete before any compute primitive is written.
**Delivers:** All five Supabase tables via Alembic migrations; marketplace as first-class dimension; `cogs` as SCD with FX per cost row; `metric_snapshots` with `captured_at` + `datadoe_export_id`; `config` seeded with real operator thresholds; SOUL.md + business context deployed to `~/.hermes/`; `.hermes-context/` version-controlled; `~/.hermes` backup target/schedule decided.
**Open item:** Config seed values — operator supplies real min-margin %, ACOS ceiling, days-of-cover trigger before Phase 1 is done.
**Avoids:** invented thresholds, snapshot timezone basis, captured_at for restatement.
**Research flag:** Standard SQLAlchemy/Alembic/psycopg3 patterns. No research phase needed.

### Phase 2: DataDoe Read/Compute Primitives
**Rationale:** `datadoe.py` and `store.py` must exist before analysis primitives. Once done, `margin.py` and `ppc.py` proceed in parallel (margin also needs `reconcile.py`; PPC does not). Every external call wrapped and logged; 2500-row cap handled by design.
**Delivers:** `datadoe.py` (full MCP call pattern, tenacity retry, structlog, skip-based pagination, 2500-row detection); `store.py` (idempotent upserts, cogs/config reads, marketplace enforcement); `reconcile.py` (DataDoe-authoritative margin, cogs FX fallback, stamps `margin_source`); `margin.py` (net profit, ACOS/TACOS/ROI reading premium column, labeled fallback); `ppc.py` (search-term waste with config thresholds, negative candidates, budget-cap detection). pytest coverage against real export fixtures before Phase 3.
**Avoids:** ACOS authority, double-counting, 2500-row cap, search-term vs targeting confusion, premium fallback logic.
**Research flag:** DataDoe column names require Phase 0 source-map output. Standard Python patterns otherwise.

### Phase 3: The Four Acceptance Analyses + Skills
**Rationale:** Skills (markdown orchestration) are last because they are thin wrappers over finished primitives. Building skills before primitives forces math into prose — the critical anti-pattern.
**Delivers:** Hermes skills (e.g. `ask-margin.md`, `ask-ppc.md`, `ingest-snapshot.md`, `daily-briefing.md`); on-demand answers to the four M1 acceptance questions; every answer citing export id and config source; briefings stamped with date window covered; `decision_ledger` populated with read-only recommendation records; manual spot-check against Seller Central signed off.
**Avoids:** clock-cron assumption (use on-demand/on-open), action-voice (use recommendation voice + ledger), missing provenance.
**Research flag:** Standard Hermes skill authoring. No research phase needed.

### Research Flags
Phases needing `/gsd:plan-phase --research-phase`: **None.** Coverage is comprehensive for M1. The two open empirical items (DataDoe columns, premium source enablement) are Phase 0 hands-on tasks; config seed values are operator input in Phase 1.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyPI versions verified 2026-06-08; SQLAlchemy/psycopg3/Alembic confirmed via docs. Hermes desktop specifics MEDIUM — v0.15.2 is ~6 days old; verify `hermes mcp list` + cron pane empirically on first run. |
| Features | HIGH | All eight table-stakes features map cleanly to confirmed DataDoe sources (docs/04). Anti-features are project-locked. |
| Architecture | HIGH | Component model and read-only contract grounded in project docs. Schema recommendations resolve all five docs/05 open items. Exact DataDoe column names MEDIUM — resolve in Phase 0. |
| Pitfalls | HIGH | Amazon Ads attribution/timezone pitfalls verified against Amazon Ads docs + multiple sources; LLM hallucination pitfalls grounded in research; DataDoe-specifics authoritative from internal docs. |

**Overall confidence:** HIGH

### Gaps to Address
- **DataDoe column names and source timezone (Phase 0 — empirical):** Run `exports_sources_get` + a by-hand test export; record in the source-map doc. Keep `metric_snapshots` columns close to the Profit-by-SKU output to minimize transformation.
- **Premium Profit-by-SKU enablement (Phase 0 — empirical):** Confirm via `exports_sources_get`. If not enabled/incomplete, test the `reconcile.py` fallback path before Phase 2 is done.
- **Config seed values (Phase 1 — operator input):** Real min-margin %, ACOS ceiling, days-of-cover trigger. An empty config is a fabrication invitation.
- **Hermes desktop cron pane availability (post-M1):** MEDIUM confidence on the cron pane / `hermes gateway install`. Does not block M1 (on-demand only). Verify before designing M3 scheduling.
- **`~/.hermes` backup target and schedule (Phase 1):** Resolve before Phase 1 is done — disk loss before backup setup wipes procedural memory + decision ledger.

---

## Sources

### Primary (HIGH confidence)
- Internal project docs: `docs/01-architecture.md`, `docs/02-context-and-constraints.md`, `docs/04-data-tools-reference.md`, `docs/05-open-decisions.md`, `CLAUDE.md`, `.planning/PROJECT.md`
- agentskills.io specification (https://agentskills.io/specification)
- PyPI verified 2026-06-08: supabase 2.31.0, sqlalchemy 2.0.50, alembic 1.18.4, psycopg 3.3.4, pgvector 0.4.2, httpx 0.28.1, tenacity 9.1.4, structlog 26.1.0, pydantic 2.13.4, polars 1.41.2, python-dotenv 1.2.2
- Amazon Ads attribution basics (https://advertising.amazon.com/library/guides/basics-of-amazon-attribution)
- ACOS vs TACOS definitions (https://www.datadoe.com/blog-posts/amazon-acos-vs-tacos)
- Amazon reporting timezone/PST/UTC (https://docs.openbridge.com/en/articles/5053618-understanding-timezones-within-amazon-seller-central-and-amazon-advertising)
- LLM text-to-SQL hallucination research (https://arxiv.org/html/2512.22250v1)

### Secondary (MEDIUM confidence)
- Hermes desktop app docs (https://hermes-agent.nousresearch.com/docs/user-guide/desktop) — MEDIUM: v0.15.2 is ~6 days into public preview
- PPC negative-keyword research (AdBadger, SellerMetrics) — 10–20 click zero-conversion threshold

### Tertiary (LOW-MEDIUM confidence)
- DataDoe MCP tool names and call order — from project's own `docs/04` and live connection; exact column names require empirical Phase 0 resolution.

---
*Research completed: 2026-06-08*
*Ready for roadmap: yes*
