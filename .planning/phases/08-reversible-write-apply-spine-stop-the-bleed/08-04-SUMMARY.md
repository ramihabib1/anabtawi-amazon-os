---
phase: 08-reversible-write-apply-spine-stop-the-bleed
plan: 04
subsystem: ppc
tags: [datadoe, actions_start, apply-spine, canary, runbook, ppc, reversible-write]

# Dependency graph
requires:
  - phase: 08-03
    provides: apply_action.py CLI + --confirm-canary + the apply spine (BUILD→denylist→margin gate→dryRun→apply→poll→FIND-echo→reconcile→ledger)
  - phase: 08-02
    provides: idempotency ledger, owned-ASIN denylist, magnitude cap, find-cache staleness window
provides:
  - "tasks/stop-the-bleed-batch.md — the runbook that drives the canary + stop-the-bleed batch via apply_action.py"
affects: [phase-09, phase-10, ppc-daily, the live-write rollout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Runbook-as-prompt: a tasks/*.md cadence prompt that sequences MCP calls + apply_action.py invocations (mirrors morning-briefing/ppc-daily style)"
    - "Canary-then-batch: one --confirm-canary pause reconciled COMPLETED before the standing-approved batch"

key-files:
  created:
    - tasks/stop-the-bleed-batch.md
  modified: []

key-decisions:
  - "Runbook routes campaign identity through *_FIND + find_cache, never sku_catalog.toml (only 2 of 4 dead SKUs are in it; a pause is spend-decreasing so the margin gate auto-passes with no catalog read)"
  - "keep-positive allowlist `baklava gift box` is never negated; watch-don't-negate terms are bid-down not negated; exact-only negatives (no phrase/broad)"
  - "Reconcile via actions_get COMPLETED + *_FIND echo, never via a next-day DataDoe export (≤24h lag)"

patterns-established:
  - "Canary one-time confirm: --confirm-canary on the phase's first apply only; the marker auto-applies subsequent reversible moves"
  - "Org-enable precondition surfaced as a 412 → action_type_disabled refusal (surface, never retry)"

requirements-completed: []  # WRITE-03, WRITE-06, EXEC-01 are NOT yet complete — they require the live writes in Tasks 2/3, gated behind the human org-enable.

# Metrics
duration: ~12min
completed: 2026-06-24
---

# Phase 08 Plan 04: Stop-the-Bleed Batch Runbook Summary (PARTIAL — Task 1 of 3)

**The stop-the-bleed batch runbook (`tasks/stop-the-bleed-batch.md`) is authored and committed — encoding the org-enable precondition, FIND-not-catalog identity, the canary, the exact-only negative harvest with the `baklava gift box` keep-positive, and reconcile-via-status. Tasks 2 and 3 (the live writes) are BLOCKED on the human org-enable gate.**

## ⚠️ PARTIAL EXECUTION — scope-limited run

This run executed **Task 1 ONLY** (write the runbook document). Tasks 2 and 3 were intentionally
**NOT executed** — they require Rami to flip the DataDoe Settings → Actions org-enable switches
(a UI/DB toggle outside any CLI/API surface Claude can drive) and then perform the first real
`dryRun:false` writes against the live Amazon account. **Zero live account writes were performed.
No `actions_start` with `dryRun:false`. No canary, no batch.** This run produced the runbook
document only.

## Performance

- **Duration:** ~12 min
- **Tasks:** 1 of 3 (Task 1 complete; Tasks 2/3 await the human org-enable gate)
- **Files modified:** 1 (`tasks/stop-the-bleed-batch.md` created)

## Accomplishments
- Wrote `tasks/stop-the-bleed-batch.md` — the runbook that drives the canary + stop-the-bleed
  batch through `engine/scripts/apply_action.py`.
- Encoded every Task-1 acceptance criterion: the 4 dead SKUs (FX-M8MA, 9Z-KUHZ, VH-ZTOC,
  ZK-4NDS), the `--confirm-canary` one-time gate, the `baklava gift box` keep-positive allowlist,
  identity routed through `*_FIND`/`find_cache` (never `sku_catalog.toml`), reconcile-via-
  `actions_get`-COMPLETED + FIND echo (never a DataDoe export), exact-only negatives, and
  watch-don't-negate → bid-down.
- Mirrored the existing `tasks/*.md` cadence-prompt style (morning-briefing / ppc-daily).

## Task Commits

1. **Task 1: Write the stop-the-bleed batch runbook** — `433c901` (feat)

_Tasks 2 (org-enable human-action checkpoint) and 3 (live canary + batch human-verify
checkpoint) were not executed — see "Tasks Awaiting the Human Org-Enable Gate" below._

## Files Created/Modified
- `tasks/stop-the-bleed-batch.md` — the runbook prompt the agent executes to run the canary +
  stop-the-bleed batch via the apply CLI; sequences org-enable precondition → FIND → canary →
  batch → reconcile → human spot-check.

## Verification

Task-1 automated verify (from the plan) **PASSED**:
```
test -f tasks/stop-the-bleed-batch.md \
  && grep -qiE "confirm[-_]canary" tasks/stop-the-bleed-batch.md \
  && grep -qi "baklava gift box" tasks/stop-the-bleed-batch.md \
  && grep -qi "FIND" tasks/stop-the-bleed-batch.md   # → OK
```
Additional acceptance checks passed: `apply_action.py` referenced, all 4 dead SKUs named, "do
not route dead-SKU identity through sku_catalog" present, watch-don't-negate present,
reconcile-not-via-export present.

## Tasks Awaiting the Human Org-Enable Gate

- **Task 2 — Org-enable (checkpoint:human-action, gate=blocking):** Rami must enable the three
  reversible Ads action types in DataDoe Settings → Actions (`campaign-state update` /
  `negative-keyword create exact` / `target-state update`) and leave `CAMPAIGNS_ADD/REMOVE` OFF.
  This is a UI/DB toggle with **no CLI/API surface** Claude can drive, OFF by default — a 4th
  access-control gate. Until cleared, a real `dryRun:false` apply returns
  **412 → action_type_disabled** (surface, never retry). **Resume signal:** Rami replies
  "enabled".
- **Task 3 — Run the canary + batch (checkpoint:human-verify, gate=blocking):** the first real
  writes — FIND the 4 dead-SKU campaigns, run the canary single pause via
  `apply_action.py --confirm-canary`, reconcile to COMPLETED + FIND echo, then the
  standing-approved batch (whole-campaign pauses + exact negatives, keep-positive protected),
  logging `data/actions_ledger.jsonl` + `state/decisions.md` + `brain/raw/2026-06-23_stop-the-bleed-batch.md`
  per move. **Blocked on Task 2.**

## Decisions Made
None beyond the plan — the runbook encodes the plan's D-03/D-04/D-05 batch scope, D-08/D-09
canary sequencing, D-10 idempotency, D-11 logging, and the reconcile-via-status discipline
exactly as specified.

## Deviations from Plan
None — Task 1 executed exactly as written. Tasks 2/3 were not deviations; they are the plan's
own blocking human checkpoints, intentionally not crossed in this scope-limited run.

## Issues Encountered
The two referenced `brain/raw/` files (`2026-06-16_ppc-coverage-gap.md`,
`2026-06-20_datadoe-write-path-gating.md`) are untracked in the main checkout and thus absent
from this worktree's base commit; read them from the main checkout for context. No impact on
Task 1 (pure documentation authoring).

## Next Phase Readiness
- **Runbook ready.** The full apply spine + CLI (Plans 01–03) is built, tested, dry-run-ready;
  the runbook is now authored. The **only** remaining gate before the first real reversible
  write is the DataDoe org-enable (Task 2), which Claude cannot flip.
- **Blocker:** Tasks 2 and 3 require Rami's org-enable + spot-check. WRITE-03 / WRITE-06 /
  EXEC-01 are **not** yet complete — they land only when the live canary + batch run and
  reconcile (Task 3).

---
*Phase: 08-reversible-write-apply-spine-stop-the-bleed*
*Plan: 04 — PARTIAL (Task 1 of 3)*
*Completed (Task 1): 2026-06-24*
