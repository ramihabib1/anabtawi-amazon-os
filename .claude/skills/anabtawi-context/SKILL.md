---
name: anabtawi-context
description: Brand, catalog, and commercial context for ANABTAWI SWEETS CA on amazon.ca. Use for any Anabtawi-specific question so analysis is grounded in the real catalog, SKU tiers, COGS, and seasonality. Reference content — load it whenever interpreting results for this account.
---

# Anabtawi Sweets — Brand & Catalog Context

- **Marketplace:** amazon.ca (Canada), CAD. FBA + AWD.
- **Category:** Middle Eastern food / sweets (shelf-stable). Watch expiry/lot-sensitivity:
  aged FBA inventory isn't just a fee problem here, it's a freshness problem.

## SKU tiers
Maintain the live SKU list below. Tier drives how aggressively each SKU is defended in PPC
and restock. (Fill from the latest portfolio scoring; update monthly via `pnl-monthly`.)

| Tier | Meaning | PPC posture | Restock posture |
|------|---------|-------------|-----------------|
| HERO | Top profit + velocity | Defend rank, accept higher ACOS | Never stock out |
| MAINTAIN | Steady contributors | Hold target ACOS | Standard cover |
| CUT | Low velocity / margin | Minimal/no spend | Sell through, don't reorder |

> Tiers below refreshed **2026-06-12** from engine t90 (export c30ca944) + the 06-11 full
> listing audit. Still **inferred** (pending Rami sign-off); `pnl-monthly` re-tiers monthly.
> COGS = `cogs_total_value` from `amazon_listings_with_cogs` (export b18aadfd, landed).

> **Source of truth (D-05):** the margin gate does NOT read this prose table. Its machine
> source of truth is `engine/config/sku_catalog.toml` — edit tier/COGS/the SKU set THERE
> and mirror here, never the reverse, so the two can't silently diverge. That TOML
> currently carries only the SKUs with a **reviewed, committed landed COGS** (16 today);
> any SKU shown below but absent from the TOML **refuses on funding**
> (`sku_not_in_catalog`) until its real COGS is committed — it is never given a guessed
> cost. This prose table stays the fuller human reference.

| SKU | ASIN | Product | Tier | COGS (CAD) | Note |
|-----|------|---------|------|-----------|------|
| T8-2W2X-INOK | B0FXX3JVR5 | Baklava 400g (canonical) | HERO | 26.77 | apply bullets; reprice ≥49.99 |
| 18-116Z-1R77 | B0FXX46ST8 | Baklava 180g (canonical) | HERO | 13.63 | reprice ≥29.49; TACOS drift |
| Y4-Y8EE-VEOD | B0FTM6Y263 | Barazek 400g | HERO | 11.76 | ACOS 107.5 t30 — bid cut |
| 09-AJOP-CS83 | B0FY6PBYZS | Assorted 250g | HERO | 11.07 | best ROI (105, engine) — fund |
| GG-0DC1-SKHG | B0FTSQ8M46 | HL Maamoul Date 350g | HERO | 15.56 | restock first (1 unit!) |
| EU-Z87B-ZRBZ | B0FY6N6TRH | Baklava 850g | HERO | 29.06 | INACTIVE 0 FBA — reactivate |
| C5-TXQU-Y67R | B0FTM92W43 | Maamoul Walnut 550g | MAINTAIN | 20.07 | node fix open |
| AN-9938-NXOT | B0FTM1JV7N | Maamoul Date 550g | MAINTAIN | 13.49 | needs 7-image set |
| KL-GDUL-HEA1 | B0FTSNBX57 | HL Barazek 250g | MAINTAIN | 10.86 | family canonical |
| W3-UQRU-PGRR | B0FXXN7HGB | B&W Baklava 350g | MAINTAIN | 11.07 | converts 5.3% on no spend |
| YE-HCDW-4UYW | B0GKWQJNYR | Assorted 800g | MAINTAIN | 38.27 | node fix |
| KP-MEL9-XYGW | B0FXXQHDHP | Honey Nut Brittle 500g | MAINTAIN | 7.96 | allergen + PPC cut first |
| H8-PWJ0-3B1Y | B0FY6SX9RP | Special Assorted 250g | MAINTAIN | 12.45 | 103 sess/0 conv — rebuild |
| E3-DSPC-O2UN | B0FY6MFJV5 | Baklava 500g | MAINTAIN | 20.06 | Buy Box 93% check |
| 1S-ITGB-CZFR | B0FY6M2LHX | Special Assorted 500g | CUT* | 21.79 | *promote if title fix converts |
| 26-JITG-E4FU | B0FXXM1CK8 | Barazek 250g (dup) | CUT | 5.53 | retire into KL-GDUL family |
| BU-6GOS-GW5Q | B0FXX2R3BD | HL Ghraybeh 250g | CUT | 8.10 | node fix; no spend |
| O3-V1B9-CH1H | B0FTMBSVDN | Ghraybeh Special 375g | CUT | 9.48 | rebuilt; discoverability |
| RL-KMFR-SEGS | B0FT3PHRF6 | Cashew Fingers 400g | CUT (fold) | 8.99 | → Premium-Baklava parent |
| 3I-SHTN-9CKQ | B0FT3HN2XV | Almond Fingers 375g | CUT (fold) | 7.61 | freshness check 16 units |
| 0C-45D7-6JUB | B0FXX2QVF8 | Assorted Cookies 725g | CUT (fold) | 34.59 | → gift-box parent anchor |
| ASW-H50 | B0FSL5KQ9Q | Honey Baklava 500g | CUT (exit) | 39.05 | unit economics (ROI −100) |
| FX-M8MA-MMSA | B0FTSM2HSJ | Baklava 180g DUP | EXIT | 13.49 | Inactive; **pause ads** |
| 9Z-KUHZ-FU2I | B0FTSMTDGP | Baklava 400g DUP | EXIT | 26.63 | stop ads, clear 24 units |
| VH-ZTOC-GW1Q | B0FTM5PBZW | Maamoul Pistachio 550g | EXIT | 27.60 | sell through 5 units |
| ZK-4NDS-MNA9 / OA-26MX-IHV0 / 5G-ZW6Q-WOZG / 9J-ASSK-BVKC / FO-SE3J-T74M | — | inactive remnants | — | — | fold-or-delist in variation project |

## Commercial notes
- COGS in DataDoe profit tables reflects landed cost if maintained in DataDoe; if a SKU's
  COGS looks like 0/null, treat its profit as unreliable and flag it.
- Seasonality: note Ramadan/Eid and holiday gifting spikes — pull forward restock and budget.
- Family/operating context: sales & marketing and finance are handled by others; this
  workspace owns the technical + analytical operation of the marketplace.
