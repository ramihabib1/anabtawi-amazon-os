# Task: PPC Daily Check  (schedule: daily, midday)

Act as ppc-manager (ppc-analysis skill). Trailing-14 vs prior-14:
- Flag spend with zero/near-zero ad_orders (waste).
- Flag campaigns/ASINs above target_acos for 7+ days.
- Flag budget-capped winners below target ACOS (raise candidates).
If any flag clears the materiality threshold in state/targets.md, write/refresh
deliverables/ppc-changes_{date}.xlsx and post a 3-line summary. Otherwise report "no action".
