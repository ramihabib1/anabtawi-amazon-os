---
name: inventory-restock
description: Playbook for FBA inventory health, restock timing/quantity, aged and excess stock, and low-inventory-fee and storage-cost risk for Anabtawi. Use for any question about stock levels, reorders, days of supply, or removals. Produces a reviewable restock plan — it never places orders.
---

# Inventory & Restock Planning

Load `datadoe-query` and `anabtawi-context` first. Read targets from `state/targets.md`.

## Input
`amazon_fba_inventory_health` (44fc5ba0ce) — latest snapshot. Cross-check velocity with
`amazon_profit_by_sku_and_date`. For inbound pipeline use `amazon_awd_replenishment_orders`
(cedb259753).

## Stockout side (protect revenue)
For each SKU compute cover from `days_of_supply`, `weeks_of_cover_t30/t90`, and velocity
(`units_shipped_t30`, `sales_shipped_last_30_days`). Flag **RESTOCK NOW** when projected
cover (including `inbound_quantity`) falls below `min_weeks_cover` (tier-weighted; HEROs
never stock out). Anchor against Amazon's own `recommended_ship_in_quantity` /
`recommended_ship_in_date` but adjust for known lead time and seasonality. Watch
`fba_inventory_level_health_status` and `low_inventory_level_fee_applied_in_current_week`.

## Excess side (protect margin & freshness)
Flag `estimated_excess_quantity > 0`, aging into `inv_age_271_to_365_days`, or
`no_sale_last_6_months`. For food, treat old lots as freshness risk, not just storage fees.
Use `recommended_action`, `recommended_removal_quantity`, and
`estimated_cost_savings_of_recommended_actions`; quantify `estimated_storage_cost_next_month`.

## Output (to `deliverables/restock-plan_{date}.xlsx`)
Tab 1 — Restock: SKU · on-hand · inbound · velocity (t30) · cover weeks · recommended qty ·
ship-by date · flag. Tab 2 — Reduce: SKU · excess qty · age · recommended action · savings.
Summary with total units to ship and capital required. **Wait for approval before any PO or
removal.** Log approved actions to `state/decisions.md`.
