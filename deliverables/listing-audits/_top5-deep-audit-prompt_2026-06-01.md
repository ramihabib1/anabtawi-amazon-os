# Prompt — Deep 360° Audit of the Top-5 SKUs (Anabtawi Sweets CA)

> Paste everything below the line into a fresh agent running in this workspace.

---

You are an operations analyst for **ANABTAWI SWEETS CA** (amazon.ca, FBA, CAD). Read `CLAUDE.md`
first, then **load the skills** `datadoe-query`, `anabtawi-context`, `profit-analysis`,
`ppc-analysis`, `inventory-restock`, and `listing-audit` before pulling any data. Read
`brain/wiki/` and the existing audits in `deliverables/listing-audits/` (the 2026-06-01 rollup,
account audit, and per-ASIN plans) so you build on prior work instead of repeating it.

## Your task
Run a **thorough, everything-included audit of these 5 SKUs only** — the account's profit core.
Go deep, not wide: this is a deep-dive on five products, not a catalog sweep.

| # | ASIN | SKU | Product | Price | Landed COGS | Rating (Rami, 2026-06) | Notes to verify |
|---|------|-----|---------|-------|-------------|------------------------|-----------------|
| 1 | B0FXX46ST8 | 18-116Z-1R77 | Baklava Gift Set 180g | $28.00 | $13.63 | Negative reviews (★ TBC) | Highest velocity (41u/90d), conv ~3.6%, near-duplicate of B0FTSM2HSJ (FX-M8MA, a margin loser) |
| 2 | B0FY6N6TRH | EU-Z87B-ZRBZ | Baklava 850g | $55.99 | $29.06 (new PI landed ~$37.74) | **4.1★**, negatives present | Top profit, only 1 unit in stock, margin ~8% at new cost — likely underpriced (~$70 to clear 25%) |
| 3 | B0FXX3JVR5 | T8-2W2X-INOK | Baklava 400g | $55.99 | $26.77 | **3.3★** ⚠ | Best converter (~6.2%) DESPITE low rating; near-duplicate of B0FTSMTDGP (9Z-KUHZ, 400g) |
| 4 | B0FTM6Y263 | Y4-Y8EE-VEOD | Barazek 400g | $32.99 | $11.76 | Negative reviews (★ TBC) | Only non-baklava hero, stock low (~8), conv ~3.1% |
| 5 | B0FY6PBYZS | 09-AJOP-CS83 | Classic Assorted 250g | $25.99 | $11.07 | Negative reviews (★ TBC) | Best margin (~35%), flagship assortment |

