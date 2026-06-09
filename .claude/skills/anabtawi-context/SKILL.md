---
name: anabtawi-context
description: Brand, catalog, and commercial context for ANABTAWI SWEETS CA on amazon.ca. Use for any Anabtawi-specific question so analysis is grounded in the real catalog, SKU tiers, COGS, and seasonality. Reference content — load it whenever interpreting results for this account.
---

# Anabtawi Sweets — Brand & Catalog Context

- **Marketplace:** amazon.ca (Canada), CAD. FBA + AWD.
- **Category:** Middle Eastern food / sweets (shelf-stable). Watch expiry/lot-sensitivity:
  aged FBA inventory isn't just a fee problem here, it's a freshness problem.

## SKU tiers
Maintain the live SKU list below. Tier drives how aggressively each SKU is defended in PPC
and restock. (Fill from the latest portfolio scoring; update monthly via `pnl-monthly`.)

| Tier | Meaning | PPC posture | Restock posture |
|------|---------|-------------|-----------------|
| HERO | Top profit + velocity | Defend rank, accept higher ACOS | Never stock out |
| MAINTAIN | Steady contributors | Hold target ACOS | Standard cover |
| CUT | Low velocity / margin | Minimal/no spend | Sell through, don't reorder |

> TODO (Rami): paste the current SKU → ASIN → tier → landed-COGS table here. Until then,
> derive tiers at runtime from `amazon_profit_by_sku_and_date` (rank by trailing-90 profit
> and velocity) and flag that tiers are inferred, not authoritative.

## Commercial notes
- COGS in DataDoe profit tables reflects landed cost if maintained in DataDoe; if a SKU's
  COGS looks like 0/null, treat its profit as unreliable and flag it.
- Seasonality: note Ramadan/Eid and holiday gifting spikes — pull forward restock and budget.
- Family/operating context: sales & marketing and finance are handled by others; this
  workspace owns the technical + analytical operation of the marketplace.
