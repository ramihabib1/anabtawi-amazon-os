# 2026-06-24 — Phase 9 daily ranked queue built; first live write deferred (live findings)

Phase 9 (daily ranked queue + explicit-approval spend-up) is **code-complete and
pytest-green**. The one human-gated step — the first real mutating spend-up — was deferred to
a focused session after opening the live path surfaced two material changes.

## What shipped (engine + skill)
- `engine/src/habibos/harvest.py` — pure predicates: `is_matured` (SP≥7d, SB/SD≥14d),
  `is_act_now`, `judge_later_blocked` (immature-window refusal), `consolidation_blocked`
  (bid-up on a term in >1 ENABLED campaign → block to lowest-ACOS owner), `graduates`.
- `engine/scripts/queue_run.py` — daily-queue CLI: `render` (rank → tag → render the
  dollar-ranked table; run the read-only gate chain on spend-ups; auto-apply auto-class
  reversibles via the Phase-8 spine) and `apply --approve` (fire ONE gate-passed spend-up).
- Wave 1–3 also landed the dials (cap 50% / cover 42d / conversion 12%), `cover_gate.py`,
  `rank_queue.py` + `QueueRow`, and `queue.py`. Full engine suite: **83 passed, 5 skipped**.

## Live findings (the reason the first write was deferred)
1. **DataDoe write path is LIVE.** `AMAZON_ADS_CAMPAIGNS_FIND` returned in <1s;
   `actions_list` shows **5 actions ever, all FINDs — zero mutating writes have ever landed**.
   16 ENABLED Sponsored Products campaigns, almost all **$10/day** (one $5/day), most
   `SALES_DOWN_ONLY` (defensive). `MAINT-MOF-B&W-Baklava-Exact` (the W3-UQRU winner) already
   exists at $10/day since 2026-06-17.
2. **agentcentral is EXPIRED** (`trial_expired`; Seller Central + Amazon Ads both `missing`
   for CA). So the live-read tools the plan named (`get_days_of_cover`, `get_sales_velocity`,
   `get_fba_inventory`, `get_sales_and_traffic`) are **down** — reads must come from **DataDoe
   exports** (FBA Inventory Health `44fc5ba0ce`, Sales & Traffic `401ffcd7e5`, Profit by SKU
   `57a0cb319c`). **Action for Rami:** renew agentcentral if those live tools are wanted, else
   stay on DataDoe exports.
3. **The 2026-06-16 "funded winners" are mostly Phase-10 new campaigns** (`CAMPAIGNS_ADD`,
   held; several already built). A clean Phase-9 spend-up is a `budget_up`/`bid_up` on an
   existing enabled winner — which needs **current** matured ACOS + **current** days-of-cover.
   The only cached cover file is `top5, 2026-06-02` (~3 weeks stale) — unsafe to gate a first
   real $ write (GG-0DC1's whole point is the sub-cover refusal).

## To run the live first-write (focused session)
Fresh **FBA Inventory Health** (cover) + matured **ad-campaign performance** export → engine
gate over the 16 enabled campaigns → `queue_run.py render` the live table (confirm a sub-cover
SKU renders REFUSED) → dryRun the best gate-passed `budget_up` → show Rami the exact raise →
`queue_run.py apply --approve` → poll COMPLETED + `*_FIND` echo → log to `decisions.md` +
brain. Also demo an over-ceiling raise refused-not-clamped. **Still 0 real writes on the
account.**
