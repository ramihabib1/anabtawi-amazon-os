# Stop-the-Bleed premise was stale — verified live 2026-06-24

**Context:** Phase 8 (reversible-write apply spine) Plan 08-04 was set to pause the 4 dead SKUs
(FX-M8MA, 9Z-KUHZ, VH-ZTOC, ZK-4NDS) that the 2026-06-16 coverage-gap note said held ~43% of
ad spend (~$279/mo). Before executing the batch, I FIND-verified the live state (DataDoe Actions
access enabled by Rami 2026-06-24) and pulled current ad spend. **The premise no longer holds.**

## What the live data shows (ad-by-ASIN, 2026-06-10→06-24, source d0017e92fb)

- The **dedicated** dead-SKU campaigns are **already PAUSED**. FIND on B0FTSM2HSJ (FX-M8MA)
  returned 8 AIHELLO SP campaigns, **all `state:PAUSED`** since ~2026-02-26. FIND on
  B0FTSMTDGP and B0FTM5PBZW returned **no** ASIN-named SP campaigns.
- Residual dead-ASIN ad spend is **~$20.4 / 14d ≈ ~$44/mo = ~9.7% of current spend**
  (total ENABLED SP spend = $209.31/14d ≈ ~$449/mo), NOT 43% / ~$279/mo.
- The residual spend lives in **SHARED keyword campaigns** that also serve healthy SKUs:
  - `SP - Phrase - stock out` (id 30844736154957): $17.34 on dead B0FTSMTDGP (0 sales) — BUT
    the same campaign earns **$155.94 sales on $33.18 spend for healthy B0FXX46ST8 (18-116Z)**.
    Pausing the whole campaign would kill that profitable performer.
  - `{skw] Middle Eastern sweets` (72369111877919): $1.52 on FX-M8MA actually returned **$28 sales** — profitable, not waste.
  - `skw -Arabic sweets`, `skw - pistachio baklava`, `[SP] Mamoul exact`: cents of dead-ASIN spend each.

## Decision (2026-06-24): batch NOT executed

Running Plan 08-04's "pause the whole dead-SKU campaigns" against current reality would be
**destructive** — the residual dead-ASIN spend is inside shared campaigns serving healthy,
profitable SKUs. Pausing whole campaigns = collateral damage. Per CLAUDE.md hard rules (don't
act destructively; surface when the target contradicts the description), I stood the batch down.

## What's actually true / next-step options

- The dead-SKU bleed was **already ~95% eliminated** (dedicated campaigns paused months ago).
- The only genuine residual waste is **$17.34/14d (~$37/mo) on dead B0FTSMTDGP inside the shared
  `stock out` campaign**. The correct fix is a **product-ad-level pause** (`AMAZON_ADS_ADS_UPDATE`
  — set that ASIN's product ad to PAUSED), which is **out of Phase 8's scope** (not one of the 3
  org-enabled types: CAMPAIGNS_UPDATE / TARGETS_ADD / TARGETS_UPDATE). A whole-campaign pause or
  a keyword negative would both hit the healthy ASINs in the same campaign.
- The apply spine itself (Plans 01–03) is built, tested, green, and dry-run-validated live. Its
  first **real** write should land on a genuinely-wasteful, **non-shared** ENABLED campaign (TBD)
  rather than the now-stale dead-SKU list.

**Cached evidence:** `data/ads_dead_asins_spend_2026-06-10_2026-06-24.csv`,
`data/ads_stockout_campaign_30844736154957_2026-06-10_2026-06-24.csv`,
`data/ads_total_spend_2026-06-10_2026-06-24.csv`. See [[2026-06-16_ppc-coverage-gap]] (the now-stale source).
