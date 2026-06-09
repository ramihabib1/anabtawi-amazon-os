---
name: profit-analysis
description: Playbook for profit, margin, ROI, fee drag, and customer/repeat analysis for Anabtawi. Use for "how is the business doing", margin erosion, per-SKU profitability, fee or ad drag, and repeat-purchase / CLV questions.
---

# Profit & Business Analysis

Load `datadoe-query` and `anabtawi-context` first.

> **NUMBERS COME FROM THE ENGINE, NOT PROSE (CLAUDE.md hard rule 4).** Per-SKU
> ACOS/TACOS/ROI/margin and threshold flags are computed by the tested CLI (see
> `datadoe-query` → "Money math": `groupBy sku + *_sum` → `engine/scripts/answer_tacos.py`).
> You interpret its typed JSON and write the narrative; you never re-derive the ratio in
> chat. Top-line trend (sales/profit/ROI/TACOS over time) and CLV come from the tables, but
> any per-SKU ratio or breach is the CLI's output. Flag null/zero-COGS SKUs as unreliable.

## Top-line
`amazon_profit_by_date` (b24cd69c06): trend `total_sales, profit, total_cost, roi, tacos`
over trailing 7 / 28 / 90 with prior-period deltas. Always report **profit and ROI**, not
just revenue.

## Per-SKU
`amazon_profit_by_sku_and_date` (57a0cb319c): rank by trailing-90 profit and ROI. Surface
**losers** (`profit < 0`), **margin erosion** (ROI falling), **fee drag** (`fba_fees + awd_fees`
share of sales rising), and **ad drag** (`tacos` rising). Tie findings to tiers in
`anabtawi-context`.

## Customer / repeat (CLV)
`amazon_order_items_with_cogs` (89b27535d2): group by `buyer_email` (hashed, stable) for
repeat rate, orders-per-buyer, and which SKUs drive re-orders. Use `address_state` for
geographic concentration and `order_is_business` for B2B share.

## Output
Quick questions → answer in chat with the source + window noted. Recurring reviews →
contribute the numbers + a 3-bullet narrative to the weekly/monthly deliverables. Flag any
SKU with null/zero COGS as unreliable profit.
