---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
plan: 03
subsystem: engine-money-core
tags: [queue, ranker, money-logic, tdd, provenance, D-07]
requires:
  - "09-01: queue_candidates.json fixture + test_rank_queue.py RED contract"
  - "habibos.result.SkuRow (the dataclass shape mirrored)"
  - "habibos.tacos._ratio (the None-on-undefined grammar cloned)"
provides:
  - "habibos.result.QueueRow — typed ranked-row result for the daily queue"
  - "habibos.rank_queue.estimate_weekly_usd — expected-$/wk impact estimator"
  - "habibos.rank_queue.rank — dollars-first ranker (None-estimate rows last)"
affects:
  - "09-04 queue.py renderer (consumes QueueRow, sets the real cls tag)"
tech-stack:
  added: []
  patterns:
    - "None-on-undefined estimator (clones tacos._ratio: zero/missing denominator -> None, never 0/guess)"
    - "D-07 dollars-first sort key: (x.expected_weekly_usd is None, -(x.expected_weekly_usd or 0))"
    - "provenance carried per-row from the candidate's own data (engine names no source itself)"
    - "pure money-core: no socket, no fetch — agent feeds components via committed JSON artifact"
key-files:
  created:
    - "engine/src/habibos/rank_queue.py"
  modified:
    - "engine/src/habibos/result.py (added QueueRow only)"
decisions:
  - "rank() takes a single candidates-path arg (matches the RED test contract rank_queue.rank(FIXTURE)), NOT the plan's literal rank(candidates, source, window_from, window_to) signature — the test is the binding contract per CLAUDE.md."
  - "Estimator formula: expected weekly $ = delta_spend_weekly / (ad_spend_sum / ad_sales_sum); a spend-down yields a negative figure (a saving); zero/missing denominator -> None."
metrics:
  duration: ~10 min
  completed: 2026-06-24
  tasks: 2
  files: 2
---

# Phase 09 Plan 03: Dollar-Ranked Queue Ranker Summary

The pure, hand-written, pytest-covered queue ranker — an expected-weekly-$ impact estimator
(`delta_spend_weekly / window_acos_fraction`, cloning the `tacos._ratio` None-on-undefined
grammar) plus the D-07 dollars-first sort — emitting a new `QueueRow` typed result. Turns
Plan 01's `test_rank_queue.py` GREEN (4 passed).

## What Was Built

**Task 1 — `QueueRow` dataclass (`engine/src/habibos/result.py`, commit `e1e19f2`):**
A frozen `QueueRow` added immediately after `SkuRow`, mirroring its None-means-undefined
discipline. Fields: `sku`, `entity`, `action_type`, `current: float | None`,
`proposed: float | None`, `expected_weekly_usd: float | None`, `provenance: str`, and
`cls: str = "auto"`. The docstring pins that an `expected_weekly_usd` of `None` means "no
defensible estimate" — distinct from `0.0` and sorting LAST (D-07). Additive only; no
existing dataclass (`SkuRow`, `ProposedAction`, `GateRefusal`, `GateVerdict`, `Answer`)
was touched. `cover_gate.py` (owned by parallel plan 09-02) was not touched.

**Task 2 — `rank_queue.py` (`engine/src/habibos/rank_queue.py`, commit `ad73727`):**
A pure money-core (no socket, no fetch) with the hard-rule-3/4 anti-fabrication banner.
- `estimate_weekly_usd(candidate)` — clones the `tacos._ratio` shape: a missing component,
  a zero/missing `ad_sales_sum`, or a zero `acos_fraction` (zero `ad_spend_sum`) returns
  `None` (undefined), never `0` or a guess. Otherwise returns
  `round(delta_spend_weekly / (ad_spend_sum / ad_sales_sum), 2)`.
