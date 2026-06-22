---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: milestone
status: executing
last_updated: "2026-06-22T10:23:26.788Z"
last_activity: 2026-06-22 -- Phase 07 Plan 03 complete (gate.py money core, test_gate.py 7/7 GREEN)
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 8
  completed_plans: 7
  percent: 20
---

# Project State: Habib OS

<!-- Project memory. Updated at phase/plan transitions. -->

## Project Reference

- **Core value (M2):** Move the units already in FBA at a healthy, margin-derived TACOS (not a flat number) — turning reviewed PPC artifacts into real, approval-gated account changes via DataDoe `actions_start`, with the margin gate protecting net margin ≥ ~15% and zero autonomous spend-up.
- **Milestone:** v2.0 — Execution Era (Gated PPC Write Path). PPC writes only; catalog refresh / restocks / listing writes deferred.
- **Current focus:** Phase 07 — margin-tiered-safety-gate
- **Project mode:** execution-layer on the M1 read-only engine (agent does MCP I/O; hand-written, pytest-covered Python owns the money truth)

## Current Position

Phase: 07 (margin-tiered-safety-gate) — EXECUTING
Plan: 4 of 4 (07-01, 07-02, 07-03 complete; 07-04 gate_action CLI remaining)
Status: Executing Phase 07
Last activity: 2026-06-22 -- Phase 07 Plan 03 complete (gate.py money core, test_gate.py 7/7 GREEN)

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete (M2) | 0/5 |
| Requirements mapped | 21/21 |
| Real writes landed | 0 |

## Accumulated Context

### Key Decisions (constrain execution)

- **M2 write path = DataDoe `actions_start`** (not a custom SP-API MCP); gated 4 ways (connection · dryRun · human approval · DataDoe org-enable). Python never opens a socket — the agent does all MCP I/O.
- **M2 efficiency gate = per-SKU margin-tiered TACOS**, derived from each SKU's own contribution margin to hold net ≥ ~15%. NOT a flat 25% (the 25% is only the aggressive ceiling on high-margin winners). Missing margin/threshold → typed refusal, never a default.
- **Margin gate is a hard predecessor to any spend increase** (Phase 7 ships before any real spend-up in Phases 9–10). It must refuse on everything until `min_net_margin_pct` is set.
- **Autonomy = standing approval for reversible moves** (pause / negative / bid-down) within a magnitude cap; explicit approval for spend-up / new campaigns / archive. Standing-approved actions still log (autonomy ≠ silence).
- **Reconcile via `actions_get` COMPLETED + console, never next-day DataDoe exports** (≤24h reporting lag).
- **Two-class verdict model** (attribution lag): act-now reversible stop-loss on obviously-dead campaigns vs judge-later efficiency verdicts that wait for a matured window (≥7d SP / ≥14d SB/SD).
- **Binding EXCLUDE rule:** own private-label ASIN B07TV972JT (and any owned ASIN) on a hard never-target denylist; any payload targeting it refused before dryRun.
- **Archive (`CAMPAIGNS_REMOVE`) is the only low-reversibility move** — runs dead-last, its own explicitly-approved batch, per-ID pre-check (PAUSED + zero-spend ≥30d).
- Money math stays hand-written + pytest-covered (`engine/`); `cd engine && uv run pytest` must stay green. Gate is the new money-logic contract.

### Open Items (resolve in phase discussion)

- **Blocking — operator config:** set `min_net_margin_pct` (~15%) in `thresholds.toml` (currently empty `""`); the gate refuses everything until set (gates Phase 7 / any spend-up).
- **Blocking — data:** make the SKU→tier/contribution-margin table in `anabtawi-context` machine-readable (gate hard dependency; gates spend-up in Phase 9).
- **Blocking — org-enable:** enable each Ads action type in DataDoe Settings → Actions (reversible set before Phase 8; hold CAMPAIGNS_ADD/REMOVE until Phase 10).
- **Phase 7:** pin the closed-form per-tier TACOS-ceiling-from-margin formula + the authoritative contribution-margin source (premium Profit-by-SKU vs COGS reconciliation) before writing `gate.py`.
- **Phase 9:** set harvest-loop graduation thresholds and the ≥6-week inventory-cover binding value + velocity source in `state/targets.md`; define the standing-approval magnitude cap; decide whether phrase/broad negatives need explicit approval.
- **Phase 10:** resolve the portfolios decision (tier in name+tags vs Rami-created console portfolios); pin the projected-TACOS seed for no-history new campaigns.

### Todos / Watch-fors

- Attribution lag is the #1 pitfall: never pause/cut on an immature window; "3 clean days" = 3 days of *matured* data.
- Negative-keyword collateral: keep-positive allowlist (`baklava gift box`) checked before any `TARGETS_ADD negative:true`; negate exact by default; "watch don't negate" terms → bid-down.
- Bidding against yourself: dedupe "baklava" EXACT (live in ≥4 campaigns) before any bid-up.
- Partial-build atomicity: dryRun the full create chain; gate each step on prior COMPLETED + returned ID; rollback the partial campaign on failure.
- Idempotency: content-hash dedup persisted in `data/actions_ledger.jsonl`; in-flight `actionId` resumes at poll, never re-fires start.

### Blockers

None hard-blocking roadmap; three operator preconditions (min-margin floor, machine-readable SKU→margin table, org-enable) must clear before their respective phases pass a real write.

## Session Continuity

- **Last action:** Phase 07 Plan 03 executed — `engine/src/habibos/gate.py` implemented as the hand-written, pytest-covered margin-tiered safety money core (pre-ad CM% with ad_spend added back, per-SKU ceiling = CM% − min_net_margin_pct, worst-case projection, typed GateVerdict/GateRefusal refusing on every missing/over-ceiling input). `test_gate.py` 7/7 GREEN; full engine suite 33 passed / 5 skipped (pre-existing Supabase/context skips). Commit `183c1de`.
- **Next action:** `/gsd:execute-phase 7` continues with 07-04 (gate_action CLI: argv → gate.evaluate inside logged_call → JSON stdout, mirroring answer_tacos.py). The gate money contract is now the Phase 7 truth layer.

---
*State initialized: 2026-06-08 · Milestone v2.0 roadmap state set: 2026-06-20*
