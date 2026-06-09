# Top-5 Deep-Dive — Durable Findings (2026-06-02)

Deep 360° audit of the 5 profit-core SKUs. Deliverables: `deliverables/sku-deep-dives/{ASIN}_2026-06-02.md` + `_top5_summary_2026-06-02.md`. Data cached in `data/` (profit t30, ads t90, fba_inventory_health, order_items geo).

## Freshness root cause is visible in inventory-age data (confirms Rami)
- **Oldest FBA stock = the money losers.** FX-M8MA (B0FTSM2HSJ) holds 8 units aged **181–270 days**; Classic Assorted 250g (B0FY6PBYZS) holds 17 units aged **91–180 days** with ~0 t30 turn (excess flagged, ~$331 Amazon cost-savings est.). These are exactly the listings losing money / idle.
- **Canonical HERO 180g (B0FXX46ST8) = the model:** 100% stock in 0–30d bucket, sell-through 1.81, 9 units shipped t7 → turns inside shelf life. Copy this rotation everywhere.
- Fix is structural/operational, not copy: retire duplicates, consolidate demand onto fresh-rotating canonicals, clear aged 250g lot, send smaller/fresher FBA lots, add best-before dating + freshness guarantee.

## Parent families now EXIST (changed since 2026-06-01 audit which said all standalone)
- **B0GKGQ15SQ** = canonical baklava: 180g B0FXX46ST8 + 400g B0FXX3JVR5. KEEP.
- **B0GKH8YNXP** = the duplicates: 180g B0FTSM2HSJ (FX-M8MA) + 400g B0FTSMTDGP (9Z-KUHZ). RETIRE/REDIRECT.
- **B0FY6NTZ5X** = Classic Assorted: 250g B0FY6PBYZS + 850g B0FY6N6TRH. Clean family.
- Barazek 400g (B0FTM6Y263) still standalone — build a 250g+400g barazek family.

## Money headlines
- **FX-M8MA (B0FTSM2HSJ) bleeds:** t30 **−$93.85** (−18.5%), ACOS 43%, TACOS 18%, ~$333 enabled ad spend over t90. Switch off its ads + retire = biggest single cleanup. Duplicate of the HERO 180g.
- **850g (B0FY6N6TRH) underpriced under new PI cost:** new landed **$37.74** → per-unit margin drops 23.7%→**8.2%**. Need ~$72 for 25%; recommend reprice to ~$69.99. Also **1 unit in stock** (days_of_supply 4) — restock-now. Highest profit/unit + #1 t90 profit ($239).
- **400g B0FXX3JVR5 = best converter (5.80% > 4.94% bench), healthiest margin (29.9%/unit), but Rami says 3.3★** — rating is the cap. Vine = highest leverage. Its $59.99 duplicate 9Z-KUHZ loses money.
- **Barazek = strong margin (32.7%/unit, 41.8% t30) + biggest conversion gap among keepers (2.72%)** + low stock (8u, aging 61–90d). Restock ~15 by 2026-06-20; own the "barazek" keyword.
- **Assorted 250g = best realized margin but ~0 velocity + aging** → freshness liability; rotate/markdown/remove, do NOT restock.

## Ad quick wins
- Pause `SP - Phrase - stock out` on B0FXX46ST8 ($50, 0 orders).
- Two capped winners at $10/day with ACOS far below target: `PATA - Stock Out` (B0FXX3JVR5), `Low bids cookies` (B0FTM6Y263) → raise to ~$20/day.
- NOTE: ads-table ACOS uses `ad_sales_same_sku` only and overstates ACOS vs the blended profit-table ACOS/TACOS — cite the profit table as the blended truth.

## Compliance flags
- Duplicate listings' descriptions copy **"Holy Land Baklava"** brand text — IP/brand-mismatch risk; fix or retire.
- All 5 missing explicit tree-nut/sesame allergen line + best-before/origin — added in proposed bullets. Sesame = Canadian priority allergen.
- 3 open restricted-product violations still the top account risk; escalate any "made me sick/mold/expired" review language.

## Open / TODO
- **Get the updated proforma** for 180g/400g/250g landed costs (only 850g $37.74 supplied) to re-check floors.
- **Confirm real FBA lead time** and **per-product shelf life** (drives every ship-by date and the FBA-dwell freshness math).
- **Chrome pass** (browser not connected this run): exact review counts/★, 1–3★ verbatim root-cause, A+/gallery confirmation, competitor $/100g. See [[2026-06-01_top5-review-ratings]].
