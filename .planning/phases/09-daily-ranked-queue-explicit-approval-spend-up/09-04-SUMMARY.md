---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
plan: 04
subsystem: engine-queue-render
tags: [queue, renderer, class-tag, autonomy, tdd, D-01, D-02, D-07]
requires:
  - "09-01: test_queue.py RED contract"
  - "09-03: habibos.result.QueueRow (the typed row the renderer consumes)"
provides:
  - "habibos.queue.classify — action_type+match_type -> auto | needs-approval"
  - "habibos.queue.classify_row — class for a ranked QueueRow"
  - "habibos.queue.tag — set cls on rows, order preserved (no re-sort)"
  - "habibos.queue.render_row — per-row render dict (D-07 schema)"
  - "habibos.queue.render — one dollar-ranked, class-tagged table string"
affects:
  - "09-05 queue_run.py (calls queue.tag -> queue.render; auto-applies the auto class)"
tech-stack:
  added: []
  patterns:
    - "data-derived class flag via two reviewable frozensets (mirror ProposedAction.is_spend_increasing)"
    - "fail-safe default: unknown action_type -> needs-approval (never auto-apply an unmodeled action)"
    - "no-business-logic-in-render: render reads QueueRow fields only, computes no money/rank/class (mirror answer_tacos._serialize)"
    - "None expected estimate renders as em-dash, never 0"
key-files:
  created:
    - "engine/src/habibos/queue.py"
  modified: []
decisions:
  - "Implemented BOTH the binding test signatures (classify(action_type, match_type=None), render_row(...) -> dict) AND the plan/downstream signatures (classify_row(row), tag(rows), render(rows) -> str) so test_queue.py passes and 09-05's queue.tag->queue.render wiring works."
  - "negative match handled two ways: classify('negative', match_type='phrase'|'broad') -> needs-approval, exact/None -> auto; QueueRow.action_type 'negative_phrase'/'negative_broad' resolve to the same via _canonical."
  - "Executed INLINE by the orchestrator (sequential fallback) after the gsd-executor subagent spawn returned 529 Overloaded three times; same atomic-commit + SUMMARY contract honored on the main tree."
metrics:
  duration: ~10 min
  completed: 2026-06-24
  tasks: 1
  files: 1
---

# Phase 09 Plan 04: Queue Renderer + Reversibility Class-Tagger Summary

The pure renderer/class-tagger layer over `QueueRow`: tags each ranked row `auto` (standing
approval) or `needs-approval` (explicit approval) by action type + blast radius (D-01/D-02),
and renders the one dollar-ranked, class-tagged daily table (D-07). Turns Plan 01's
`test_queue.py` GREEN (4 passed). No money math, no re-ranking, no network — the ranking is
`rank_queue.py`'s, the money is the gate's, the class is the two frozensets'.

## What Was Built

**Task 1 — `queue.py` (`engine/src/habibos/queue.py`, commit `8ced80a`):**

- `classify(action_type, match_type=None) -> str` — the standalone tagger the test contract
  pins. Folds the `negative`+match_type form into a canonical action_type (`_canonical`),
  then looks it up in two reviewable frozensets:
  - `NEEDS_APPROVAL_ACTIONS = {bid_up, budget_up, harvest, negative_phrase, negative_broad}`
  - `AUTO_ACTIONS = {pause, bid_down, negative_exact, negative}`
  An UNKNOWN action_type returns `needs-approval` — fail-safe toward the human gate
  (T-09-04-01; an unmodeled action is never auto-applied).
- `classify_row(row: QueueRow) -> str` — class for a ranked row (its `action_type` already
  encodes the negative match).
- `tag(rows) -> list[QueueRow]` — rebuilds each frozen row via `dataclasses.replace(row,
  cls=classify_row(row))`, preserving the incoming dollar-ranked order (never re-sorts).
- `render_row(rank, sku, entity, action, current, proposed, expected_weekly_usd, provenance,
  match_type=None) -> dict` — the per-row render schema (the test contract): carries
  `rank, sku, entity, action, current, proposed, expected_weekly_usd, provenance, class`,
  with `class` derived via `classify`.
