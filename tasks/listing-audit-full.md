# Task: Full Listing Audit  (run on demand; re-run quarterly or after copy/competitor changes)

Act as catalog-auditor with the `listing-audit` framework (also load `datadoe-query`,
`anabtawi-context`). Audit every live listing and produce a fix plan per listing plus a rollup.

## Step 1 — Build the priority queue (one DataDoe pull)
Pull trailing-30 `amazon_sales_and_traffic_with_cogs` (sessions, units_session_percentage,
buybox_percentage) and `amazon_profit_by_sku_and_date` (price, margin, ad_spend) for all ASINs.
Rank ASINs by `sessions × max(0, conversion_benchmark − actual_conversion) × tier_weight`
(benchmark from state/targets.md). Note any Buy Box <95% or structural-loss SKU to force-flag.

## Step 2 — Audit each listing (work in batches of 5, highest priority first)
For each ASIN:
1. Pull listing content from DataDoe: `amazon_products_by_child_asin` (title, bullets 1-5,
   description, image url, brand, size, rank) + `amazon_listings_with_cogs` (price, status).
   Use `amazon_products_raw` (download to file) for full attributes + all images if needed.
2. Use Chrome ONLY for what DataDoe can't show: A+ visual modules, rendered image gallery,
   recent 1-3★ review themes. Then pull the top 2-3 competitors for the head keyword via Tavily.
3. Score all 10 rubric dimensions Green/Amber/Red with reasons; compute the 0–100 score.
4. Write `deliverables/listing-audits/{ASIN}_{YYYY-MM-DD}.md` from
   `deliverables/_templates/listing-fix-plan.md` — fill the snapshot, scorecard, prioritized
   fixes (with the EXACT proposed title text, the 7-image shot list, the A+ module stack, the
   reprice target), and the ordered path-to-perfect checklist.
5. Append a durable note to `brain/raw/`.

## Step 3 — Rollup
Write `deliverables/listing-audits/_rollup_{YYYY-MM-DD}.md`: a table of every ASIN with its
score, Buy Box, conversion vs benchmark, the single highest-impact fix, and priority rank;
then a "fix queue" — the top 10 fixes across the whole catalog ranked by expected $ impact.

## Guardrails
Recommendations only. Produce plans; do not edit live listings. Pause for approval before any
execution. Be conservative on health claims and anything implying the product targets children.

## After approval
Approved listing changes get logged to state/decisions.md; re-audit the changed ASIN in ~2–3
weeks to measure the conversion lift (the audit is a loop, not a one-off).