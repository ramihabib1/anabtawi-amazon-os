---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
plan: 01
subsystem: engine
tags: [thresholds, config-dials, cover-gate, conversion-floor, magnitude-cap, dollar-ranked-queue, anti-fabrication, red-contract, tdd]

# Dependency graph
requires:
  - phase: 08-02
    provides: magnitude.py seeded-permissive cap (max_reversible_pct_change dial seeded empty); the asymmetric None-dial pattern
  - phase: 07
    provides: thresholds.read None-dial (empty=refuse); gate.py strict-breach-never-clamp + spend-direction-first grammar; result.py typed grammar (GateRefusal/ProposedAction); tacos.py fixture-driven _pct-mirror test pattern
provides:
  - "engine/config/thresholds.toml — three LIVE Phase-9 dials in [marketplace.CA]: max_reversible_pct_change=50 (D-01), days_of_cover_floor=42 (D-03), conversion_benchmark=12 (D-05, ADDED to the machine mirror)"
  - "engine/tests/test_thresholds.py — test_phase9_dials_live asserting 50.0/42.0/12.0 read back as floats (anti-tampering guarantee T-09-01-01/02)"
  - "engine/tests/test_cover_gate.py — RED contract for the inventory+conversion spend-up gate (cover_below_floor never clamps, ==42 passes, conversion_below_floor, no_threshold_set, spend-down passes, GG-0DC1 1-unit edge)"
  - "engine/tests/test_rank_queue.py — RED contract for the dollar-ranked queue estimator (dollars-desc/None-last sort, undefined-estimate is None not 0, estimates rebuilt from fixture components)"
  - "engine/tests/test_queue.py — RED contract for the class-tagging renderer (spend-up + phrase/broad-negative=needs-approval, reversibles=auto, render-row schema)"
  - "engine/tests/fixtures/queue_candidates.json — 5-row candidate fixture with one zero-denominator None-estimate edge row, no seller UUID"
affects: [09-02, 09-03, 09-04, cover-gate, rank-queue, queue-renderer, spend-up-path]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Build-the-mechanism-then-flip-the-dial: D-01/D-03 machinery shipped in Phases 7-8, this plan flips the config values live (no code change)"
    - "Sequenced cross-file dependency: conversion_benchmark ADDED to the machine mirror (thresholds.toml) before the gate that reads it (Plan 02) — the engine reads thresholds via thresholds.read, not state/targets.md"
    - "RED contract baseline: contract tests import not-yet-existing modules and fail RED on the import so Waves 2-4 are GREEN-the-suite exercises (CLAUDE.md hard rule 3, test-first)"
    - "Anti-tampering assertion: test_phase9_dials_live trips if any live dial silently reverts to empty/absent (None)"
    - "Fixture estimate rebuilt from its own components: the ranker test recomputes expected weekly-$ from queue_candidates.json's components (the tacos _pct-mirror) so a fabricated estimate cannot pass review (T-09-01-03)"

key-files:
  created:
    - engine/tests/test_cover_gate.py
    - engine/tests/test_rank_queue.py
    - engine/tests/test_queue.py
    - engine/tests/fixtures/queue_candidates.json
  modified:
    - engine/config/thresholds.toml
    - engine/tests/test_thresholds.py

key-decisions:
  - "max_reversible_pct_change flipped \"\" -> 50 (D-01): the reversible magnitude cap is LIVE; a move steeper than -50% per action is refused and routed to explicit review (strict >cap breach, equal passes, never clamped — mirror magnitude.py:65)"
  - "days_of_cover_floor flipped \"\" -> 42 (D-03): 6-week maintain cover (targets.md:23 min_weeks_cover_maintain x 7); a sub-cover SKU is refused from any spend-up; refuse-never-default (a missing floor REFUSES, the asymmetry vs the magnitude cap)"
  - "conversion_benchmark ADDED = 12 to [marketplace.CA] (D-05): previously lived ONLY in state/targets.md:34; the engine reads thresholds via thresholds.read, so it MUST exist in the machine mirror before the conversion gate (Plan 02) can read it — the sequenced cross-file dependency PATTERNS.md flagged. PROVISIONAL: retune to portfolio top-quartile after a sales_and_traffic pull"
  - "min_net_margin_pct / acos_ceiling_pct / tacos_ceiling_pct left UNCHANGED (15/30/15) per the task's do-not-touch scope"
  - "Cover-gate contract mirrors magnitude.check's pure-predicate shape extended for two floors (cover + conversion); final signature is decided in Plan 02 — the RED contract pins the BEHAVIOR each branch must exhibit, not the exact arg list"

patterns-established:
  - "Flip-the-dial config change with a paired anti-tampering test asserting the live value"
  - "Cross-file mirror sequencing: add a threshold to the machine mirror in the wave BEFORE the gate that reads it"
  - "RED contract pins behavior (refusal codes, never-clamp, sort order, None-not-0) against a final signature decided downstream"

requirements-completed: [QUEUE-01, QUEUE-03, EXEC-05]

