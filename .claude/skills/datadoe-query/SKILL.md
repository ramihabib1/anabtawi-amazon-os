---
name: datadoe-query
description: Canonical guide for pulling Anabtawi Amazon data from the DataDoe MCP. Use whenever you need sales, profit, advertising, inventory, or order data — before calling any DataDoe tool. Contains the seller ID, the source catalog with table IDs and columns, which table to prefer for which question, and the query/polling rules.
---

# Querying DataDoe for Anabtawi

DataDoe is the **read-only analytics layer**. You request an export (CSV/JSON), poll until
it completes, then download and analyze. It does **not** write back to Amazon.

## Account
- **sellerOrVendorId:** `5692b95f-f3f0-4063-9c1c-40177c54f408` (ANABTAWI SWEETS CA)
- **Marketplace:** amazon.ca · marketplace_id `A2EUQ1WTGCTBG2` · currency CAD

## The workflow (every pull)
1. `exports_create` with `sellerOrVendorIds`, `sourceId`, `columns`, `outputType:"CSV"`,
   and — if the source has a `date` column — `from`/`to` (required, inclusive).
2. Poll `exports_get(exportId)` until status is `COMPLETED` (or `FAILED`).
3. `exports_raw_download(exportId)` for the content. Save it to `data/{table}_{from}_{to}.csv`.
4. If a needed source isn't in the catalog below, discover it with
   `exports_sources_get(query, sellerOrVendorIds)` and add it here.

## Hard rules
- **Row cap is 2500 per export.** If a query would exceed it: aggregate (`groupBy` +
  `aggregations`), filter, top-N (`orderByColumn`/`orderByDirection` + `limit`), or paginate
  with `skip`. Never assume you got the full table.
- **Dates are required** on any source with a `date` column. Use real dates (today is the
  reference). Default windows: yesterday, trailing 7, trailing 28/30.
- **`filters`** = SQL WHERE on raw rows *before* aggregation (combinator `and`/`or`, per-rule
  operators `=, !=, >, >=, <, <=, in, between, contains, null, ...`).
- **`dateInterval`** (DAY/WEEK/MONTH) collapses a `date` group-by to that bucket.
- Prefer **purpose-built tables over manual math** (see "prefer" notes below).

## Source catalog (verified for this account)

### Money
- **Profit by SKU & Date** — `id: 57a0cb319c` (premium) · table `amazon_profit_by_sku_and_date`.
  The money table. Per SKU/ASIN/day: `profit, total_cost, total_sales, total_units_sold,
  total_orders, cogs_total, total_fees, fba_fees, awd_fees, ad_spend, ad_sales, acos, tacos,
  roi, buybox_percentage, page_views`, plus product metadata. **Prefer this for any profit/
  margin/ROI question — do not recompute profit from raw tables.**

> **VERIFIED LIVE (2026-06-09) — read before any money pull:**
> - The SKU column is **`sku`** (not `seller_sku`).
> - `acos/tacos/roi` are **percentages** (`30.0` = 30%, not `0.30`) — verified row-wise.
> - **A1 (locked):** these ratios are **DAILY** only; there is **no per-SKU window-ratio
>   column** and `groupBy` **cannot** aggregate a correct window ratio (avg of daily ratios
>   is wrong). To get a trailing-window per-SKU ratio, pull **`groupBy ["sku","currency"]`
>   + `sum`** of the components, aliased `*_sum` (a bare alias collides — `ALIAS_COLLISION`):
>   `ad_spend_sum, ad_sales_sum, total_sales_sum, profit_sum, total_cost_sum, total_units_sold→units_sum`.
>   The reviewed engine computes the ratio from the sums.

## Money math — ALWAYS via the engine CLI, never prose (CLAUDE.md hard rule 4)

Any ACOS / TACOS / ROI / margin / breach **number** comes from the hand-written, pytest-covered
engine — **never computed in chat**. After downloading the `groupBy sku + *_sum` export, run:

```
cd engine && uv run python scripts/answer_tacos.py \
  --artifact <downloaded.csv> --export-id <id> --marketplace CA \
  --status COMPLETED --window-from <from> --window-to <to>
```

It returns typed JSON (per-SKU `acos/tacos/roi` computed from the summed components, breach
flags vs `engine/config/thresholds.toml`, `no data` / `no sales` / refusal). The skills
**render and interpret** that JSON; they do not re-derive the numbers. The CLI catalog
defaults to `engine/tests/fixtures/ca_catalog_skus.txt` (re-seed from the real catalog).
- **Profit by Date** — `id: b24cd69c06` (premium) · table `amazon_profit_by_date`.
  Same metrics aggregated to the day. Use for top-line trend.