- `rank(candidates_path)` — reads the committed candidate JSON, builds one `QueueRow` per
  candidate (provenance carried from each candidate's own `provenance` field, falling back
  to the file's `source` + `window` header), and sorts with the D-07 key
  `(x.expected_weekly_usd is None, -(x.expected_weekly_usd or 0))` — highest expected-$/wk
  first, None-estimate rows last. `cls` left at the `QueueRow` default `"auto"` (Plan 04's
  `queue.py` sets the real reversibility class). `__all__ = ["estimate_weekly_usd", "rank"]`.

## How It Maps to Requirements / must_haves

- **"Proposed PPC changes are ranked by expected weekly $ impact, descending"** — the D-07
  sort key in `rank`; verified by `test_rows_sorted_dollars_desc_none_last`.
- **"A change with no defensible $ estimate sorts LAST, with a None estimate (never a
  fabricated 0)" (D-07)** — `estimate_weekly_usd` returns `None` on a zero denominator and
  the sort key keys `None` last; verified by `test_undefined_estimate_is_none_not_zero`
  (`C5-TXQU-Y67R`, `ad_sales_sum == 0` -> None -> `rows[-1]`).
- **"Every ranked row carries provenance citing the DataDoe source + window" (D-04)** —
  every `QueueRow.provenance` is non-empty, cites `57a0cb319c` and a `..` window range;
  verified by `test_every_row_carries_provenance`. The engine opens no socket; the agent
  feeds components via the committed artifact.
- **T-09-03-01 (fabricated $ cannot pass review)** — `test_estimates_match_fixture_components`
  rebuilds each estimate from the fixture's own components (the `test_tacos` `_pct`-mirror
  pattern), so a fabricated value would fail the contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Contract] `rank()` signature matches the RED test, not the plan's prose**
- **Found during:** Task 2 (reading the RED contract `test_rank_queue.py`).
- **Issue:** The plan's `<action>` text describes `rank(candidates, source, window_from,
  window_to) -> list[QueueRow]`, but the binding RED test calls `rank_queue.rank(FIXTURE)`
  with a single candidates-path argument and asserts provenance is rebuilt from the fixture's
  own `source`/`window`/per-row `provenance` data. Implementing the plan's literal 4-arg
  signature would have left `test_rank_queue.py` RED (the plan's own verify step requires it
  GREEN).
- **Fix:** `rank` takes one `candidates_path` arg, loads the JSON, and derives provenance per
  candidate from the candidate's own `provenance` field (fallback: the file's `source` +
  `window` header). The test is the contract (CLAUDE.md: "Tests are the contract").
- **Files modified:** `engine/src/habibos/rank_queue.py`.
- **Commit:** `ad73727`.

## Verification

- `cd engine && uv run pytest tests/test_rank_queue.py -q` -> **4 passed** (was RED on a
  missing import before this plan).
- `cd engine && grep -nE "requests|urllib|http\.client|socket|fetch" src/habibos/rank_queue.py`
  -> only docstring prose ("no socket", "no fetch"); the only code imports are `json`,
  `pathlib`, and `from .result import QueueRow` (engine opens no socket, D-04).
- `cd engine && uv run pytest tests/test_tacos.py tests/test_gate.py -q` -> 16 passed
  (the `result.py` addition is additive; existing dataclasses untouched).
- Full suite (excluding the two not-mine RED contracts `test_queue.py` [Wave 3] and
  `test_cover_gate.py` [plan 09-02]): **56 passed, 5 skipped, 1 failed**. The single failure
  is `test_env.py::test_seller_id_in_env_not_code` — the known fresh-worktree artifact
  (gitignored `.env` absent), flagged in the execution prompt as not-my-concern, not a
  regression from this plan.

## Threat Surface

No new security-relevant surface beyond the plan's `<threat_model>`. The three `mitigate`
dispositions are all satisfied: T-09-03-01 (estimate is hand-written + test-rebuilt from
candidate components), T-09-03-02 (zero/missing denominator -> None, never a guessed 0;
None rows sort last), T-09-03-03 (every row cites source-id + window; no seller UUID in any
row). No package installs (T-09-03-SC accept).

## Known Stubs

None. `cls` defaulting to `"auto"` is intentional per the plan — Plan 04's `queue.py` owns
the reversibility-class tag; the ranker deliberately computes none.

## Self-Check: PASSED

- `engine/src/habibos/rank_queue.py` — FOUND
- `class QueueRow` in `engine/src/habibos/result.py` — FOUND
- Commit `e1e19f2` (Task 1) — FOUND
- Commit `ad73727` (Task 2) — FOUND
- `test_rank_queue.py` — 4 passed (GREEN)
