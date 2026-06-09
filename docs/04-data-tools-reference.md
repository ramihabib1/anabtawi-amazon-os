# Data Tools Reference

All Amazon data comes from **DataDoe** (read-only). Agent Central is not used. Your DataDoe org has the Amazon Ads connection attached, so PPC data is fully available.

## DataDoe call pattern (always this order)
1. `sellers_and_vendors_list` → resolve seller UUID (amazon.ca seller is `5692b95f-f3f0-4063-9c1c-40177c54f408`; cache in `.env`).
2. `exports_sources_get(query, sellerOrVendorIds)` → find a source + its columns (full schema: https://datadoe.com/hub/data-scheme).
3. `exports_create(...)` → SQL-style query: `sourceId`, `columns` (req), `outputType` (CSV/JSON), `filters` (WHERE), `groupBy` + `aggregations`, `from`/`to` (req if source has a date col), `dateInterval`, `orderBy*`, `limit` (**cap 2500**), `skip`.
4. Poll `exports_get(id)` → COMPLETED/FAILED.
5. Read via `exports_raw_download` or `exports_raw_url_get`.

## Confirmed sources for this build

### PPC (Amazon Ads)
- **Search Term Performance** (`amazon_ads_search_terms_by_campaign_by_date`) — search term → matched keyword, spend, sales, orders, impressions, clicks, CTR, keyword bid, match type. Core for negative-keyword harvesting and search-term optimization.
- **Keyword Targeting Performance** (`amazon_ads_targeting_by_campaign_by_date`) — keyword/target per campaign with top-of-search impression share, bid.
- **Ad Performance by Campaign & Date** (`amazon_ads_performance_by_campaign_by_date`) — campaign spend/sales/orders/units, budget amount & type, invalid impressions.
- **Ad Performance by ASIN & Date** (`amazon_ads_performance_by_child_asin_and_date`) — per-ASIN ad performance (SP + SD).
- **Ad Placement Performance** (`amazon_ads_placement_by_campaign_by_date`) — top-of-search vs rest-of-search vs product-page performance.
- **Ad Campaigns (raw)** (`amazon_ads_campaigns_raw`) — campaign config: budgets, budget caps, bid strategy, placement bid adjustments, state. The settings snapshot.

### Listings / SEO (Seller Central)
- **Organic Search Ranks by ASIN** (weekly / monthly) — organic rank per ASIN per search query, query volume, impressions, clicks, conversions.
- **Search Engagement by ASIN (Monthly)** — impressions, CTR, cart-adds, purchases, conversion rate per child ASIN (organic + ads).

### Profit & Orders (Seller Central)
- **Profit by SKU & Date** (`amazon_profit_by_sku_and_date`, PREMIUM) — net profit, total cost (fees + COGS + ad spend), **ACOS, TACOS, ROI**, sales, units, fba/awd fees, ad spend/sales, buybox %, page views. Prefer this for margin. Confirm it's enabled on the plan.
- **Order Line Items** (`amazon_order_items_with_cogs`) — order/item grain with COGS and a hashed `buyer_email` (enables repeat-purchase / CLV if needed). Non-premium sales fallback.

## Not available (Agent Central removed)
Granular FBA long-term storage fees; native repeat-purchase and Subscribe & Save metrics. Fee drag still appears in the Profit table; repeat-purchase is reconstructable from Order Line Items' hashed buyer_email.

## Writes
None here. Bid/budget/negative/listing changes are out of scope until a dedicated, human-gated write-MCP exists (deferred milestone).
