# DataDoe Source Map (CONN-03)

> **Empirical artifact.** Per RESEARCH §Pitfall 1, every column list, ad-program
> scope, timezone basis, and premium-enablement flag below comes from a live
> `exports_sources_get` call against the connected DataDoe MCP — never guessed.

**Status:** Resolved empirically via live `exports_sources_get` /
`sellers_and_vendors_list` / `organization_and_subscription_details_get`.
**Marketplace scope:** amazon.ca only (CAD, marketplace `A2EUQ1WTGCTBG2`).
**Seller UUID:** `5692b95f-f3f0-4063-9c1c-40177c54f408` (cached in `.env` as
`AMAZON_CA_SELLER_ID`; resolved via `sellers_and_vendors_list`).
**Last updated:** 2026-06-08

---

## 1. Connection state (empirically verified this session)

Source of truth: **DataDoe** `sellers_and_vendors_list` + organization details
(DataDoe is the project's single Amazon data source per CLAUDE.md — *not* Agent
Central, which is a separate, unrelated service).

| Connection | State | Evidence |
|------------|-------|----------|
| DataDoe seller (ANABTAWI SWEETS CA) | **Connected**, `marketplaceId=A2EUQ1WTGCTBG2` (CA), 12,268 rows | `sellers_and_vendors_list` |
| Seller Central (amazon.ca) | **Connected** — `initialLoadComplete: true`, 12,268 rows (conn `90612dbe-…`) | `sellers_and_vendors_list` |
| Amazon Ads (amazon.ca) | **Connected** — `initialLoadComplete: true`, 11,105 rows (conn `77044907-…`, profile `A13QU1H2J81LX0`) | `sellers_and_vendors_list` |
| Vendor Central | Not present (seller account, not vendor) — expected | `sellers_and_vendors_list` |
| DataDoe org / plan | `rami@habibdistribution.com`; 23,373 / 30M data rows; $97/mo, next bill 2026-06-28 | `organization_and_subscription_details_get` |

> **Correction to earlier scaffold:** an earlier draft recorded Seller Central /
> Amazon Ads as "NOT connected." That was the **Agent Central** API key's status
> (a different service, trial ended) and does **not** describe DataDoe. Via
> DataDoe — the architecture's only data source — both Seller Central and Amazon
> Ads are connected and fully loaded for amazon.ca.