# Metrics
duration: 5min
completed: 2026-06-24
---

# Phase 9 Plan 01: Live Phase-9 Threshold Dials + RED Contract Baseline Summary

**Flipped the two seeded-permissive config dials to their real Phase-9 values (magnitude cap 50%, cover floor 42 days), ADDED the conversion benchmark (12%) to the machine-readable threshold mirror so the engine can read it, and laid down the three RED contract test files (cover_gate / rank_queue / queue) plus a candidate fixture that Waves 2-4 turn GREEN.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-24T12:55Z
- **Completed:** 2026-06-24T13:00Z
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- **Three LIVE Phase-9 dials (D-01/D-03/D-05):** `max_reversible_pct_change` flipped `""` → `50` (a reversible move steeper than -50% is now refused and routed to explicit review, never clamped); `days_of_cover_floor` flipped `""` → `42` (a sub-6-week-cover SKU is refused from any spend-up, refuse-never-default); `conversion_benchmark = 12` ADDED to `[marketplace.CA]` — it previously lived ONLY in `state/targets.md`, so the engine (which reads via `thresholds.read`) could not see it. All three read back as the exact floats 50.0 / 42.0 / 12.0. The three untouched ceilings stay 15/30/15.
- **Anti-tampering assertion (T-09-01-01/02):** `test_phase9_dials_live` in `test_thresholds.py` pins the three live floats with `isinstance(..., float)` — a silent revert of any dial to `""`/absent flips the value to `None` and trips the test. The stale `days_of_cover_floor is None` assertion was removed (the dial is live now); the refuse-on-empty path stays covered via an absent key and an absent marketplace (`ZZ`).
- **Three RED contracts + a candidate fixture:** `test_cover_gate.py` (6 contracts: cover_below_floor never clamps, cover==42 passes, conversion_below_floor, no_threshold_set refuse-never-default, spend-down passes without a floor read, GG-0DC1-at-1-unit edge), `test_rank_queue.py` (dollars-descending/None-last sort, undefined zero-denominator estimate is None not 0, estimates rebuilt from the fixture's own components, every row carries provenance), `test_queue.py` (spend-up + phrase/broad-negative tag `needs-approval`, reversibles tag `auto`, render-row schema). All three FAIL RED on the missing `cover_gate` / `rank_queue` (+ `QueueRow`) / `queue` modules — the intended Wave-1 baseline. `queue_candidates.json` carries 5 production-shaped rows (real CA fixture SKUs) including the `C5-TXQU-Y67R` zero-`ad_sales_sum` row that exercises the None-sorts-last edge; no seller UUID, no network.

## Task Commits

Each task was committed atomically:

1. **Task 1: flip cover+magnitude dials live, add conversion_benchmark to thresholds.toml** — `a29fc30` (feat)
2. **Task 2: assert the three Phase-9 dials read back live (D-01/D-03/D-05)** — `8cb91a9` (test)
3. **Task 3: add RED contracts for cover_gate, rank_queue, queue + candidate fixture** — `044d6d3` (test)

## Files Created/Modified
- `engine/config/thresholds.toml` (modified) — flipped `days_of_cover_floor` → 42 and `max_reversible_pct_change` → 50; ADDED `conversion_benchmark = 12`; all in `[marketplace.CA]`; per-key WHY+units+asymmetry comment style preserved
- `engine/tests/test_thresholds.py` (modified) — added `test_phase9_dials_live`; removed the stale `days_of_cover_floor is None` assertion; kept the absent-key + absent-marketplace refuse-on-empty coverage
- `engine/tests/test_cover_gate.py` (created) — RED contract for the inventory+conversion spend-up gate
- `engine/tests/test_rank_queue.py` (created) — RED contract for the dollar-ranked queue estimator
- `engine/tests/test_queue.py` (created) — RED contract for the class-tagging renderer
- `engine/tests/fixtures/queue_candidates.json` (created) — 5-row candidate fixture with one zero-denominator None-estimate edge row

## Decisions Made
- **Flip-the-dial, not a code change.** D-01 (magnitude cap) and D-03 (cover floor) machinery already exists and is pytest-covered from Phases 7-8; this plan only flips the config VALUES live. The cap was `""`-permissive (magnitude.py: empty PASSES); the cover floor was `""`-refuse (the floor asymmetry — empty REFUSES). Both are now real numbers.
- **conversion_benchmark added to the machine mirror BEFORE the gate that reads it.** The engine reads thresholds via `thresholds.read(key, marketplace)` against `thresholds.toml`, never against `state/targets.md`. D-05's benchmark lived only in `targets.md:34`, so it was ADDED to `thresholds.toml[marketplace.CA]` in this wave — the sequenced cross-file dependency, so Plan 02's conversion gate has a value to read. Marked PROVISIONAL in the comment (retune to portfolio top-quartile after a sales_and_traffic pull).
- **Cover-gate contract pins behavior against a downstream-decided signature.** The plan defers the final `cover_gate.check` signature to Plan 02; the RED contract mirrors `magnitude.check(action, cap)`'s pure-predicate shape extended for the two floors (cover + conversion) and pins the refusal codes, the never-clamp `breached_value`, the strict-`<` equal-passes semantics, and the spend-direction-first branch. Since the file is RED-on-import anyway, the exact arg list is what Plan 02 implements against.
- **Fixture estimate is rebuilt from its own components (T-09-01-03).** `test_rank_queue.py` recomputes each expected weekly-$ value from `queue_candidates.json`'s raw components (`delta_spend_weekly`, `ad_spend_sum`, `ad_sales_sum`) using the documented estimator model — the `tacos._pct`-mirror pattern — so a fabricated estimate in the fixture cannot pass review unnoticed.

## Deviations from Plan

None — the plan executed exactly as written. The three dials are live, `test_thresholds.py` asserts them and passes, the three RED contract files import their target modules and fail RED, and `queue_candidates.json` is committed with the None-estimate edge row and no secret. No Rule 1-4 deviations were needed.

## Issues Encountered
- **`test_env.py::test_seller_id_in_env_not_code` fails in this isolated worktree** (1 failure outside this plan's scope). This is a PRE-EXISTING, out-of-scope environment-config gap unrelated to this plan's changes: `test_env.py` imports no `habibos` code touched here and asserts the gitignored `.env` carries `AMAZON_CA_SELLER_ID`, which is absent in a fresh worktree (`.env` is gitignored and never copied into a worktree — confirmed via `git check-ignore`). NOT auto-fixed — materializing the seller UUID into the worktree would violate CLAUDE.md hard rule 5 (secrets live in `.env`, never inlined/committed). It passes in the primary checkout where `.env` exists. The rest of the suite is green.

## Test Results
- **`test_thresholds.py`:** 4/4 GREEN (the original 3 + the new `test_phase9_dials_live`).
- **Dial read-back verified:** `thresholds.read("max_reversible_pct_change","CA")` → 50.0, `days_of_cover_floor` → 42.0, `conversion_benchmark` → 12.0; untouched ceilings still 15/30/15.
- **No-regression suite:** `test_magnitude_cap.py` + `test_gate.py` + `test_tacos.py` → 18 passed (the dial flips do not perturb the Phase 7-8 money logic, which reads `min_net_margin_pct`/`acos`/`tacos`, all unchanged).
- **Full suite excluding the three intended-RED files:** 52 passed, 5 skipped, 1 failed (the out-of-scope `test_env` worktree env-gap above) — matches the stated baseline (52 passed / 5 skipped) plus the worktree-local env failure that pre-dates this plan.
- **The three RED contracts:** `pytest tests/test_cover_gate.py tests/test_rank_queue.py tests/test_queue.py` exits non-zero (exit 2, collection error on the missing `cover_gate` / `rank_queue`+`QueueRow` / `queue` imports) — the intended Wave-1 baseline, NOT a defect.

## Threat Model Coverage
- **T-09-01-01 (cover/conversion dial tampering):** mitigated — refuse-never-default semantics carry over (an empty floor REFUSES, the gate.py:198-204 grammar the cover gate will reuse); `test_phase9_dials_live` asserts the live 42.0/12.0 so a silent revert to `""` is caught.
- **T-09-01-02 (magnitude cap tampering):** mitigated — the strict `>cap` breach never clamps (magnitude.py:65); the flip to 50 is asserted by `test_phase9_dials_live`; equal-to-cap passes is the documented semantics.
- **T-09-01-03 (fixture estimate repudiation):** mitigated — `test_rank_queue.py` rebuilds expected weekly-$ from the fixture's own components (the `_pct`-mirror), so a fabricated estimate cannot pass review.
- **T-09-01-SC (package installs):** N/A / ACCEPTED — no `uv`/`pip` installs in this plan; config + tests only, nothing added to the dependency set.

## Threat Surface Scan
No new security-relevant surface introduced. This plan touches config values (operator policy numbers, not secrets) and test files only — no new network endpoints, no auth paths, no file-access patterns, no trust-boundary schema changes. The committed fixture carries sanitized component sums and public-shaped SKU/entity strings, no seller UUID.

## Next Phase Readiness
- **Plan 09-02 (cover + conversion spend-up gate) is unblocked:** `thresholds.read("days_of_cover_floor"|"conversion_benchmark","CA")` now return 42.0/12.0, and `test_cover_gate.py` is the RED contract `habibos.cover_gate` implements against.
- **Plans 09-03/09-04 (dollar-ranked queue + class-tagging renderer) are unblocked:** `test_rank_queue.py` / `test_queue.py` + `queue_candidates.json` are the RED contracts `habibos.rank_queue` (+ a new `QueueRow` in result.py) and `habibos.queue` implement against.
- **No live writes performed.** This plan edited local config + tests and ran pytest only.

## Self-Check: PASSED

All 6 created/modified files verified present; all 3 commits (a29fc30, 8cb91a9, 044d6d3) verified in git log.

---
*Phase: 09-daily-ranked-queue-explicit-approval-spend-up*
*Completed: 2026-06-24*