- `render(rows) -> str` — one markdown pipe table with the D-07 columns
  `rank | SKU | entity | action | current -> proposed | expected $/wk | provenance | class`,
  dollars-first / one screen. A `None` expected estimate renders as an em-dash (never 0);
  `current`/`proposed` of `None` likewise. Reads `row.cls` (set by `tag`) — computes no class.
- `__all__` exports the five callables plus the two frozensets.

## How It Maps to Requirements / must_haves

- **"Each ranked row is tagged auto or needs-approval by blast radius" (QUEUE-02)** — the two
  frozensets + `classify`; verified by `test_spend_up_tags_needs_approval`,
  `test_phrase_and_broad_negatives_tag_needs_approval`, `test_reversibles_tag_auto`.
- **"Spend-ups and phrase/broad negatives -> needs-approval; pauses/exact-negatives/bid-downs
  -> auto" (D-02)** — exact membership in the maps; phrase/broad negatives are NOT auto.
- **"The rendered queue is one dollar-ranked table with the D-07 columns" (QUEUE-01, D-07)** —
  `render` + `COLUMNS`; `render_row` schema asserted by `test_render_row_schema`.
- **"The renderer computes no money math" (D-04)** — `render` reads QueueRow fields and
  `row.cls` only; verified by the grep below returning nothing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Contract] Test signatures (`classify`, `render_row`) implemented alongside
the plan-prose signatures (`classify_row`, `tag`, `render`)**
- **Found during:** Task 1 (reading the RED contract `test_queue.py`).
- **Issue:** The binding test calls `queue.classify(action_type, match_type=None)` and
  `queue.render_row(rank, ...) -> dict` — NOT the plan's prose `classify_row(row)` /
  `render(rows) -> str`. But 09-05's wiring (`queue.tag(rows) -> queue.render(rows)`) and the
  must_haves (`contains: "def render"`, min_lines 50) need the plan-prose surface too.
- **Fix:** Implemented BOTH surfaces. `classify` is the primitive; `classify_row` delegates to
  it; `tag`/`render` are the list-level helpers 09-05 calls. The test is the binding contract
  (CLAUDE.md: "Tests are the contract").
- **Files modified:** `engine/src/habibos/queue.py`. **Commit:** `8ced80a`.

### Process deviation (not a code deviation)

This plan was executed **inline by the orchestrator** (the GSD sequential-execution fallback)
after the `gsd-executor` subagent spawn returned `529 Overloaded` three times with zero token
use. The same execute-plan contract was honored on the main working tree: atomic
implementation commit, then this SUMMARY, then orchestrator-owned tracking. No worktree was
used (single sequential plan), so there is no merge step.

## Verification

- `cd engine && uv run pytest tests/test_queue.py -q` -> **4 passed** (was RED on a missing
  import before this plan).
- `cd engine && grep -nE "requests|urllib|http\.client|socket|/100|\* 100|round\(" src/habibos/queue.py`
  -> **nothing** (no network, no money math in the renderer).
- `cd engine && uv run pytest -q` -> **67 passed, 5 skipped** — the full suite is now GREEN
  (all three Wave-1 RED contracts — cover_gate, rank_queue, queue — are green; the only
  remaining RED is the Wave-4 harvest/queue_run contract, not yet built). `test_env.py`
  passes in the primary checkout (the `.env` worktree artifact does not apply inline).

## Threat Surface

The plan's `<threat_model>` dispositions are satisfied: T-09-04-01 (spend-ups + phrase/broad
negatives gated to needs-approval; unknown action_type fails safe to needs-approval — both
asserted), T-09-04-02 (render computes no money/rank/class — grep-verified), T-09-04-03 (the
table prints provenance only; no seller UUID is a QueueRow field). No package installs
(T-09-04-SC accept).

## Known Stubs

None. The renderer is complete; `render` reads `row.cls` set by `tag`, so the class shown is
always the tagged class.

## Self-Check: PASSED

- `engine/src/habibos/queue.py` — FOUND (171 lines; contains `def render`, `def classify`, `def tag`)
- Commit `8ced80a` (Task 1) — FOUND
- `test_queue.py` — 4 passed (GREEN)
- Full engine suite — 67 passed, 5 skipped
- Grep verification (no network / no money math) — clean