### Sales & orders
- **Order Line Items** — `id: 89b27535d2` · table `amazon_order_items_with_cogs`.
  Near-real-time order log (initial 730d, daily refresh 28d). Use for **recent/precise**
  sales, geography (`address_state/city`), B2B (`order_is_business`), and **repeat/CLV** via
  `buyer_email` (hashed, stable per buyer). Use `item_price_value` for order value. Aggregate
  for per-product or per-day totals.
- **Sales & Traffic by ASIN & Date** — `id: 401ffcd7e5` · table `amazon_sales_and_traffic_with_cogs`.
  Per child ASIN/day: `session, page_views, units_session_percentage` (conversion),
  `buybox_percentage, total_sales, total_units, total_orders, cogs_*`. **Prefer for
  long-period and traffic/conversion analysis.** Data can lag up to 4 days — for the last few
  days use Order Line Items instead.

### Advertising
- **Ad Performance by ASIN & Date** — `id: d0017e92fb` · `amazon_ads_performance_by_child_asin_and_date`
  (SP + SD, per ASIN). Use for per-ASIN ad efficiency.
- **Ad Group Performance** — `id: 7c1ba29e52` · `amazon_ads_by_ad_group_by_date`.
- **Ad Placement Performance** — `id: 3d720918e6` · `amazon_ads_placement_by_campaign_by_date`
  (SB + SP, top-of-search vs rest).
- **Sponsored Brands by Ad & Date** — `id: 0dd6cbf08c` · `amazon_ads_sponsored_brands_by_ad_by_date`.
- Common ad columns: `ad_spend, ad_sales, ad_clicks, ad_impressions, ad_orders,
  ad_units_sold, ad_campaign_name, ad_campaign_status, ad_campaign_budget_amount`,
  plus new-to-brand metrics. SP sales are 7-day attribution; SB/SD are 14-day.
- **Ad Performance by Campaign & Date** — `id: 08cdc77d3d` · `amazon_ads_performance_by_campaign_by_date`
  (SP + SB + SD, per campaign). Prefer for campaign-level rollups; per-ASIN table only
  when ASIN attribution is needed. (Verified 2026-06-11.)
- **Search Term Performance** — `id: e94e967198` · `amazon_ads_search_terms_by_campaign_by_date`.
  **The negative-keyword lever.** Per date: `ad_search_term` (what the shopper typed),
  `ad_keyword`/`ad_targeting_text` (what you bid on), `ad_match_type, ad_campaign_name,
  ad_group_name, ad_keyword_bid, ad_spend, ad_sales, ad_orders, ad_clicks, ad_impressions`.
  SP + SB only (no SD). Backfill ~60d initial. (Verified 2026-06-11.)
- **Keyword Targeting Performance** — `id: bbba3d213a` · `amazon_ads_targeting_by_campaign_by_date`.
  Per advertised keyword/target: spend/sales/orders + `ad_top_of_search_impression_share`
  and `ad_keyword_status`. Use for the bid sheet (per-keyword bid decisions). (Verified 2026-06-11.)
- **Ad Campaigns (raw)** — `id: 90b696e336` · `amazon_ads_campaigns_raw`. Campaign config
  snapshot: state, delivery status, start/end date, `ad_campaign_optimization_bid_strategy`,
  placement bid adjustments (JSON), AUTO/MANUAL targeting, cost type. No date filter needed.
  Use for campaign-structure audits (orphaned/paused campaigns, bid-strategy review). (Verified 2026-06-11.)

### Inventory
- **FBA Inventory Health** — `id: 44fc5ba0ce` · `amazon_fba_inventory_health` (daily snapshot).
  The restock brain: `available, inbound_quantity (working/shipped/received), days_of_supply,
  weeks_of_cover_t30/t90, sell_through, units_shipped_t7/t30/t60/t90, recommended_ship_in_quantity,
  recommended_ship_in_date, fba_inventory_level_health_status, low_inventory_level_fee_applied_in_current_week,
  estimated_excess_quantity, inv_age_* buckets, estimated_storage_cost_next_month,
  recommended_action, recommended_removal_quantity, estimated_cost_savings_of_recommended_actions,
  sales_rank, supplier`.
- **AWD Replenishment Orders** — `id: cedb259753` · `amazon_awd_replenishment_orders`
  (status, inbound/outbound shipments).

### To discover and add as needed
Returns/concessions, settlement/fee detail, reviews/ratings, and listing/catalog quality —
use `exports_sources_get` with the relevant keywords, verify the columns, and append them
above so the next run doesn't rediscover them.

### Listing content & catalog (added)
- **Product Catalog by ASIN** — `id: 68d2de238e` · `amazon_products_by_child_asin`. Real
  listing copy: `product_name` (title), `product_bullet_point_1..5`, `product_description`,
  `product_image_url`, `product_brand`, `product_size`, category names, best-selling ranks.
  This is the source of truth for the listing audit — no scraping needed.
