---
name: ppc-analysis
description: Playbook for analyzing and optimizing Anabtawi's Amazon advertising. Use for any question about ACOS, TACOS, ad spend, wasted spend, bids, budgets, or campaign/ad-group/ASIN ad performance. Produces a reviewable bid & budget change sheet — it never changes the live account.
---

# PPC Analysis & Optimization

Load `datadoe-query` and `anabtawi-context` first. Read targets from `state/targets.md`.

> **NUMBERS COME FROM THE ENGINE, NOT PROSE (CLAUDE.md hard rule 4).** Every per-SKU
> ACOS/TACOS/ROI and breach flag is produced by the tested CLI — see `datadoe-query` →
> "Money math": pull `groupBy sku + *_sum`, then `cd engine && uv run python
> scripts/answer_tacos.py …`. You **render and interpret** its typed JSON (breach / no
> data / no sales / refusal); you do **not** compute or eyeball a ratio in chat. Ad-console
> figures may be cited for cross-check, but the system-of-record number is the CLI's.

## Inputs
- Per-ASIN efficiency: `amazon_ads_performance_by_child_asin_and_date` (d0017e92fb).
- Ad group / placement / SB: `7c1ba29e52`, `3d720918e6`, `0dd6cbf08c`.
- Blended truth: `amazon_profit_by_sku_and_date` (57a0cb319c) for `acos, tacos, ad_spend,
  ad_sales, profit` per SKU — always cross-check ad-console ACOS against profit-table TACOS.

## What to find (rank by $ impact)
1. **Wasted spend** — clicks/spend with zero or near-zero `ad_orders` over trailing 14–28d.
   Candidates to pause or cut bids. (Negative-keyword mining needs the search-term source —
   flag if not yet wired in.)
2. **ACOS breaches** — campaigns/ASINs above `target_acos` (per tier) for ≥7d. Recommend a
   bid reduction sized to the overspend.
3. **Budget-capped winners** — campaigns at/near `ad_campaign_budget_amount` with ACOS below
   target and rising sales. Recommend a budget raise.
4. **TACOS drift** — SKUs where `tacos` is climbing while organic share falls: the ads are
   buying sales that used to be organic. Flag for structural review.
5. **Tier mismatch** — HERO SKUs underfunded, CUT SKUs still spending.

## Output (to `deliverables/ppc-changes_{date}.xlsx`)
One row per recommended change: SKU/ASIN · campaign · metric (bid/budget/status) ·
current → proposed · trailing ACOS/TACOS · expected effect · confidence. Summary tab with
total projected spend delta and the rationale. **Stop there — wait for approval.**

## Acting (Phase 2, optional)
If a SP-API (or Amazon Ads API) write-back MCP is connected, execution is a *separate,
approval-gated* step: dry-run the diff, get explicit "apply", then write, then append each
applied change to `state/decisions.md`.

## Daily ranked queue (the standing operating rhythm)

On-open / on-demand (no cron). The queue is the one screen that turns the day's PPC signals
into a dollar-ranked, class-tagged action list — and it is the only path that fires a real
spend change.

**1. Pull the live reads (the agent does the MCP I/O — the engine opens no socket, D-04).**
Download to local JSON the four signals the gate chain consumes:
`get_sales_velocity` · `get_days_of_cover` · `get_fba_inventory` · `get_sales_and_traffic`
(when the agentcentral connection is live). When it is not, pull the DataDoe equivalents —
**FBA Inventory Health** (`44fc5ba0ce`, days-of-cover) · **Sales & Traffic** (`401ffcd7e5`,
conversion) · **Profit by SKU & Date** (`57a0cb319c`, the margin-gate components) — and the
candidate set (the proposed bid/budget/harvest moves with their $ components).

**2. Render the dollar-ranked table.** From the repo root:
```
cd engine && uv run python scripts/queue_run.py render \
  --candidates <candidates.json> --cover <cover_map.json> [--term-acos <map.json>] \
  --artifact <profit_export.csv>
```
It prints one table — `rank | SKU | entity | action | current → proposed | expected $/wk |
provenance | class` — dollar-ranked, no-$-estimate rows last (D-07). **The numbers come from
the engine, never prose** (same discipline as the banner above): `rank_queue` ranks,
`answer_tacos`/`gate` own the money, `queue` tags the class. You render and interpret.

**3. Reversibility classes drive autonomy (QUEUE-02).**
- **`auto`** (standing approval — pause / exact-match negative / bid_down / contested-term
  pause): render mode **auto-applies** these through the Phase-8 spine after dryRun and shows
  them already-actioned (autonomy ≠ silence). The magnitude cap (live at 50%) refuses an
  over-cap reversible — never clamps.
- **`needs-approval`** (spend-up: bid_up / budget_up / harvest — and phrase/broad negatives):
  these are **never** auto-applied. They wait for ONE explicit batch approval:
  ```
  cd engine && uv run python scripts/queue_run.py apply --approve \
    --sku … --action-type budget_up --delta-spend … --entity-type campaigns --entity-id … \
    --dryrun-resp … --apply-resp … --status-resp … --find-echo …
  ```
  Without `--approve` the CLI refuses any needs-approval row (D-06).

**4. Every spend-up clears the full gate chain before it is actionable** — margin gate
(per-SKU margin-derived TACOS ceiling) → cover/conversion gate (≥42-day cover, ≥12%
conversion) → matured-window (≥7d SP / ≥14d SB·SD) → internal-competition consolidation
(a term live in >1 ENABLED campaign blocks the bid-up until consolidated to the lowest-ACOS
owner). **An over-ceiling raise is REFUSED, not clamped** — the `GateRefusal` surfaces the
breaching projected TACOS verbatim; the agent never silently rewrites the raise to the ceiling.

Reconcile a fired write by `actions_get` → terminal status **plus** a `*_FIND` echo — never by
a next-day export (the analytics tables lag ~24h). Log every applied change to
`state/decisions.md` and a `brain/raw/` note carrying the `actionId`.
