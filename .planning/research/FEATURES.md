# Feature Research

**Domain:** Amazon FBA PPC & profit intelligence — conversational, read-only Q&A (Milestone 1)
**Researched:** 2026-06-08
**Confidence:** HIGH

This research maps the standard analyses an Amazon-seller PPC/profit tool is expected to do, scoped strictly to what is **answerable read-only from the DataDoe sources confirmed in docs/04**. Every feature below is a *question the agent answers* — none writes to Amazon. All Amazon-write/automation actions are in Anti-Features (the prior-agency abuse vector).

DataDoe source shorthand used throughout:
- **STP** = Search Term Performance (`amazon_ads_search_terms_by_campaign_by_date`)
- **KWT** = Keyword Targeting Performance (`amazon_ads_targeting_by_campaign_by_date`)
- **PERF-CAMP** = Ad Performance by Campaign & Date (`amazon_ads_performance_by_campaign_by_date`)
- **PERF-ASIN** = Ad Performance by ASIN & Date (`amazon_ads_performance_by_child_asin_and_date`)
- **PLACE** = Ad Placement Performance (`amazon_ads_placement_by_campaign_by_date`)
- **CAMP-RAW** = Ad Campaigns raw config (`amazon_ads_campaigns_raw`)
- **PROFIT** = Profit by SKU & Date (`amazon_profit_by_sku_and_date`, PREMIUM)
- **ORDERS** = Order Line Items (`amazon_order_items_with_cogs`)
- **COGS-TBL** = Supabase `cogs` / `sku_master` (operator's landed cost + FX truth)

## Feature Landscape

### Table Stakes (Sellers Expect These)

The eight analyses named in the milestone brief. Any Amazon PPC/profit tool that can't answer these feels broken. All are read-only against DataDoe.

| Feature | Why Expected | Complexity | DataDoe Source | Notes |
|---------|--------------|------------|----------------|-------|
| **Search-term harvesting + negative-keyword identification** | The single highest-ROI PPC optimization; industry audits show 25–40% of spend goes to terms that never converted. Sellers expect "which search terms should I negate." | MEDIUM | **STP** (search term → matched keyword, spend, sales, orders, clicks, CTR, match type) | Rule of thumb: terms with ≥10–20 clicks (or > a spend threshold like ~1× target CPA) and **zero orders** are negation candidates; converting search terms not yet a keyword are *harvest* candidates. **Thresholds must come from Supabase `config`, never invented** (per docs/02). Output is a ranked candidate list — operator approves & adds the negative in Seller Central. |
| **Wasted-spend detection** | "Where am I wasting ad spend" is a literal Milestone-1 acceptance question. | MEDIUM | **STP** (primary), **PERF-CAMP**, **KWT** | Aggregate spend with no/low return across search terms, keywords, and campaigns. Sort by spend desc, flag zero-conversion and high-ACOS spend. Overlaps heavily with negative-keyword harvesting but also covers high-spend low-return *keywords/campaigns*, not just raw search terms. |
| **Keyword/target bid context** | Sellers expect to see current bid vs. performance vs. top-of-search impression share before reasoning about a bid. | MEDIUM | **KWT** (keyword/target, bid, top-of-search impression share), **STP** (keyword bid, match type) | Read-only *context for a bid decision*, NOT a bid recommendation engine (that's Milestone 3). Surface: current bid, TOS impression share, spend/ACOS per keyword so the operator can reason. |
| **Campaign budget-cap detection** | "Which campaigns are budget-capped" is a literal Milestone-1 acceptance question. | MEDIUM | **CAMP-RAW** (budget amount, budget type, bid strategy, state) + **PERF-CAMP** (daily spend vs. budget) | Flag campaigns whose daily spend ≈ daily budget (capped) AND are performing well (low ACOS / high conversion) — those are the costly caps. DataDoe does not expose Amazon's native "Lost IS (budget)" column, so detect via **spend-hitting-budget pattern** over the date range, not impression-share-lost. Note this approximation as a known limitation. |
| **Placement analysis (TOS vs rest-of-search vs product-page)** | Standard lever; top-of-search CTR runs materially higher than other placements, and placement bid adjustments are a core PPC dial. | MEDIUM | **PLACE** (TOS / rest-of-search / product-page spend, sales, orders) + **CAMP-RAW** (current placement bid adjustments) | Compare per-placement ACOS/CVR to show where each campaign converts. Read-only: surfaces "your product-page placement converts at X, TOS at Y, current TOS adjustment is Z%" — operator decides. |
| **ACOS / TACOS / ROI by SKU** | "What's my TACOS by SKU" is a literal Milestone-1 acceptance question. TACOS-by-SKU requires ad spend joined to *total* revenue at SKU grain — the metric sellers most want and most tools get wrong. | LOW–MEDIUM | **PROFIT** (premium — already computes ACOS, TACOS, ROI, net profit per SKU/date) | **Prefer PROFIT's precomputed values** (docs/02 operating principle: don't hand-roll the math). Complexity is LOW *if* the premium source is enabled; MEDIUM if it must be reconstructed by joining PERF-ASIN ad spend to ORDERS revenue. Confirm premium availability in Phase 1. |
| **True margin / profit-by-SKU** | A 25% ACOS is profitable or ruinous depending on the SKU's real margin; sellers expect net-profit-after-everything, not just ad metrics. | MEDIUM | **PROFIT** (net profit, total cost = fees + COGS + ad spend, FBA/AWD fees, referral) — authority; **COGS-TBL** as reconciliation/fallback | PROFIT is the margin authority. `cogs`/`sku_master` reconcile FX and cover SKUs the premium source misses. Flag when PROFIT's COGS disagrees with the operator's landed cost. |
| **FX-aware margin for a CA seller importing in USD** | Anabtawi stock is imported (landed cost likely in USD/foreign currency) while amazon.ca revenue is CAD. Margin computed without FX is wrong; small CAD/USD swings move the bottom line. | MEDIUM–HIGH | **COGS-TBL** (landed cost + the FX rate/currency per cost row) reconciled against **PROFIT** (CAD-denominated net profit) | DataDoe data is amazon.ca CAD; the FX truth lives in Supabase `cogs`. Open question (docs/05): whether `cogs` captures FX per cost row. Feature = reconcile PROFIT's COGS against operator's landed cost converted at a known rate, and surface the FX assumption explicitly. Highest-complexity table-stakes item because the source of truth is operator-supplied, not DataDoe. |

### Differentiators (Competitive Advantage)

Not expected of a basic tool, but align with Habib OS's Core Value: a *conversational, trustworthy, numbers-first* agent with structural anti-write guardrails. All still strictly read-only.

| Feature | Value Proposition | Complexity | DataDoe Source | Notes |
|---------|-------------------|------------|----------------|-------|
| **Conversational natural-language Q&A over live data** | The entire premise — ask in plain English, get correct numbers spot-checkable to source. Most seller PPC tools are dashboards, not askable. | MEDIUM | All | This is the Milestone-1 product itself, not an add-on. Differentiator vs. Helium10/AdBadger-style dashboards. |
| **"Show the data behind every claim" provenance** | Directly answers the prior-agency abuse (fabricated reporting). Every number traceable to a DataDoe export + filters. Builds the trust required before any future write-MCP. | MEDIUM | All + run logging | Per docs/02: every external call wrapped/logged. Persist run + result to Supabase (`metric_snapshots`) so answers are auditable, not vibes. |
| **Margin-aware PPC reasoning (ACOS read against per-SKU margin)** | The pros' insight: "a 25% ACOS means nothing without margin per SKU." Joining PROFIT margin to PPC spend lets the agent say "this spend is unprofitable *for this SKU*," not just "ACOS is high." | MEDIUM | **PROFIT** + **STP/PERF-CAMP** | Cross-source join is the differentiator. Many tools silo ad metrics from true profit. |
| **Budget-cap impact quantification** | Beyond detecting a cap: estimate forgone profitable sales (capped campaign with low ACOS = leaving money on the table). | MEDIUM–HIGH | **CAMP-RAW** + **PERF-CAMP** + **PROFIT** | Estimate only (no native Lost-IS data). Frame as "this profitable campaign is hitting budget ~daily" rather than a hard $ forgone figure. |
| **Repeat-purchase / CLV context for PPC payback** | Sweets are consumable/repeat-buy; a high first-order ACOS can be fine if customers repurchase. Reconstructable from ORDERS' hashed `buyer_email`. | HIGH | **ORDERS** (hashed buyer_email) | Native repeat-purchase metrics are NOT available (Agent Central removed); this is a reconstruction. Defer past Milestone 1 unless trivially cheap — flag as v1.x. |
| **Multi-marketplace-ready answers (CA now, US later)** | Schema carries marketplace as a first-class dimension; answers stay correct when US data lands without a migration. | LOW (schema), deferred (US logic) | All, partitioned by marketplace | docs/03: US schema-ready, US-specific *logic* deferred until CA is solid. Differentiator is the clean dimension, not US analysis now. |

### Anti-Features (Deliberately NOT Built — Forbidden)

**WARNING — prior-abuse vector.** docs/02: a prior third party took **unauthorized PPC actions and produced fabricated reporting**. The guardrails are *structural*: the DataDoe data layer physically cannot write. Every item below is a hard out-of-scope for Milestone 1; several are forbidden autonomously *forever* (only ever human-approved, logged proposals — and only through a future gated write-MCP). Do not propose patterns that bypass this.

| Anti-Feature | Why It Gets Requested | Why Forbidden Here | What To Do Instead |
|--------------|----------------------|--------------------|--------------------|
| **Autonomous negative-keyword application** | "Just auto-add the negatives you find." | This is exactly the abuse vector — silent PPC changes. No DataDoe write capability exists; would require the deferred write-MCP. | Emit a ranked negative-keyword **proposal** with spend/return data; human approves and adds it in Seller Central. Log to `decision_ledger`. |
| **Autonomous bid changes** | "Lower bids on losers, raise on winners." | Money-moving; the single most-abused PPC action. Money-touching logic must be hand-written/reviewed (docs/02), never auto-executed. | Surface bid *context* (current bid, TOS share, ACOS vs margin). Bid *recommendations* are a Milestone-3 proposal, still human-executed. |
| **Autonomous budget changes** | "Raise budgets on capped winners automatically." | Direct spend control; autonomous = unbounded spend risk. | Detect & quantify the cap; emit a proposal. Human raises the budget. |
| **Autonomous campaign / placement-bid-adjustment edits** | "Tune placement bids for me." | Write to the ad account; forbidden. | Placement analysis is read-only context. Adjustments are Milestone-3 proposals. |
| **Autonomous listing / pricing / inventory writes** | "Fix the listing / reprice / restock." | Out of scope for Milestone 1 entirely; listing is M2 (draft-only), pricing/inventory writes forbidden. Listing edits were part of the prior abuse. | M2 drafts copy for human paste. Pricing/inventory never autonomous. |
| **Direct SP-API / Amazon Ads API integration in M1** | "Skip DataDoe, go straight to the API for writes." | Reintroduces write capability and the superseded server design; DataDoe is the single read-only source by decision. | Stay on DataDoe (read-only). A gated write-MCP is a separate, later, trust-gated decision. |
| **Invented thresholds / benchmarks** | "Just flag anything over 30% ACOS." | Fabricated-reporting risk; generic benchmarks lie per-SKU. Never invent thresholds (docs/02). | Read every threshold (min margin %, ACOS ceiling) from Supabase `config`. |
| **Hand-rolled margin math when PROFIT exists** | "Compute net profit yourself from fees." | Error-prone, duplicates a vetted premium source, risks subtly-wrong money numbers. | Prefer PROFIT premium; use `cogs` only to reconcile FX / fill gaps, and flag disagreements. |
| **Unattended/scheduled PPC review in M1** | "Run this every morning automatically." | Desktop app runs only while the Mac is awake; no assumed cron. Scheduled review is M3. | M1 is conversational/on-demand. Scheduling is M3 (on-open or always-on Mac). |

## Feature Dependencies

```
Supabase truth store (sku_master, cogs, config, metric_snapshots, decision_ledger)
    └──required by──> ALL features (thresholds, FX, SKU mapping, run logging)

DataDoe read/compute primitives (STP, KWT, PERF-CAMP, PERF-ASIN, PLACE, CAMP-RAW)
    └──required by──> every PPC analysis

PROFIT (premium) primitive
    └──required by──> ACOS/TACOS/ROI-by-SKU
    └──required by──> True-margin-by-SKU
                          └──requires──> COGS-TBL + FX  (reconciliation/fallback)

Search-term harvesting / negative-ID ──shares source(STP)──> Wasted-spend detection
Budget-cap detection ──requires──> CAMP-RAW (config) + PERF-CAMP (actual spend)
Margin-aware PPC reasoning ──requires──> PROFIT  +  (STP | PERF-CAMP)   [cross-source join]
Provenance/run-logging ──enhances──> ALL  (every answer auditable)
Repeat-purchase/CLV ──requires──> ORDERS (hashed buyer_email)  [reconstruction, defer]
```

### Dependency Notes

- **Everything requires the Supabase truth store first.** Thresholds (`config`), FX/landed cost (`cogs`), SKU↔ASIN mapping (`sku_master`), and audit logging (`metric_snapshots`, `decision_ledger`) underpin every analysis. Phase ordering must stand this up before any analysis is trustworthy.
- **DataDoe primitives gate all PPC analysis.** The read/compute primitives over STP/KWT/PERF-*/PLACE/CAMP-RAW are the substrate; build them before the analyses that consume them.
- **Margin-by-SKU requires PROFIT, with COGS-TBL+FX as reconciliation.** PROFIT is the authority; `cogs`/FX fill gaps and validate. The FX feature *requires* the margin feature and adds the currency layer on top.
- **Budget-cap detection needs both config and actuals.** CAMP-RAW gives the budget setting; PERF-CAMP gives daily spend. Neither alone detects a cap — must join. (No native Lost-IS column; detection is approximate.)
- **Margin-aware PPC reasoning is the cross-source join** (PROFIT × PPC) that turns "high ACOS" into "unprofitable for this SKU" — the main differentiator, and it depends on both pillars being built first.
- **Conflict: any write/automation feature conflicts with the read-only data layer.** They cannot coexist with the structural guardrail and are deferred to a gated write-MCP.

## MVP Definition

### Launch With (v1 — Milestone 1)

The four acceptance questions, answered correctly read-only, plus the foundation they stand on.

- [ ] **Supabase truth store + business context in `~/.hermes`** — every analysis depends on it; thresholds/FX/SKU map live here.
- [ ] **DataDoe read/compute primitives** (STP, KWT, PERF-CAMP, PERF-ASIN, PLACE, CAMP-RAW) — substrate for all PPC answers.
- [ ] **Wasted-spend detection** — "where am I wasting ad spend" (STP-led).
- [ ] **Search-term harvesting / negative-keyword identification** — "which search terms to negate" (STP).
- [ ] **ACOS/TACOS/ROI by SKU** — "what's my TACOS by SKU" (PROFIT premium).
- [ ] **Campaign budget-cap detection** — "which campaigns are budget-capped" (CAMP-RAW + PERF-CAMP).
- [ ] **True margin / profit-by-SKU with FX reconciliation** — makes the PPC answers profit-aware (PROFIT + COGS-TBL).
- [ ] **Provenance / run-logging** — every answer traceable to a DataDoe export; persisted to Supabase (trust requirement given prior abuse).

### Add After Validation (v1.x)

- [ ] **Keyword/target bid context surfacing** — once core Q&A is trusted; read-only bid context (KWT). Trigger: operator starts asking "should I bid X on this keyword."
- [ ] **Placement analysis** — TOS vs rest vs product-page (PLACE). Trigger: operator asks about placement performance.
- [ ] **Budget-cap impact quantification** — estimate forgone profitable sales. Trigger: budget-cap detection proves accurate and operator wants the $ size.
- [ ] **Margin-aware PPC reasoning (explicit join)** — formalize PROFIT×PPC narration. Trigger: per-SKU margin numbers spot-check clean.

### Future Consideration (v2+ / later milestones)

- [ ] **Repeat-purchase / CLV reconstruction** (ORDERS hashed buyer_email) — high complexity, reconstruction not native; defer until there's a concrete payback question.
- [ ] **US-marketplace-specific logic** — schema ready; logic deferred until CA is solid (docs/03).
- [ ] **Listing optimization intelligence** — Milestone 2 (draft-only).
- [ ] **Scheduled PPC review** — Milestone 3 (on-open/always-on; respects desktop constraint).
- [ ] **Approve-ready PPC change *proposals* (bid/budget/negative)** — Milestone 3; human-executed, logged. Still no autonomous writes.
- [ ] **Gated write-MCP** — deferred, separate, trust-gated decision. Only after recommendations earn trust.

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Supabase truth store + context load | HIGH | MEDIUM | P1 |
| DataDoe read/compute primitives | HIGH | MEDIUM | P1 |
| Wasted-spend detection | HIGH | MEDIUM | P1 |
| Search-term harvesting / negative-ID | HIGH | MEDIUM | P1 |
| ACOS/TACOS/ROI by SKU | HIGH | LOW | P1 |
| Campaign budget-cap detection | HIGH | MEDIUM | P1 |
| True margin / profit-by-SKU (+FX) | HIGH | MEDIUM–HIGH | P1 |
| Provenance / run-logging | HIGH | MEDIUM | P1 |
| Keyword/target bid context | MEDIUM | MEDIUM | P2 |
| Placement analysis | MEDIUM | MEDIUM | P2 |
| Margin-aware PPC reasoning (explicit join) | HIGH | MEDIUM | P2 |
| Budget-cap impact quantification | MEDIUM | MEDIUM–HIGH | P2 |
| Repeat-purchase / CLV | MEDIUM | HIGH | P3 |
| US-specific logic | MEDIUM | MEDIUM | P3 |
| Any autonomous write/automation | — | — | FORBIDDEN |

**Priority key:** P1 = must-have for Milestone 1 launch · P2 = add when core is validated · P3 = future · FORBIDDEN = anti-feature.

## Competitor Feature Analysis

How established tools handle these analyses, and where Habib OS deliberately diverges.

| Feature | Dashboard tools (Helium10 / AdBadger / Perpetua) | DataDoe (raw data layer) | Our Approach (Habib OS) |
|---------|--------------------------------------------------|--------------------------|-------------------------|
| Negative-keyword finding | Surface candidates *and* auto-apply / rule-based automation | Provides STP raw export | Surface candidates only; **never auto-apply** — human proposal + ledger |
| ACOS/TACOS by SKU | Dashboards; TACOS often account-level not per-SKU | PROFIT premium gives per-SKU ACOS/TACOS/ROI precomputed | Per-SKU from PROFIT, read conversationally, margin-aware |
| Budget-cap detection | Uses Amazon's native Lost-IS (budget) column | No native Lost-IS column exposed | Approximate via spend-hits-budget pattern; flag as estimate |
| True margin / FX | Generic FBA calculators; FX usually ignored or manual | PROFIT (CAD) + operator `cogs` | Reconcile PROFIT vs operator landed cost; surface FX assumption explicitly |
| Bid/budget changes | Automated bid rules / autopilot | Read-only (no write) | Read-only context in M1; human-approved proposals in M3; **never autopilot** |
| Reporting trust | Vendor dashboards (the prior agency fabricated these) | Auditable raw exports | Every claim traceable to a logged DataDoe export — structural anti-fabrication |

## Sources

PPC negative keywords / search-term harvesting / wasted spend (thresholds: ~10–20 clicks zero-conversion; 25–40% wasted spend):
- [AdBadger — Amazon PPC Negative Keywords (2026)](https://www.adbadger.com/blog/amazon-ppc-education/negative-keywords-amazon-ppc/)
- [SellerMetrics — Find, Use & Optimize Negative Keywords](https://sellermetrics.app/negative-keywords-amazon-ppc/)
- [Headline — Amazon Negative Keywords: Profitability-First Guide](https://www.headlinema.com/blog/amazon-negative-keywords)
- [CaptenAMZ — Amazon Negative Keywords 2026 Strategy Guide](https://captenamz.com/blog/amazon-negative-keywords/)

ACOS vs TACOS, per-SKU profit, placement segmentation by margin:
- [DataDoe — Amazon ACoS vs TACoS](https://www.datadoe.com/blog-posts/amazon-acos-vs-tacos)
- [Perpetua — Amazon Total ACoS (TACoS)](https://perpetua.io/blog-amazon-tacos/)
- [Canopy Management — Ultimate Guide to ACoS and TACoS](https://canopymanagement.com/ultimate-guide-to-acos-and-tacos/)
- [Adverio — Amazon KPIs That Drive Profit](https://www.adverio.io/amazon-kpis-that-drive-profit-2/)

Budget caps / lost impression share / placement & TOS:
- [AdLabs — Amazon PPC Budget & Spend Optimization Guide](https://adlabs.app/guides/amazon-ppc-budget-guide/)
- [Headline — What is Impression Share](https://www.headlinema.com/blog/what-is-impression-share)
- [ScaleInsights — Fix Low/No Impressions in Amazon PPC](https://scaleinsights.com/learn/how-to-fix-low-or-no-impressions-in-amazon-ppc)

True margin / landed cost / Canada FBA / FX (CAD/USD):
- [Amazon Seller Central — Canada FBA Profitability Calculator](https://sellercentral.amazon.com/fba/profitabilitycalculator/index?lang=en_CA)
- [CanAm Currency — Managing CAD/USD for Amazon sellers](https://canamcurrencyexchange.com/currency-exchange-for-online-sellers-managing-cad-usd-for-amazon-etsy-and-shopify-stores/)
- [Amazon Currency Converter for Sellers (ACCS)](https://sell.amazon.com/programs/amazon-currency-converter)
- [SAL Accounting — Selling Internationally on Amazon (CA importer)](https://salaccounting.ca/blog/international-selling-amazon-fba/)

Internal (authoritative for source mapping & guardrails):
- `docs/04-data-tools-reference.md` (confirmed DataDoe sources + columns)
- `docs/02-context-and-constraints.md` (guardrails, abuse history, margin authority)
- `docs/03-scope-and-phases.md` (Milestone 1 acceptance questions)
- `.planning/PROJECT.md` (active requirements, out-of-scope reasoning)

---
*Feature research for: Amazon FBA PPC & profit intelligence (read-only conversational Q&A)*
*Researched: 2026-06-08*