**Hermes-CLI MCP wiring (separate from DataDoe being reachable in-session):**
`~/.hermes/config.yaml` `servers:` is still empty (`hermes mcp list` → "No MCP
servers configured"). DataDoe is callable in the agent session but not yet
registered in the Hermes desktop/CLI runtime. Operator action — see §5.

---

## 2. DataDoe read-only confirmation (CONN-01)

DataDoe's tool surface is **read-only by construction** — confirmed by
enumerating the surface (never by attempting a write; CLAUDE.md hard rule 1):

| Tool | Operation | Mutates Amazon? |
|------|-----------|-----------------|
| `sellers_and_vendors_list` | read — resolve seller/vendor UUIDs | No |
| `exports_sources_get` | read — enumerate sources + columns | No |
| `exports_create` | read — submit a SELECT-style export job (not an Amazon write) | No |
| `exports_get` | read — poll job status | No |
| `exports_raw_download` / `exports_raw_url_get` | read — fetch export artifact | No |
| `organization_and_subscription_details_get` | read — plan/usage | No |
| `actions_*` / docs tools | read/diagnostic | No |

No write / bid / budget / negative / listing / pricing tool exists in the
surface. Read-only verified live this session (three read calls executed, all
returned data; no mutate tool present).

---

## 3. Sources enumerated live (`exports_sources_get`)

### 3a. Profit & Margin (Seller Central) — **margin authority**

| Source ID | Table | Grain | Key columns | tz basis | Premium | Fetch |
|-----------|-------|-------|-------------|----------|---------|-------|
| `57a0cb319c` | `amazon_profit_by_sku_and_date` — **Profit by SKU & Date** | 1 row per marketplace × connection × child_asin × sku × date | `profit`, `total_cost`, `acos`, `tacos`, `roi`, `total_sales`, `total_units_sold`, `total_orders`, `cogs_item/shipping/total`, `total_fees`, `fba_fees`, `awd_fees`, `ad_spend`, `ad_sales`, `ad_orders`, `ad_units_sold`, `ad_clicks`, `ad_impressions`, `buybox_percentage`, `page_views`, `currency` | `date` = **marketplace-local** (CA) | **PREMIUM — ENABLED** | CONTINUOUS |
| `b24cd69c06` | `amazon_profit_by_date` — Profit by Date | daily aggregate (no SKU) | same metric set, no `sku`/`asin` | marketplace-local | **PREMIUM — ENABLED** | CONTINUOUS |

**Definitions returned live (use verbatim; do not re-derive):**
- `acos` = ad_spend ÷ **14-day** ad sales, as a percentage.
- `tacos` = ad_spend ÷ **total_sales**, as a percentage.
- `roi` = profit ÷ total_cost, as a percentage.
- `total_cost` = settlement fees + cogs_total + ad_spend.
- `ad_sales`/`ad_orders`/`ad_units_sold` attribution: **14d** for SPONSORED_BRANDS
  & SPONSORED_DISPLAY, **7d** for SPONSORED_PRODUCTS (mixed-window — note when
  reconciling against per-program ad tables).
- `total_fees` is **negative**; FBA/AWD fees are subsets of it.

→ Phase-2 implication: the locked margin authority is live and enabled, so the
`cogs_fallback` path is genuinely a *reconciliation/fallback*, not the primary.
RESEARCH Open-Question Q4 is **resolved: ENABLED**.

### 3b. Sales / Orders / Settlements (Seller Central)

| Source ID | Table | Grain | Notable columns | Premium | Fetch |
|-----------|-------|-------|-----------------|---------|-------|
| `89b27535d2` | `amazon_order_items_with_cogs` — Order Line Items | order × line item | `item_price_value` (only column for order value), `quantity`, COGS cols, hashed `buyer_email` (retention key), `order_purchased_at_utc` (UTC) + `date` (marketplace-local) | No | INITIAL 730d / DAILY 28d |
| `401ffcd7e5` | `amazon_sales_and_traffic_with_cogs` — Sales & Traffic by ASIN & Date | child_asin × date | sessions, `page_views`, `buybox_percentage`, `units_session_percentage`, `total_sales/units/orders`, COGS (nullable) | No | INITIAL 60d / DAILY 4d (may lag ≤4d) |
| `732dac689a` | `amazon_settlements_with_cogs` — Settlements & P&L | settlement × SKU/ASIN | full fee decomposition (`referral_fee`, `fba_*`, `awd_*`, refunds, promotions, `cost_of_advertising`), `total`, COGS; expenses negative | No | CONTINUOUS |

### 3c. PPC / Amazon Ads

| Source ID | Table | Program scope | Use for | Premium |
|-----------|-------|---------------|---------|---------|
| `e94e967198` | `amazon_ads_search_terms_by_campaign_by_date` — Search Term Performance | SP, SB | **negative-keyword harvesting** (`ad_search_term`, `ad_keyword`, `ad_match_type`, spend/sales/orders, `ad_keyword_bid`) | No |
| `bbba3d213a` | `amazon_ads_targeting_by_campaign_by_date` — Keyword Targeting | SP/SB/SD | bid/target perf (`ad_keyword`, `ad_match_type`, `ad_top_of_search_impression_share`) | No |
| `08cdc77d3d` | `amazon_ads_performance_by_campaign_by_date` — Ad Perf by Campaign | SP/SB/SD | campaign roll-up + budget (`ad_campaign_budget_amount`, `ad_campaign_budget_type`), invalid-traffic cols | No |
| `d0017e92fb` | `amazon_ads_performance_by_child_asin_and_date` — Ad Perf by ASIN | **SP, SD only (no SB)** | per-ASIN ad perf; `ad_campaign_id`/`name`/`status` NULL for SD | No |
| `0dd6cbf08c` | `amazon_ads_sponsored_brands_by_ad_by_date` — SB Ad Performance | SB | SB-specific (new-to-brand, video metrics) | No |
| `3d720918e6` | `amazon_ads_placement_by_campaign_by_date` — Ad Placement | SB, SP | placement (`ad_placement_classification`) | No |
| `7c1ba29e52` | `amazon_ads_by_ad_group_by_date` — Ad Group Performance | SB, SD | ad-group roll-up | No |
| `90b696e336` | `amazon_ads_campaigns_raw` — Ad Campaigns (raw config) | SP/SB/SD | **budget-capped detection**: `ad_campaign_delivery_status`, `ad_campaign_delivery_reasons` (JSON), `ad_campaign_budget_caps` (JSON), bid strategy, state | No |

> **"Budget-capped" answer path:** there is no single boolean column. Derive it
> from `amazon_ads_campaigns_raw.ad_campaign_delivery_status` /
> `ad_campaign_delivery_reasons` (and/or budget vs. spend from the campaign perf
> table). Hand-write this rule in Phase-2+ money logic, not in skill prose.

### 3d. Listings / SEO / catalog / retention (Seller Central)

| Source ID | Table | Grain | Use for | Premium |
|-----------|-------|-------|---------|---------|
| `81aa5b4cc2` | `amazon_child_product_organic_search_ranks_per_week` | child_asin × query × week | organic rank per query (`child_asin_organic_search_rank` 1–100) | No (data may be incomplete) |
| `df4160ff8e` | `amazon_child_product_organic_search_ranks_per_month` | child_asin × query × month | monthly organic rank | No (may be incomplete) |
| `8772614caf` | `amazon_child_product_search_performance_per_month` — Search Engagement | child_asin × month | impressions/CTR/cart-adds/purchases/conv (organic + ads) | No |
| `68d2de238e` | `amazon_products_by_child_asin` — Product Catalog | child_asin | titles, bullets, description, brand, category, BSR | No (CONTINUOUS) |
| `8723a9f82b` | `amazon_repeat_purchase_report` — Repeat Purchase | child_asin × month | `repeat_customers_score_total`, repeat revenue | No |

### 3e. Inventory (Seller Central)

| Source ID | Table | Grain | Use for | Premium |
|-----------|-------|-------|---------|---------|
| `2a81389e42` | `amazon_fba_inventory_by_asin_by_country` — FBA Inventory | asin × sku × country × date | on-hand `quantity_for_local_fulfillment` | No (DAILY 1d) |
| `44fc5ba0ce` | `amazon_fba_inventory_health` — FBA Inventory Health | asin × sku × date | `days_of_supply`, `weeks_of_cover_t30/t90`, aged-inventory buckets, storage-fee estimates, inbound qty, recommended actions | No (DAILY 1d) |

---

## 4. Profit by SKU — enablement determination

**RESOLVED — ENABLED.** `amazon_profit_by_sku_and_date` (`57a0cb319c`) is
`isPremium: true` and the live `exports_sources_get` returned its full column set
(profit, total_cost, acos, tacos, roi, full COGS + fee decomposition). It is the
locked margin authority; `cogs` (SCD-2 + per-row FX) is the documented
reconciliation/fallback path, not the primary. SKU coverage is confirmed at the
schema level (grain includes `sku`); per-SKU completeness is validated at the
first real export pull in Phase 2 (DATA-05). No export pull performed here.

---

## 5. Remaining operator actions (not blockers for the source map)

These do **not** block this map (resolved live) but are needed before Wave 2 and
for the Hermes desktop runtime:

1. **Supabase connection strings** → fill `SUPABASE_DB_URL` (direct, 5432) and
   `SUPABASE_DB_URL_POOLED` (pooled, 6543) in `.env` from Supabase **Settings →
   Database**. *Required before 01-02 pushes migrations against live Supabase.*
2. **Wire the DataDoe MCP into the daily runtime.** Runtime decision (2026-06-09):
   the daily runtime is **Claude Cowork** (Max subscription), not Hermes — connect
   DataDoe as a Cowork custom connector. See `docs/cowork-setup.md`.

---

## 6. Phase-2 live-pull resolution (DATA-05 / A1 / A2 / A3 — 2026-06-09)

First real pull executed against the live DataDoe MCP (CA, trailing 30d). Findings:

- **Column name:** the SKU column is **`sku`** (earlier scaffold assumed `seller_sku`).
- **A2 — percent convention RESOLVED:** `acos`/`tacos`/`roi` are **percentages**
  (`30.0` = 30%), verified row-wise (`acos == ad_spend/ad_sales*100`). Matches the
  seeded thresholds (acos=30 / tacos=15). No 100× unit risk.
- **A1 — window aggregation RESOLVED (locked):** the source computes the ratios at
  **daily** grain only; there is **no per-SKU trailing-window ratio column**, and
  DataDoe's `groupBy` aggregations (sum/avg/min/max) **cannot** emit a correct window
  ratio (averaging a daily ratio is wrong). Decision (operator-approved): pull a
  server-side **`groupBy ["sku","currency"]` + `sum`** of the components (aliased `*_sum`
  — bare aliases collide with source column names) and let the reviewed
  `habibos.tacos` compute the window ratio from the sums (`tacos=Σad_spend/Σtotal_sales`,
  etc.), applying the source's verbatim definitions. NOT silent recomputation — it is
  window aggregation of source components, and it was escalated + approved.
- **A3 — fetch RESOLVED:** `exports_raw_download` returns the artifact inline; the
  per-SKU `groupBy` export is small (~22 rows). A raw daily pull (~455 rows) spills to a
  file (>token cap) — prefer the aggregated pull.
- **Sanitization:** the `groupBy` export carries **no seller UUID / utility columns**
  (collapsed by the group-by), so it is safe to persist as `tests/fixtures/
  profit_by_sku_30d.csv` after review. (A raw daily export DOES prepend the seller UUID —
  sanitize before persisting.)
- **TRUST-04:** operator spot-checked the live answer against Seller Central — reconciles,
  CA-only, no marketplace bleed.
