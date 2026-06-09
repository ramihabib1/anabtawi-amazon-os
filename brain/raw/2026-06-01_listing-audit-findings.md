# Listing Audit — Durable Findings (2026-06-01)

Full content audit of all 25 active ASINs. Scores 35–50/100 (catalog-wide weakness; no listing scored Green-heavy).

## Catalog-wide patterns (reuse next audit)
- **All ASINs are standalone** (blank parent). No variation families exist anywhere. Biggest structural lever.
- **Duplicate pairs:** 180g baklava B0FXX46ST8 ↔ B0FTSM2HSJ; 400g baklava B0FTSMTDGP ↔ B0FXX3JVR5;
  250g barazek B0FXXM1CK8 ↔ B0FTSNBX57. Consolidate before investing in content.
- **Browse nodes wrong:** baklava → Sweet Rolls/Tarts/Snack Gifts; barazek → Digestive Cookies/Nut;
  cashew fingers → Indian Sweets.
- **Titles brand-first**, missing Halal/Kosher + size; **size attribute blank** on ~10 SKUs.
- **Bullets templated** across catalog (generic "luxury/premium", no Halal lead, no allergen line, weak Eid/Ramadan).
  B0FY6M2LHX bullets cite wrong pack sizes (180g/400g) on a 500g SKU — copy-paste error.

## Model listing (the internal gold standard)
- **B0FXXQHDHP** (Honey Nut Brittle 500g): keyword-rich title, "Halal & Kosher Certified" in title, brand story
  (Anabtawi family confectioner since 1983, Levant), CAPS bullet lead-ins. Converts ~12.1% vs portfolio ~3-5%.
  Use as the template for every rewrite. Brand fact to reuse: family-run since 1983, Levant, butter ghee + wheat
  flour + premium nuts, no artificial preservatives. Brittle SKU carries Halal+Kosher cert — confirm cert scope
  before adding Kosher to other SKUs.

## Money signal
- **B0FTSM2HSJ (FX-M8MA)** is a structural loser: $28 price, realized t90 margin **1.4%** on 666 sessions/34 units.
  It also duplicates B0FXX46ST8 (the HERO 180g baklava, margin 17.8%). Likely discontinue FX-M8MA, keep B0FXX46ST8.
- Conversion gap upside (lift to 4.94% benchmark) ≈ **$1,300/mo** concentrated in baklava + maamoul SKUs.

## Benchmark / config to update
- conversion_benchmark in state/targets.md should change 12 → ~5 (data-grounded P75 = 4.94%).
- Tier weights are NOT in targets.md — add explicit HERO/MAINTAIN/CUT weights if this ranking is to be reproducible.

## Open data gaps (need Chrome/Tavily pass)
- A+ module presence, gallery image count, review count/rating are not in DataDoe — scored Amber, not verified.
  A targeted Chrome pass on the top-5 $-impact ASINs would firm up the images/A+/reviews dimensions.
