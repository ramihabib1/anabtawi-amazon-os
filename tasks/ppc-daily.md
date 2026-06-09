# Task: PPC Daily Check  (schedule: daily, midday)

Act as ppc-manager (ppc-analysis skill). Trailing-14 vs prior-14:
- Flag spend with zero/near-zero ad_orders (waste).
- Flag campaigns/ASINs above target_acos for 7+ days.
- Flag budget-capped winners below target ACOS (raise candidates).
Compute every per-SKU ACOS/TACOS/ROI + breach via the engine CLI (datadoe-query →
"Money math") — never prose. If any flag clears the materiality threshold in
state/targets.md:
1. Write/refresh `deliverables/ppc-changes_{date}.xlsx`.
2. Assign each as an Action-Inbox item (the operator's queue) with the engine numbers:
   `cd engine && uv run python scripts/inbox.py add --domain ppc --agent ppc-manager …`
   (`--impact` = signed $CAD so it ranks; `--evidence` = export id + the ratios;
   `--operator-task` = the exact Campaign Manager step). Skip SKUs already in `inbox.py list`.
3. Refresh the cockpit: `uv run python scripts/render_dashboard.py --tacos <answer.json>`.
Post a 3-line summary. Otherwise report "no action". Never touch the live account.