**⚠ START HERE — reviews are the lead issue, and the root cause is CONFIRMED.** Rami reports all
five carry negative reviews; the 400g baklava sits at **3.3★** (the account's *best converter*) and
the 850g at **4.1★**. **Rami has confirmed the recent negatives are driven by FRESHNESS / NEAR-EXPIRY
stock reaching customers** — a supply/rotation problem, not listing copy. Treat this as the governing
constraint: content/price fixes will NOT repair the rating; fresh, fast-rotating FBA stock will.
Verify the freshness theme in the live reviews, then prioritise the FBA-rotation actions below.

## Audit every dimension for each SKU
1. **Profit & unit economics** — trailing-30 and trailing-90 from `amazon_profit_by_sku_and_date`:
   profit, real margin %, ROI, total_fees, fba_fees, ad_spend, ACOS, TACOS. Recompute per-unit
   contribution at BOTH current COGS and the **new PI landed costs** (a recent proforma raised
   several costs — the 850g to ~$37.74). State the price needed to hold the 25% margin floor.
2. **Advertising** — `amazon_ads_performance_by_child_asin_and_date` (t30/t90): spend, sales,
   ACOS, clicks, impressions, orders, campaign names/budgets. Flag wasted spend, budget-capped
   winners, ACOS above the tier target in `state/targets.md`. Recommend bid/budget moves.
3. **Inventory & restock** — `amazon_fba_inventory_health`: available, inbound, days_of_supply,
   weeks_of_cover, sell-through, recommended_ship_in qty/date, aged/excess, low-inventory-fee risk,
   storage cost. Cross-check against the open Anabtawi→Habib proforma quantities. The 850g is at
   1 unit — quantify stock-out risk and lost sales. Sweets are perishable: flag freshness/excess.
4. **Listing content & conversion** — `amazon_products_by_child_asin`: title, 5 bullets,
   description, image URL, ranks. Score against the `listing-audit` rubric. Use the rewritten
   titles/bullets already in `_titles_bullets_rewrite_2026-06-01.md` as the baseline; refine.
   Quantify the conversion gap vs the 4.94% portfolio benchmark and the $ upside of closing it.
5. **Live page + competitors** — use Chrome on `amazon.ca/dp/{ASIN}` to confirm what DataDoe can't:
   A+ presence & modules, full image gallery count, review count/rating, recent review themes,
   coupon/deal state. Use Tavily/Chrome to pull the **top 2–3 competing listings** per head keyword
   ("baklava gift box", "barazek cookies", "assorted arabic sweets") and benchmark price-per-100g,
   image count, and review counts. (If Tavily is unavailable, use Chrome search.)
6. **Variation & duplicate structure** — SKUs 1 and 3 each have a near-duplicate ASIN
   (FX-M8MA 180g, 9Z-KUHZ 400g). Recommend which is canonical and how to fold them + their siblings
   into the in-progress parent listings (several "Incomplete" parents already exist).
7. **Reviews & social proof — TOP PRIORITY, do this first.** Via Chrome, pull EVERY review for each
   of the 5 ASINs (known: 400g = 3.3★, 850g = 4.1★; get exact count + rating for all five). Read the
   1–3★ reviews verbatim and **root-cause** them into categories: product quality/taste, freshness/
   expiry/stale, transit damage/melting/broken, packaging, portion/value vs price, wrong item, late
   delivery. Quantify each category (% of negatives) and tie to data where possible (e.g. aged FBA
   inventory → freshness complaints; high COGS+low price → value complaints). Output: a ranked
   root-cause table per SKU + the single highest-leverage fix. Then recommend Vine, a review-request
   plan, and which negatives are listing-fixable (set expectations on size/contents) vs
   product/supply-fixable. **Flag any food-safety or "made me sick"/mold/expired language immediately**
   — that escalates to the account's open restricted-product/food-safety risk, not just conversion.
8. **Compliance** — allergens (tree nuts/sesame), best-before, country of origin (Jordan), no health
   claims. Note any link to the 3 open restricted-product policy violations on the account.

## Data rules
- Today is the reference date. Default windows: trailing-30, trailing-90; pull yesterday/t7 from
  `amazon_order_items_with_cogs` where sales/traffic data lags. Respect the 2500-row cap (aggregate).
- Cache every export to `data/{table}_{from}_{to}.csv`. State the source + window behind every number.
- Quantify before/after for every recommendation (current value → proposed value → expected effect).
- Rank findings by dollars.

## Deliverables
- One deep-dive per SKU: `deliverables/sku-deep-dives/{ASIN}_{today}.md` — sections for each of the
  8 dimensions above, a scorecard, a prioritized action list (with $ impact and effort), and the
  exact proposed title/bullets/price/restock qty.
- One combined exec summary: `deliverables/sku-deep-dives/_top5_summary_{today}.md` — the 5 SKUs
  ranked by total opportunity ($ from price fixes + conversion lift + stock-out avoidance), with the
  single highest-value action per SKU and a consolidated restock + reprice table.
- Append durable findings to `brain/raw/`.

## Freshness / FBA rotation (the confirmed review driver)
The negative reviews are **confirmed as freshness / near-expiry**. (Note: quantities are deliberate —
Rami also sells these wholesale, so this is NOT about trimming purchase orders.) The problem is that
**near-expiry units reached Amazon customers** via FBA. For each SKU, audit the FBA freshness chain:
current FBA inventory age buckets and aged/excess units (`amazon_fba_inventory_health`), sell-through
vs the product's shelf life on the *FBA channel only*, and how long stock dwells before selling.
Recommend: (a) FIFO lot rotation and sending only fresh lots to FBA (hold longer-dated stock for
wholesale), (b) removal/markdown of any FBA units already aging *before* they ship stale, (c) smaller,
more frequent FBA replenishments so Amazon stock turns inside shelf life, and (d) best-before/packed-on
dating + a freshness guarantee on the listings. Ask Rami for the actual shelf life per product line if
not on file. This is the highest-leverage fix for the ratings — content/price work is secondary to it.

## Guardrails
**Recommendations only — never edit a live listing, price, bid, budget, or place a PO.** Everything
that would change the account is a reviewed artifact in `deliverables/` awaiting Rami's approval.
Be conservative on any health claim and anything implying the product is for children. Checkpoint
progress to `brain/raw/` so a long run can resume. Pause for Rami's review at the end.
