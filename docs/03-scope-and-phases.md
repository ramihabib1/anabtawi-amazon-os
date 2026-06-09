# Scope & Phases (→ GSD milestones)

Map each phase to a GSD milestone. Don't start a later phase before the earlier one is verified. The vision is an AI-first workspace that does **both**: a command center I work in (conversational) and, later, scheduled reviews — both on one foundation.

## Deployment note (Mac desktop app)
The runtime is the Hermes Mac desktop app, which runs only while the Mac is awake/open. Milestones 1–2 are conversational/on-demand and need nothing always-on. Milestone 3's "scheduled" review must therefore either run on an always-on Mac or be triggered on-open / on-demand rather than by clock cron.

## Milestone 1 — Foundation + PPC/profit intelligence
**Goal:** the workspace foundation, proven conversationally on the top priority.
- Connect the desktop app to DataDoe + Supabase + Gmail/Drive.
- Build the Supabase truth store: `sku_master`, `cogs` (or rely on DataDoe profit), `metric_snapshots`, `decision_ledger`, `config`.
- Load business context into `~/.hermes` (+ SOUL.md): the business, SKUs, guardrails, tone.
- Hand-write read/compute primitives over DataDoe PPC + profit sources: Search Term Performance, Keyword Targeting, Ad Performance by Campaign & ASIN, Ad Campaigns (raw), and premium Profit by SKU & Date (profit / ACOS / TACOS / ROI).
- **Done when:** from the desktop workspace I can ask "where am I wasting ad spend", "which search terms to negate", "what's my TACOS by SKU", "which campaigns are budget-capped" — and get correct answers against live data, spot-checked manually. No writes.

## Milestone 2 — Listing optimization intelligence
**Goal:** find listing weaknesses and draft fixes; read + draft only.
- Use Organic Search Ranks by ASIN + Search Engagement by ASIN + ad search-terms to surface keyword gaps, low-CTR/low-CVR listings, and ranking opportunities.
- Draft improved titles/bullets/backend keywords with the data justifying each, for my review. I paste edits into Seller Central manually.
- **Done when:** for a given ASIN it produces a justified optimization brief + draft copy I'd actually use.

## Milestone 3 — Scheduled PPC review (gated, on-open or always-on)
**Goal:** recurring PPC review that produces approve-ready recommendations.
- Negative-keyword candidates, bid/budget moves, budget-capped winners — each with the spend/return data behind it.
- Delivered to Telegram and/or the workspace. **No autonomous writes** — I approve every change; all logged to `decision_ledger`.
- Trigger respects the desktop-app constraint (on-open/on-demand, or an always-on Mac).

## Later (deferred, gated)
A custom Amazon Ads / SP-API write-MCP so approved changes execute directly. Only after the recommendations have earned trust. Until then, execution is manual.
