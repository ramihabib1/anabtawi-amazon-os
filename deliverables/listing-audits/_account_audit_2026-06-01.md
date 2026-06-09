# Account-Level Audit — ANABTAWI SWEETS CA — 2026-06-01

Marketplace amazon.ca · FBA · CAD. Recommendations only — nothing changed in the live account.
Sources: `amazon_seller_performance` (snapshot 2026-05-31) · `amazon_listings_with_cogs` (live) ·
`amazon_profit_by_sku_and_date` t90 · `amazon_sales_and_traffic_with_cogs` t30 · `amazon_products_by_child_asin`.

## 1. Account health — one screen
**Account Health Rating: GREAT (score 204).** No suspension/at-risk signals. The account is healthy;
the only blemish is policy-compliance (below).

| Metric (window) | Value | Status |
|---|---|---|
| Account Health Rating (6m) | 204 | 🟢 GREAT |
| Order Defect Rate — FBA (60d) | 0% | 🟢 GOOD |
| Order Defect Rate — FBM (60d) | 0% | 🟢 (no/again FBM volume) |
| Late Shipment Rate (30d) | 0% | 🟢 GOOD |
| On-time Delivery (30d) | 0 | n/a (FBA — Amazon-handled) |
| Valid Tracking Rate (30d) | 0 | n/a (FBA) |
| Pre-fulfillment Cancellation (7d) | 0% | 🟢 |
| Listing policy violations (6m) | 0 | 🟢 |
| Product authenticity / condition / safety complaints (6m) | 0 / 0 / 0 | 🟢 |
| IP complaints received / suspected (6m) | 0 / 0 | 🟢 |
| Food & product safety issues (6m) | 0 | 🟢 |
| Customer-review policy / other violations (6m) | 0 / 0 | 🟢 |
| **Restricted product policy violations (6m)** | **3** | 🔴 **investigate** |
| Document requests (6m) | 0 | 🟢 |

## 2. The one real flag — 3 restricted-product policy violations (6m)
This is the single account-health issue. Performance metrics (ODR, late shipment) are spotless, so the
risk here is **policy/compliance**, not fulfillment. For a Middle-Eastern food seller, restricted-product
flags typically come from: ingredient/health claims, expiry/best-before or labeling gaps, country-of-origin,
or a product listed in a restricted/incorrect category.

**Why it matters:** repeated restricted-product violations are the most common path from GREAT to
"at-risk"/deactivation for food sellers, even while ODR stays clean.

**Recommended (do this first):**
1. In Seller Central → **Account Health → Policy Compliance**, open the 3 violations and read the exact
   ASIN + reason for each. (Not exposed in the DataDoe feed — needs the console or a Chrome pass.)
2. Cross-check against the listing-audit compliance findings: no health/medical claims, full **allergen +
   ingredient + best-before + country-of-origin** on every food listing.
3. Acknowledge/appeal each in the console and capture the resolution in `state/decisions.md`.

## 3. Catalog-structural audit (account-wide)
From the full content audit of all 25 active ASINs (listing scores 35–50/100 — uniformly weak):

- **No variation families anywhere.** Every ASIN has a blank parent. Baklava (6 sizes), Maamoul (4 flavours),
  Barazek (3), Ghraybeh (2) and Fingers (2) should each be one parent-child family. Standalone listings
  fragment reviews and rank.
- **3 duplicate pairs cannibalizing:** 180g baklava (B0FXX46ST8 ↔ B0FTSM2HSJ), 400g baklava
  (B0FTSMTDGP ↔ B0FXX3JVR5), 250g barazek (B0FXXM1CK8 ↔ B0FTSNBX57). Pick canonicals, redirect the rest.
- **Wrong browse nodes:** baklava under Sweet Rolls / Tarts / Snack Gifts; barazek under Digestive Cookies / Nut;
  cashew fingers under Indian Sweets. Hurts organic discoverability.
- **Titles brand-first, no Halal/Kosher, size attribute blank on ~10 SKUs.** Bullets templated catalog-wide
  (generic "luxury", no Halal lead, no allergen line, weak Eid/Ramadan hook). One SKU (B0FY6M2LHX) has a
  30-char title ("Special Assorted Sweets (500g)") and bullets citing the wrong pack sizes.
  → Fixed copy for all 25 is in `_titles_bullets_rewrite_2026-06-01.md`.
- **Model to copy:** B0FXXQHDHP (Honey Nut Brittle) — keyword-first, "Halal & Kosher Certified" title,
  brand story since 1983 — converts ~12% vs the portfolio's ~3–5%.

## 4. Commercial health (context)
- Conversion benchmark reset to **4.94%** (portfolio P75); most ASINs sit below it.
- **Structural margin loser:** B0FTSM2HSJ (FX-M8MA) 180g baklava — $28 price, **1.4%** realized t90 margin on
  666 sessions; also duplicates the healthier B0FXX46ST8 (17.8%). Reprice ≥$23.59 or discontinue.
- Conversion-gap upside (lift to benchmark) ≈ **$1,300/mo** across the top-10.
- Buy Box is ~95–100% account-wide (no buy-box loss problem).

## 5. Ranked action list
1. **Investigate & clear the 3 restricted-product violations** (compliance — highest risk to the account).
2. **Resolve the 3 duplicate ASIN pairs** (pick canonicals) before investing in content.
3. **Publish the title + bullet rewrites** for all 25 (keyword-first, Halal, allergen, Eid/Ramadan).
4. **Reprice/triage B0FTSM2HSJ** structural loser.
5. **Build variation families + correct browse nodes & size/Halal attributes.**
6. **Enroll Vine + review automation** (review counts unknown — likely thin).
7. Update `state/targets.md`: conversion_benchmark 12 → ~5; add explicit tier weights.

## 6. Data gaps (not pulled this run)
- Restricted-violation detail, A+ presence, gallery image counts, review counts/ratings — need Seller Central
  or a Chrome pass.
- Returns/concessions, settlement fee detail, and FBA reimbursement reconciliation — separate sources, not in scope here.

_Generated by the listing-audit framework. No live account or listing edited; awaiting Rami's review._