- **Listings** — `id: ba689c05d7` · `amazon_listings_with_cogs`. Live `listing_price_value`,
  `listing_status` (Active/Inactive/Incomplete), referral fee, FBA/AWD quantities, current COGS.
- **Product Catalog / Listings (Raw JSON)** — `0e1ea34395` / `6ea445cdc4`. Full SP-API
  `attributes` + `images` JSON. Heavy — download to file, don't load into context.
- **Seller Account Health** — `id: 57036be081` · `amazon_seller_performance`. Account status,
  ODR, policy/IP/food-safety violations, late-shipment — for the account-level audit.
- **FBA Ledger** — `829e34f54e` / `6a6e14526d`. Lost/damaged/returned units & reconciliation
  (reimbursement recovery).

## Write actions — the gated `actions_start` path (PPC writes only)

DataDoe's data layer above is **read-only** — it is for analysis, never a write-back. The **only**
write surface to Amazon is the gated `actions_start` path (CLAUDE.md hard rule 1: no autonomous
writes; every change is a reviewed artifact → explicit approval → a gated write). M2 scope is
**PPC writes only** (bids, budgets, states); catalog / restock / listing writes are deferred.

**The four write-path tools:**
- `actions_start(type, sellerOrVendorId, dryRun, details)` — stage an action. **ALWAYS `dryRun:true` first** (validate-only, makes **no** account change).
- `actions_get(actionId)` — poll a started action to a terminal status.
- `actions_list(...)` — enumerate prior actions (find a historical `actionId`).
- `actions_details_schema_get(...)` — read the JSON schema for an action type (read-only).

Action types use the **`AMAZON_ADS_`** prefix, one verb per call:
`AMAZON_ADS_CAMPAIGNS_FIND` / `_UPDATE` / `_REMOVE` / `_ADD` (likewise `AD_GROUPS`, `TARGETS`, `ADS`).
A `*_FIND` request carries **one ad-product** (`adProductFilter.include` `maxItems:1` —
`SPONSORED_PRODUCTS` | `SPONSORED_BRANDS` | `SPONSORED_DISPLAY`).

**1. FIND-before-write (WRITE-02).** Before any `_UPDATE`/`_REMOVE`, pull the live
`campaignId/adGroupId/targetId/adId` via the matching `*_FIND` tool and cache the result to
`data/ads_<entity>_<adProduct>_find_<date>.json` (`engine/src/habibos/find_cache.py` `write()`).
A later write whose entity ID is **not** in the cache is **refused at build** (`lookup()` →
`Refusal("stale/missing entity ID", "find_cache_miss")`) — never executed on a fabricated or stale ID.

**2. dryRun discipline (WRITE-01).** Fire `actions_start dryRun:true` first and **PROCEED only**
when `status == "VALIDATED"` **and** `validation.valid` is true **and** `validation.issues` is empty.
Do **not** classify in chat — the engine owns the verdict:
```
cd engine && uv run python scripts/classify_dryrun.py --artifact <dryRun_response.json>   # → proceed / stop
cd engine && uv run python scripts/classify_poll.py    --artifact <actions_get_response.json>  # → done / in_flight / refuse
```
The `ActionStartResponse` shape is `status` (top-level) + a **nested** `validation:{valid, issues}`
object (see `engine/tests/fixtures/dryrun_validated.json` / `dryrun_invalid.json`).

**3. Terminal-status enum (WRITE-05) — pinned verbatim** (matches `engine/src/habibos/datadoe.py`
`ACTION_TERMINAL`; a wrong name spins an infinite poll):
- **In-flight (keep polling):** `PENDING`, `IN_PROGRESS`, `WAITING_EXTERNAL_PROCESSING`
- **Terminal success:** `COMPLETED`
- **Terminal done-with-issues:** `PARTIALLY_COMPLETED`, `COMPLETED_WITH_ISSUES`
- **Terminal failure:** `ERROR`, `CANCELED`, `BLOCKED_NO_TOKENS`, `BLOCKED_INVALID_INPUT`

Note: there is **no** `FAILED` status, and `CANCELED` is spelled with **one L**. An unmodeled
status is refused (treated as neither terminal nor safe-to-spin), not assumed terminal.

**4. Reconcile via status, NEVER via export.** Confirm a write **only** by `actions_get` → a
terminal status **plus** a `*_FIND` echo of the changed entity. **Never** confirm by a next-day
DataDoe export — the analytics tables lag up to ~24h, so an export cannot confirm a just-applied write.

**5. HTTP refusals the agent must NOT retry:**
- `412` — action type **disabled** (org-enable it in DataDoe **Settings → Actions**; off by default). Do not retry; surface it.
- `402` — no AI tokens. Do not retry; surface it.
- `429` — rate limit (2 req/s). **Retryable** — honor `Retry-After`.
