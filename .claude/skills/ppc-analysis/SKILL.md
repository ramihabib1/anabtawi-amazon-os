---
name: ppc-analysis
description: Playbook for analyzing and optimizing Anabtawi's Amazon advertising. Use for any question about ACOS, TACOS, ad spend, wasted spend, bids, budgets, or campaign/ad-group/ASIN ad performance. Produces a reviewable bid & budget change sheet — it never changes the live account.
---

# PPC Analysis & Optimization

Load `datadoe-query` and `anabtawi-context` first. Read targets from `state/targets.md`.

## Inputs
- Per-ASIN efficiency: `amazon_ads_performance_by_child_asin_and_date` (d0017e92fb).
- Ad group / placement / SB: `7c1ba29e52`, `3d720918e6`, `0dd6cbf08c`.
- Blended truth: `amazon_profit_by_sku_and_date` (57a0cb319c) for `acos, tacos, ad_spend,
  ad_sales, profit` per SKU — always cross-check ad-console ACOS against profit-table TACOS.

## What to find (rank by $ impact)
1. **Wasted spend** — clicks/spend with zero or near-zero `ad_orders` over trailing 14–28d.
   Candidates to pause or cut bids. (Negative-keyword mining needs the search-term source —
   flag if not yet wired in.)
2. **ACOS breaches** — campaigns/ASINs above `target_acos` (per tier) for ≥7d. Recommend a
   bid reduction sized to the overspend.
3. **Budget-capped winners** — campaigns at/near `ad_campaign_budget_amount` with ACOS below
   target and rising sales. Recommend a budget raise.
4. **TACOS drift** — SKUs where `tacos` is climbing while organic share falls: the ads are
   buying sales that used to be organic. Flag for structural review.
5. **Tier mismatch** — HERO SKUs underfunded, CUT SKUs still spending.

## Output (to `deliverables/ppc-changes_{date}.xlsx`)
One row per recommended change: SKU/ASIN · campaign · metric (bid/budget/status) ·
current → proposed · trailing ACOS/TACOS · expected effect · confidence. Summary tab with
total projected spend delta and the rationale. **Stop there — wait for approval.**

## Acting (Phase 2, optional)
If a SP-API (or Amazon Ads API) write-back MCP is connected, execution is a *separate,
approval-gated* step: dry-run the diff, get explicit "apply", then write, then append each
applied change to `state/decisions.md`.
