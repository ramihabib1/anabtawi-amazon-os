---
phase: 08-reversible-write-apply-spine-stop-the-bleed
plan: 04
subsystem: ppc
tags: [datadoe, actions_start, apply-spine, canary, runbook, ppc, reversible-write, stand-down]

# Dependency graph
requires:
  - phase: 08-03
    provides: apply_action.py CLI + --confirm-canary + the apply spine (BUILD→denylist→margin gate→dryRun→apply→poll→FIND-echo→reconcile→ledger)
  - phase: 08-02
    provides: idempotency ledger, owned-ASIN denylist, magnitude cap, find-cache staleness window
provides:
  - "tasks/stop-the-bleed-batch.md — the runbook that drives the canary + stop-the-bleed batch via apply_action.py"
  - "Live verification that the dead-SKU bleed was already ~95% eliminated; the batch was correctly stood down (no destructive writes)"
affects: [phase-09, phase-10, ppc-daily, the live-write rollout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Runbook-as-prompt: a tasks/*.md cadence prompt that sequences MCP calls + apply_action.py invocations"
    - "FIND-before-write caught a stale premise BEFORE any mutation — the spine's gate value proven by a no-write outcome"

key-files:
  created:
    - tasks/stop-the-bleed-batch.md
    - brain/raw/2026-06-24_stop-the-bleed-premise-stale.md
    - data/ads_dead_asins_spend_2026-06-10_2026-06-24.csv
    - data/ads_stockout_campaign_30844736154957_2026-06-10_2026-06-24.csv
    - data/ads_total_spend_2026-06-10_2026-06-24.csv
  modified:
    - state/decisions.md

key-decisions:
  - "Batch STOOD DOWN after live verification: the dedicated dead-SKU campaigns were already PAUSED (since ~Feb), and residual dead-ASIN spend (~$44/mo, ~9.7% of spend — NOT the assumed 43%/$279mo) lives in SHARED keyword campaigns that also serve healthy, profitable SKUs. A whole-campaign pause would be destructive."
  - "The live FIND + dryRun path was exercised end-to-end against the real account (DataDoe access enabled by Rami) — proving the spine works live — without any dryRun:false mutation."

patterns-established:
  - "DataDoe access gate is two-layer: account access level 'Read and write' (Accounts page) + per-action-type enable (Settings>Actions). Even read-only FIND needs 'Read and write'. Access can revert (invitation-link accounts)."

requirements-completed: []  # WRITE-03/06 (a real mutating write) intentionally NOT landed — no valid target existed; deferred to Phase 9. EXEC-01 denylist enforced in code (08-02).

# Metrics
duration: ~spread across session
completed: 2026-06-24
---

# Phase 08 Plan 04: Stop-the-Bleed — Runbook + Live Verification → Batch Stood Down

**The runbook was written, the DataDoe org-enable was cleared, and the live FIND/dryRun path was
exercised end-to-end against the real account — proving the apply spine works live. But the
stop-the-bleed batch was deliberately NOT executed: live verification showed the premise was
stale and the planned action would have been destructive. No `dryRun:false` mutation was made.**

## Outcome: correct stand-down (the spine's gate value, proven by a no-write result)

Task 1 (runbook) was authored and committed. Rami cleared the org-enable gate (Task 2). On Task 3,
before any mutation, the FIND-before-write step pulled the **current** live state — and it
contradicted the 2-week-old premise:

- **The dedicated dead-SKU campaigns are already PAUSED.** A live `CAMPAIGNS_FIND` on FX-M8MA's
  ASIN (B0FTSM2HSJ) returned 8 AIHELLO SP campaigns, all `state:PAUSED` since ~2026-02-26; the
  other two dead ASINs returned no ASIN-named SP campaigns.
- **Residual dead-ASIN ad spend is ~$20.4/14d ≈ ~$44/mo = ~9.7% of current spend** (total ENABLED
  SP = $209.31/14d), NOT the assumed ~43% / ~$279/mo.
- **That residual is inside SHARED keyword campaigns serving healthy SKUs.** The biggest
  (`SP - Phrase - stock out`, id 30844736154957) wastes $17.34 on dead B0FTSMTDGP but earns
  **$155.94 on $33.18 for healthy B0FXX46ST8** in the same campaign. Another ($1.52 on FX-M8MA)
  actually returned **$28 in sales**. Pausing these whole campaigns — as the runbook instructs —
  would kill healthy, profitable revenue.

Per CLAUDE.md hard rules (don't act destructively; surface when the target contradicts its
description), the batch was stood down. The one genuine residual waste (~$37/mo, dead B0FTSMTDGP
inside the shared `stock out` campaign) needs a **product-ad pause** (`AMAZON_ADS_ADS_UPDATE`) —
out of this phase's org-enabled scope — and is deferred.

Evidence cached: `data/ads_dead_asins_spend_2026-06-10_2026-06-24.csv`,
`data/ads_stockout_campaign_30844736154957_2026-06-10_2026-06-24.csv`,
`data/ads_total_spend_2026-06-10_2026-06-24.csv`. Full write-up:
`brain/raw/2026-06-24_stop-the-bleed-premise-stale.md`.

## What landed
- `tasks/stop-the-bleed-batch.md` — the runbook (Task 1), committed `433c901`.
- Live proof the apply path works against the real account: `actions_details_schema_get` ×3,
  read-only `*_FIND` ×4 (COMPLETED), `actions_start dryRun:true` ×3 (all VALIDATED). Zero mutations.
- `brain/raw/2026-06-24_stop-the-bleed-premise-stale.md` + 3 cached evidence exports.
- `state/decisions.md` line recording the stand-down (no writes).

## What did NOT land (and why that's correct)
- **No `dryRun:false` write.** WRITE-03/WRITE-06's "first real mutating write" did not land —
  because no valid, non-destructive target existed. Forcing a write to satisfy a checklist would
  violate the golden rules. The first real *mutating* write is deferred to **Phase 9**, where the
  daily ranked queue surfaces genuine, gate-passed targets.
- The own-ASIN denylist (EXEC-01) is enforced in code (08-02) and unit-tested; it simply had no
  live payload to refuse this run.

## Deviations from Plan
**Major (justified):** Tasks 2/3 did not execute the batch. The plan assumed an active
~$279/mo dead-SKU bleed; live data showed it already ~95% eliminated and the residual non-pausable
without collateral damage. The deviation is the correct application of the spine's safety intent.

## Self-Check: PASSED
- FOUND: `tasks/stop-the-bleed-batch.md`, `brain/raw/2026-06-24_stop-the-bleed-premise-stale.md`,
  the 3 `data/ads_*` evidence exports, the `state/decisions.md` stand-down line.
- CONFIRMED: zero `dryRun:false` mutations this phase (no `data/actions_ledger.jsonl` written).
- The apply spine (Plans 01–03) is built, pytest-green, and live-`dryRun`-validated.

---
*Phase: 08-reversible-write-apply-spine-stop-the-bleed*
*Plan: 04 — COMPLETE (runbook + live verification → batch correctly stood down)*
*Completed: 2026-06-24*
