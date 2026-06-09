# Top-5 Profit-Core Deep-Dive — Executive Summary

**ANABTAWI SWEETS CA · amazon.ca · CAD · 2026-06-02**
Deep 360° audit of the 5 profit-core SKUs (+ their 2 cannibalizing duplicates). Recommendations only — nothing in the live account was changed; every action below is an artifact awaiting Rami's approval.

**Data sources & windows:** `amazon_profit_by_sku_and_date` t30 (2026-05-03→06-02) & t90 (2026-03-03→06-01) · `amazon_ads_performance_by_child_asin_and_date` t90 · `amazon_fba_inventory_health` (2026-06-02 snapshot) · `amazon_sales_and_traffic_with_cogs` t30 · `amazon_products_by_child_asin` · `amazon_listings_with_cogs`. All cached in `data/`.
**Not done this run:** live review verbatims, exact review counts/★, A+/gallery confirmation, and competitor $/100g — **Chrome was not connected** (per your call, flagged for a fast follow-up pass).

---

## The one-paragraph story
The freshness/near-expiry root cause you confirmed is **visible in the inventory-age data**, and it maps almost perfectly onto the money problems. The two SKUs reaching customers with the **oldest FBA stock are the two cannibalizing duplicates** (FX-M8MA 180g = 8 units aged 181–270 days; and the slow 9Z-KUHZ 400g) **plus the slow Classic Assorted 250g** (17 units aged 91–180 days, ~zero turn) — and those are exactly the listings losing money or sitting idle. Meanwhile the **canonical HERO 180g (B0FXX46ST8) holds 100% fresh 0–30-day stock and turns it in under two weeks** — the model rotation. So the highest-leverage fix is structural and operational, not copy: **retire the two duplicates and consolidate their demand onto the fresh-rotating canonical ASINs, clear the aged 250g lot, send only fresh lots in smaller/more-frequent FBA shipments, and add best-before dating + a freshness guarantee.** Two money items ride alongside: the **850g is one unit from stock-out and, under the new proforma cost ($37.74), earns only 8% margin — restock fresh now and reprice to ~$70**; and the **FX-M8MA duplicate is bleeding ~$94/mo on ads** that should simply be switched off.

---

## 5 SKUs ranked by total opportunity
"Opportunity" = price-fix margin + conversion-lift + stock-out avoidance + loss/ waste elimination + one-time cost savings. Monthly unless noted.

