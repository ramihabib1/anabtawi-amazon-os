---
name: listing-audit
description: The full per-listing audit framework for Anabtawi — scores every element of a listing (title, bullets, A+, images, price, backend, reviews, variations, attributes, compliance) against a best-practice rubric, then produces a prioritized fix plan and a step-by-step path to a perfect listing. Use for any single-listing or full-catalog content audit. Pairs DataDoe demand signals with the live page (Chrome) and competitors (Tavily). Recommendations only — never edits the live listing.
---

# Listing Audit Framework

Load `datadoe-query` and `anabtawi-context` first. This skill produces, per ASIN, a scored
audit + a fix plan written from `deliverables/_templates/listing-fix-plan.md`.

## Inputs per listing
1. **Listing content (DataDoe — primary):** `amazon_products_by_child_asin` gives the real
   `product_name` (title), `product_bullet_point_1..5`, `product_description`, `product_image_url`,
   brand, size, category and best-selling rank. `amazon_listings_with_cogs` gives live price,
   `listing_status`, referral fee, and quantities. For full attributes + the complete image set,
   `amazon_products_raw` (JSON `attributes`, `images`) — download to file, don't dump into context.
   This is the source of truth for title/bullets/description/price/images — no scraping needed.
2. **Demand signal (DataDoe):** trailing-30 `amazon_sales_and_traffic_with_cogs`
   (`session`, `units_session_percentage` = conversion, `buybox_percentage`) and
   `amazon_profit_by_sku_and_date` (price, margin, ROI, ad spend) — tells you whether the
   listing converts and how much a fix is worth. (`amazon_seller_performance` for account-level
   policy/health flags.)
3. **Chrome (supporting only):** open `amazon.ca/dp/{ASIN}` ONLY for what the structured feed
   can't show — A+ visual modules, the rendered image gallery, and recent review themes.
4. **Competitors (Tavily + Chrome):** top 2–3 ranking listings for the head keyword
   (e.g. "baklava gift box", "maamoul cookies") to score relative to the best competitor.

## The rubric — 10 scored dimensions
Score each Green / Amber / Red with a one-line reason. "Perfect" = the STANDARD below.

**1. Title.** STANDARD: front-loads the head keyword, then brand + product + key attributes
(flavor, dietary, occasion) + size/weight, readable, within Amazon CA byte limit, no ALL-CAPS,
no promo/claims. CHECK: keyword order, length, whether size and dietary (Halal/Kosher) appear.
FAIL: vague "Gourmet Sweets" with no head keyword (e.g. FX-M8MA, 9Z-KUHZ titles bury what it is).
FIX: rewrite as `{Head keyword} – {Brand} {product}, {flavor/ingredients}, {dietary}, {occasion}, {size}`.

**2. Bullets (5).** STANDARD: each benefit-led and scannable; collectively cover taste/quality,
ingredients & sourcing, dietary & certifications (Halal/Kosher/no-preservatives), occasions &
gifting, and pack/size/freshness. Keyword-rich without stuffing. FAIL: feature-only, duplicated,
or missing dietary/gifting angles. FIX: one bullet per theme, lead with the benefit in CAPS lead-in.

**3. A+ / Description.** STANDARD: A+ Content present with brand story, a comparison chart across
your own SKUs, lifestyle/gifting module, ingredients/dietary module, and an FAQ; mobile-readable.
CHECK: is there A+ at all? how many modules? FAIL: plain-text description or no A+ (major
conversion gap). FIX: build the A+ module stack; if Brand Registry is active, also add a Brand Story.

**4. Images.** STANDARD (target 7+): compliant white-background hero with appetite appeal; an
ingredients/what's-inside infographic; a size/scale reference; a dietary-badge graphic
(Halal/Kosher/etc.); a cross-section or contents shot; a lifestyle/gifting shot; back-of-pack /
nutrition. Mobile-legible text. CHECK: count + what each communicates. FAIL: <5 images, no
infographic, no gifting shot. FIX: specify the exact missing shots to produce. (Images move
conversion most — fix here first.)

**5. Pricing & offer.** STANDARD: price clears the margin policy (30%→25%→20% floor), is
competitive on price-per-100g vs the competitor set, holds the Buy Box (≥95%), and uses a
coupon/deal where it lifts conversion without breaking the floor. CHECK against the profit table
(real margin) and competitor prices. FAIL: below-floor margin (e.g. FX-M8MA 180g at $23.99) or
uncompetitive $/100g. FIX: reprice to the floor or restructure cost; flag for the PPC/profit pass.

**6. Backend search terms.** STANDARD: search-term field full, no title duplication, includes
English + Arabic transliteration variants (Maamoul/Ma'amoul/معمول, Barazek/Barazeh, Ghraybeh/
Ghorayeba), occasions, and competitor-adjacent terms. CHECK: not directly visible — infer gaps
from the keywords competitors rank for (Tavily) that this listing ignores. FIX: list the missing
terms to add in Seller Central.

**7. Reviews & social proof.** STANDARD: rising review count, ≥4.3 stars, recent negatives
addressed, Q&A seeded, enrolled in Vine if eligible. CHECK: count, average, themes in recent
1–3 star reviews. FAIL: <15 reviews or unanswered negatives. FIX: Vine enrollment, review-request
automation, and fold negative themes back into the listing (and the product/inventory passes).

**8. Variation & catalog structure.** STANDARD: related sizes/flavors live under one parent-child
family so reviews and traffic concentrate; no duplicate/competing listings cannibalizing. CHECK:
is this ASIN a standalone that should be a child? are there two SKUs on one ASIN (e.g. Holy Land
Barazek HW-U9RL + KL-GDUL) or two ASINs for near-identical products? FIX: build the variation
family / consolidate duplicates / pick a canonical.

**9. Attributes, category & dimensions.** STANDARD: correct category & browse node, dietary
attributes set (Halal etc.), and ACCURATE package weight/dimensions — wrong dimensions inflate
FBA fees. CHECK the Product Details block. FAIL: missing dietary attributes, wrong size tier.
FIX: correct attributes; if dimensions are off, file for FBA fee re-measure.

**10. Compliance & food labeling.** STANDARD: ingredients + allergens listed, best-before/expiry
handling clear, country of origin, no disallowed health claims. CHECK copy + images for claims
risk. FAIL: health claims ("healthy", "cures") or missing allergens. FIX: remove risky claims,
add allergen/ingredient info. (Food category + minors-safe; be conservative on claims.)

## Listing score & prioritization
- **Listing score** = simple 0–100 from the 10 dimensions (Green 10 / Amber 5 / Red 0).
- **Which listings to fix first** = rank by
  `trailing-30 sessions × max(0, conversion_benchmark − actual_conversion) × tier_weight`.
  High traffic + big conversion gap + worth-fixing margin rises to the top. Always also flag any
  listing with Buy Box <95% or a structural-loss SKU regardless of score.
- **Which element to fix first within a listing** (conversion leverage order):
  main image → title → A+ → secondary images → bullets → price → backend terms.

## Output
For each ASIN, write `deliverables/listing-audits/{ASIN}_{date}.md` from
`deliverables/_templates/listing-fix-plan.md`. Then append a row to
`deliverables/listing-audits/_rollup_{date}.md` (score, top fix, priority rank). Save durable
findings to `brain/raw/`.

## Guardrails
Recommendations only — never edit the live listing. Title/A+/price changes are produced as a
plan and wait for approval; once an SP-API listings write-back exists, execution is a separate
approval-gated step logged to `state/decisions.md`. Be conservative on any health/medical claim
and on anything implying the product is for children.
