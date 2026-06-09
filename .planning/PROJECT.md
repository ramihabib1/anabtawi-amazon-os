# Habib OS

## What This Is

An AI-first operations workspace for Habib Distribution (Anabtawi Sweets — ~30 SKUs on Amazon.ca FBA, with a US FBA expansion underway), built **around the Hermes Mac desktop app**. One resident agent runs hand-written skills over a read-only Amazon data source (DataDoe) and a Supabase numeric-truth store, surfacing PPC, profit, and inventory intelligence in the workspace I actually work in. It senses and recommends autonomously; anything that could move money on Amazon is a human-approved, logged proposal — never an autonomous write.

## Core Value

From the desktop workspace I can ask real PPC/profit questions ("where am I wasting ad spend", "which search terms to negate", "what's my TACOS by SKU", "which campaigns are budget-capped") and get correct answers against live DataDoe data — with zero risk of the system changing anything on Amazon.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Milestone 1: Foundation + PPC/profit intelligence. Building toward these. -->

- [ ] Connect the Hermes desktop app to DataDoe (read-only), Supabase, and Gmail/Drive
- [ ] Resolve and cache the amazon.ca seller UUID; confirm DataDoe Ads + premium Profit-by-SKU sources are available
- [ ] Stand up the Supabase truth store: `sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config` — marketplace as a first-class dimension (CA-first, US-ready)
- [ ] Load business context into `~/.hermes` (+ SOUL.md persona): business, SKUs, guardrails, numbers-first tone
- [ ] Hand-write read/compute primitives over DataDoe PPC sources (Search Term Performance, Keyword Targeting, Ad Performance by Campaign & ASIN, Ad Placement, Ad Campaigns raw)
- [ ] Hand-write the profit/margin primitive preferring DataDoe premium "Profit by SKU & Date" (net profit, ACOS, TACOS, ROI), with `cogs` as reconciliation/FX fallback
- [ ] Answer the four Milestone-1 acceptance questions conversationally against live data, spot-checked manually — no writes

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Any autonomous write to Amazon (bids, budgets, negatives, pricing, inventory, listings) — structural guardrail; a prior third party abused PPC/listing writes. Writes are always human-approved, logged proposals.
- A custom Amazon Ads / SP-API write-MCP — deferred, gated milestone; manual execution until recommendations earn trust.
- Listing optimization intelligence — Milestone 2, not this cycle.
- Scheduled/recurring PPC review — Milestone 3, not this cycle.
- Agent Central as a data source — removed; DataDoe is the single Amazon source (its org has the Ads connection attached).
- Marketplaces beyond amazon.ca for *logic* — US data is schema-ready but US-specific logic is deferred until CA is solid.
- Unattended clock-cron scheduling — desktop app runs only while the Mac is awake/open; Milestone 1 is conversational/on-demand.

## Context

- **Business:** Habib Distribution imports/distributes Anabtawi Sweets into Canada — ~30 SKUs on Amazon.ca FBA; US FBA expansion underway. Operated solo on the technical/analytical side; finance and sales/marketing handled by family.
- **Runtime:** Hermes Mac desktop app (public preview) — the day-to-day workspace surface, NOT a server/Hetzner deployment. Memory and skills live locally in `~/.hermes`; back it up (Time Machine + explicit copy).
- **Connected systems (all already authenticated):** DataDoe MCP (single Amazon data source, SQL-style read-only exports over Seller Central + the attached Amazon Ads connection), Supabase (Postgres + pgvector), Gmail/Drive/Calendar, Tavily (web research).
- **Why guardrails are strict:** a prior third party took unauthorized PPC actions and produced fabricated reporting. The architecture makes oversight *structural* — the data tools physically cannot write, and any money-moving action is a logged, approved proposal.
- **Prior build note:** an earlier server-based design (Hetzner, direct SP-API, 3-agent fleet, Next.js dashboard, PM2/VPS) was explored and then superseded by this Hermes-desktop / DataDoe / single-agent design (docs revised 2026-06-08). This directory is greenfield (docs, no code).

## Constraints

- **Runtime:** Hermes Mac desktop app — runs only while the Mac is awake/open. No assumed unattended cron; scheduled work (later milestones) is on-open/on-demand or needs an always-on Mac.
- **Data layer:** READ-ONLY. DataDoe only reads Amazon. No code may assume a write capability it does not have.
- **Writes:** No autonomous writes to Amazon. Every write is a proposal a human approves and executes (manually first; gated write-MCP only once trusted). Every approval and outcome logged to `decision_ledger`.
- **Money-touching logic:** hand-written and reviewed (margin, ACOS/TACOS thresholds, anything feeding a spend decision). Not auto-generated.
- **Tech stack:** Python 3.11+ unless the deliverable requires otherwise; deliverables are Hermes skills (markdown, agentskills.io format), Python helpers, SQL. State in Supabase.
- **Secrets:** in environment variables (`.env`); never in code or committed files.
- **Observability:** every external call (DataDoe export, Supabase) is wrapped and logged.
- **Model provider:** Anthropic API on metered credit — Sonnet for routine work, Opus for planning/review.

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Roadmap this cycle = Milestone 1 only | Learn-before-build; highest value-to-risk is foundation + PPC. M2/M3 via `/gsd:new-milestone` later. | — Pending |
| Schema is CA-first but US-ready (marketplace a first-class column) | US expansion underway; carrying the dimension avoids a later migration without adding US logic now. | — Pending |
| Margin authority = DataDoe premium "Profit by SKU & Date", `cogs` as fallback | Premium source already computes net profit/ACOS/TACOS/ROI; `cogs` reconciles FX and covers SKUs the premium source misses. | — Pending |
| DataDoe is the single Amazon source (Agent Central removed) | DataDoe org has the Ads connection attached; one source is simpler and sufficient. | — Pending |
| One resident agent with skills, not a fleet | Simpler memory/persona model; capabilities are skills on one agent. | — Pending |

### Open (resolve in discuss-phase)

These are flagged in [docs/05-open-decisions.md](../docs/05-open-decisions.md) and intentionally deferred to phase discussion:
- `metric_snapshots` grain (daily per SKU per marketplace) and whether `cogs` captures FX per cost row
- Daily briefing content/order/local-time and what counts as an "anomaly" worth flagging
- Real seed numbers for `config` (min margin %, days-of-cover trigger, ACOS ceiling)
- Authoritative DataDoe source(s)/columns for sales & margin (resolve empirically via `exports_sources_get` in Phase 1)
- Telegram approval UX (inline buttons vs reply-keyword) and how the approval token records in `decision_ledger`
- Backup target/schedule for `~/.hermes/` and the Supabase dump

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-08 after initialization*
