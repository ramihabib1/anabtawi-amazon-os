# Task: Morning Briefing  (schedule: daily ~07:00 America/Toronto)

Act as the orchestrator. Fan out to all four specialists in parallel, then synthesize.

Pull (cache to data/):
- profit-analyst: amazon_profit_by_date for yesterday vs trailing-7 and trailing-28.
- ppc-manager: amazon_ads_performance_by_child_asin_and_date for trailing-7 vs prior-7.
- inventory-planner: latest amazon_fba_inventory_health snapshot.
- catalog-auditor: amazon_sales_and_traffic_with_cogs trailing-7 (buy-box %, conversion).

Apply thresholds from state/targets.md. Produce a ONE-SCREEN briefing:
1. Yesterday: sales, profit, ROI, TACOS — with deltas vs prior day and trailing-7 avg.
2. Anomalies, ranked by $ impact (sales drop, ACOS spike, low stock, buy-box loss, profit<0).
3. Top 3 actions for today, each with a one-line rationale and a link to a draft artifact
   in deliverables/ if action is warranted.

**Numbers come from the engine, not prose** (CLAUDE.md): any ACOS/TACOS/ROI/margin figure
is from the engine CLI (see datadoe-query → "Money math"), never eyeballed.

**Assign actions to the operator (the interactivity loop).** For each warranted action, write
an Action-Inbox item with the engine-computed numbers:
```
cd engine && uv run python scripts/inbox.py add --domain <ppc|profit|inventory|listing> \
  --agent <specialist> --title "…" --why "…" --impact <signed $CAD> --sku <SKU> \
  --current "…" --proposed "…" --evidence "<export id · the numbers>" \
  --operator-task "<the concrete thing Rami does>" [--artifact deliverables/…]
```
Then refresh the cockpit: `uv run python scripts/render_dashboard.py --tacos <answer.json>`
(opens at `deliverables/dashboard.html`). Do not re-add an item that already exists for the
same SKU+issue (check `inbox.py list`); update targets/notes instead.

Append the full briefing to state/daily/{YYYY-MM-DD}.md AND to brain/raw/daily/{YYYY-MM-DD}.md. Surface only the one-screen summary
in chat. Do NOT execute anything against the live account.
