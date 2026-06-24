---
status: partial
phase: 09-daily-ranked-queue-explicit-approval-spend-up
source: [09-05-PLAN.md Task 3 (checkpoint:human-verify)]
started: 2026-06-24
updated: 2026-06-24
---

## Current Test

[awaiting the focused live first-write session — see brain/raw/2026-06-24_phase9-queue-live-findings.md]

## Context

Phase 9 code is complete and pytest-green (83 passed); the DataDoe write path is verified live
(CAMPAIGNS_FIND COMPLETED; 0 mutating writes ever). These items prove the queue LIVE and must be
done with FRESH data (agentcentral is expired → reads via DataDoe exports; cached cover is ~3wk
stale). No account change has been made.

## Tests

### 1. Live dollar-ranked render
expected: `queue_run.py render` (fed fresh DataDoe FBA cover + matured ad-ACOS + candidate set) prints one dollar-ranked, class-tagged, provenance-cited table; no-$-estimate rows last.
result: [pending]

### 2. Sub-cover SKU refused
expected: a SKU below the 42-day cover floor (e.g. a ~1-FBA-unit SKU) renders REFUSED (cover_below_floor), not actionable.
result: [pending]

### 3. One gate-passed spend-up applied
expected: exactly ONE gate-passed funded winner (a budget_up/bid_up on an existing ENABLED campaign) is dryRun'd VALIDATED, then `apply --approve` reconciles (poll COMPLETED + *_FIND echo) and logs to decisions.md + brain/raw with the actionId.
result: [pending]

### 4. Over-ceiling raise refused, not clamped
expected: a deliberately-too-high raise on a thin-margin SKU returns GateRefusal(over_ceiling) surfacing the breaching projected TACOS — never a clamped value.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