| Rank | SKU (ASIN) | Tier | t90 profit | Total opportunity | Single highest-value action |
|------|-----------|------|-----------|-------------------|------------------------------|
| 1 | **Baklava 180g** B0FXX46ST8 | HERO | $212 | **~$314/mo** + duplicate cleanup | Content/image rewrite (~$240/mo conv) + pause $50 ad waste; **retire duplicate FX-M8MA** to end its ~$94/mo bleed and redirect its 666 sessions here |
| 2 | **Baklava 850g** B0FY6N6TRH | HERO | $239 (#1/unit) | **~$156/mo** + saves an 8%-margin sale | **Restock fresh now (1 unit left)** + reprice $55.99→~$69.99 for the new $37.74 cost |
| 3 | **Baklava 400g** B0FXX3JVR5 | HERO | $188 | review ceiling + ~$33–66/mo ads + duplicate cleanup | **Vine/review recovery** (best converter at 5.8% held down by 3.3★) + raise the capped winning campaign; **retire duplicate 9Z-KUHZ** |
| 4 | **Barazek 400g** B0FTM6Y263 | HERO | $147 | **~$119/mo** conv + restock protection | Restock ~15 fresh by 2026-06-20, then own the "barazek" keyword (rewrite) |
| 5 | **Assorted 250g** B0FY6PBYZS | HERO | $141 | **~$331 one-time** + freshness-risk removal | **Rotate/markdown or remove the aged 91–180d lot**; do NOT restock |

> Two duplicates are **retire/redirect**, not keep: **B0FTSM2HSJ (FX-M8MA, 180g)** — t30 **−$94**, ACOS 43%, 8 units aged 181–270d; and **B0FTSMTDGP (9Z-KUHZ, 400g, $59.99)** — t30 **−$24**, 24 slow units. Both cannibalize a better canonical twin.

---

## Consolidated REPRICE table (awaiting approval)
Margin policy floor 30%→25%→20%. "New PI cost" supplied only for the 850g ($37.74); **others flagged — please share the updated proforma so the 180g/400g/250g floors can be re-checked.**

| ASIN | SKU | Current $ | Landed COGS | Per-unit margin now | Proposed $ | Why |
|------|-----|----------|-------------|---------------------|-----------|-----|
| B0FY6N6TRH | 850g | 55.99 | **37.74 (new)** | **8.2%** | **69.99** (72 = full 25%) | New cost guts margin; converts w/ ~no ads → price-tolerant |
| B0FXX46ST8 | 180g | 28.00 | 13.63 | 21.7% | **29.49** | Below 25% floor; HERO, 473 sessions |
| B0FY6PBYZS | 250g | 25.99 | 11.07 | 23.3% | **26.99** | Clears 25% + buffers the (likely) new cost |
| B0FXX3JVR5 | 400g | 55.99 | 26.77 | 29.9% | **hold** | Already >25%; recheck if new cost rises |
| B0FTM6Y263 | Barazek 400g | 32.99 | 11.76 | 32.7% | **hold** | Clears 30%; invest in conv/restock instead |
| B0FTSM2HSJ | 180g DUP | 28.00 | 13.49 | (−18.5% realized) | **retire/redirect** | Don't reprice — fold into B0FXX46ST8 |
| B0FTSMTDGP | 400g DUP | 59.99 | 26.63 | (−10.5% realized) | **retire/redirect** | Don't reprice — fold into B0FXX3JVR5 |

## Consolidated RESTOCK / freshness table (awaiting approval)
Send **fresh lots only**; hold longer-dated stock for the wholesale channel. Respect the 6-week lead time in `state/targets.md` (please confirm your real lead time — it drives every ship-by date).

| ASIN | SKU | Available | Age profile | Velocity | Action | Qty / timing |
|------|-----|----------|-------------|----------|--------|--------------|
| B0FY6N6TRH | 850g | **1** | 2u @ 61–90d | ~1.3/wk | **RESTOCK NOW (fresh)** | ~12 units, ship immediately (Amazon rec. 9; date already past) |
| B0FTM6Y263 | Barazek | **8** | all 61–90d | ~1.5/wk | **Restock fresh soon** | ~15 units to land by ~2026-06-20 (order now) |
| B0FXX46ST8 | 180g | 24 | all 0–30d (model) | ~4/wk | Plan fresh replenishment | ~24 units to land mid-July (place ~mid-June) |
| B0FXX3JVR5 | 400g | 24 | 23 fresh + **1 @ 91–180d** | ~2/wk | Remove the 1 aged unit; no restock yet | remove 1; reorder ~Aug |
| B0FY6PBYZS | 250g | 14 | **17u @ 91–180d, excess 14, ~0 turn** | ~0/wk | **NO restock; rotate/markdown or remove** | up to ~$331 cost savings (Amazon est.) |
| B0FTSM2HSJ | 180g DUP | 3–4 | **8u @ 181–270d** | declining | No fresh stock; sell/remove + redirect | retire listing |
| B0FTSMTDGP | 400g DUP | 24 | all 0–30d but ~0.8 sell-through | slow | No restock; redirect | retire listing |

## Advertising — quick wins (detail in each deep-dive)
- **Pause** `SP - Phrase - stock out` on B0FXX46ST8 — $50 spend, 0 orders.
- **Switch off all FX-M8MA (B0FTSM2HSJ) campaigns** — ~$333 enabled spend driving a t30 **−$94** loss at 43% ACOS. Biggest single ad cleanup.
- **Raise budgets on two capped winners** (both at $10/day, ACOS far below target): `PATA - Stock Out` on B0FXX3JVR5 and `Low bids cookies` on B0FTM6Y263 → ~+$180–320/mo incremental sales at target ACOS. Do the Barazek raise *after* restock.

## Catalog structure — the durable lever
Two parent families now exist (good): **B0GKGQ15SQ** (canonical 180g + 400g) and **B0GKH8YNXP** (the two duplicates). **Make B0GKGQ15SQ the surviving baklava family, retire the B0GKH8YNXP duplicates, and pool reviews onto the canonical, fresh-rotating ASINs.** The "Classic Assorted" family (B0FY6NTZ5X: 250g + 850g) is clean. Fix wrong browse nodes (400g filed under "Tarts"; several under "Sweet Rolls/Snack Gifts") and set Halal + size attributes.

## Compliance / risk
- The duplicate listings' descriptions copy text from **"Holy Land Baklava"** (a different brand) — fix or retire; brand-mismatch + possible IP exposure.
- Every SKU is missing an explicit **tree-nut/sesame allergen line** and best-before/country-of-origin — added in each proposed bullet set (sesame is a Canadian priority allergen).
- The account's **3 open restricted-product policy violations** remain the top account risk. Any 1–3★ review using "made me sick / mold / expired" language must be escalated there immediately — verify in the pending Chrome pass.

## What's still open (the Chrome follow-up)
Connect Chrome and I'll, per ASIN: pull exact review count + ★, read every 1–3★ verbatim and root-cause it (freshness / taste / transit damage / packaging / value / wrong item), confirm A+ and gallery counts, capture coupon state, and benchmark the top-3 competitors' price-per-100g and image counts for each head keyword. That firms up dimensions 5 and 7 and the conversion-upside numbers.

---
_Per-SKU detail: `deliverables/sku-deep-dives/{ASIN}_2026-06-02.md`. No live listing, price, bid, budget, or PO was changed. Awaiting Rami's review._
