# Targets & Thresholds  (the single dial for the whole system)

Edit these and every agent retunes. All currency CAD.
Values below are data-grounded starting points (blended margin ~24-27%, TACOS ~4.8%).
Tune as the system runs.

> ENGINE: the hard ACOS/TACOS breach ceilings the money CLI enforces live in
> `engine/config/thresholds.toml` (the machine mirror). The tiered `target_acos_*`
> below drive the PPC skill's tier-aware *recommendations*; keep `tacos_ceiling` and the
> CLI's `acos_ceiling_pct`/`tacos_ceiling_pct` in sync. Money numbers come from the
> engine CLI, never prose math (see datadoe-query → "Money math").

## Advertising  (ACOS targets sit below margin so ads stay profitable)
- target_acos_hero: 35%       # defend rank, accept higher ACOS
- target_acos_maintain: 28%
- target_acos_cut: 18%        # or pause entirely
- tacos_ceiling: 15%          # flag SKUs above this (trips FX-M8MA at 18%)
- waste_flag_min_spend: 10    # trailing-14 spend with ~0 orders to flag (low volume = low bar)
- ppc_change_materiality: 15  # min projected weekly spend delta worth surfacing

## Inventory  (weeks of cover including inbound)
- min_weeks_cover_hero: 8
- min_weeks_cover_maintain: 6
- min_weeks_cover_cut: 3
- excess_flag_age_days: 180   # tightened from 270 — sweets are perishable, freshness risk first
- assumed_lead_time_weeks: 6  # TODO Rami: set your REAL number (air ~4, sea ~8-12). Drives every restock date.

## Profit
- min_roi_maintain: 40%       # trailing-90 below this -> review
- loser_flag: profit < 0 over trailing-30

## Listing
- min_buybox_pct: 95          # you're ~100% now; this catches a future drop
- conversion_benchmark: 12%   # PROVISIONAL. After the first sales_and_traffic pull, reset this
                              # to your portfolio top-quartile conversion so the audit flags
                              # laggards against your own winners, not a generic number.
