---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
plan: 05
subsystem: engine-queue-orchestrator
tags: [queue, harvest, attribution, spend-up, apply-spine, checkpoint-deferred, D-06, D-08, D-09, D-10, D-11]
requires:
  - "09-02 cover_gate.check, 09-03 rank_queue.rank + QueueRow, 09-04 queue.tag/render/classify"
  - "Phase-8 apply.apply spine (unchanged), Phase-7 gate.evaluate"
provides:
  - "habibos.harvest — is_matured / is_act_now / judge_later_blocked / consolidation_blocked / graduates"
  - "scripts/queue_run.py — daily ranked-queue CLI (render auto-applies reversibles; apply --approve fires a gate-passed spend-up)"
  - ".claude/skills/ppc-analysis SKILL — daily-queue operating-rhythm section"
affects:
  - "the standing daily PPC operating rhythm; the first live mutating spend-up (DEFERRED — see below)"
tech-stack:
  added: []
  patterns:
    - "pure typed predicates reusing result.GateRefusal (no new dataclass)"
    - "thin wiring CLI mirroring apply_action.py/gate_action.py — no business logic, opens no network, no seller UUID"
    - "render mode runs the read-only gate chain then auto-applies auto-class rows via apply.apply UNCHANGED; needs-approval waits for --approve (D-06)"
key-files:
  created:
    - "engine/src/habibos/harvest.py"
    - "engine/tests/test_harvest.py"
    - "engine/scripts/queue_run.py"
    - "engine/tests/test_queue_run.py"
    - "engine/tests/fixtures/queue_cover_map.json"
  modified:
    - ".claude/skills/ppc-analysis/SKILL.md"
decisions:
  - "Tasks 1/2/4 (code + tests + doc) executed INLINE by the orchestrator after the gsd-executor subagent spawn returned 529 Overloaded 4x; same atomic-commit contract honored on main."
  - "Task 3 (checkpoint:human-verify — the first LIVE mutating spend-up) DEFERRED to a focused session by Rami's explicit choice, on two material findings surfaced live (below). Phase 9 is CODE-COMPLETE; the live first-write is the one outstanding item."
  - "queue_run wires the ACTUAL Wave-2/3 signatures (cover_gate.check with caller-supplied floors; rank_queue.rank(path); queue.tag/render), not the plan's prose interfaces — the modules/tests are the contract."
metrics:
  duration: ~live session
  completed: 2026-06-24
  tasks: "3 of 4 (1,2,4 done; 3 deferred)"
  files: 6
---

# Phase 09 Plan 05: Daily Ranked Queue Wire-Up — Summary (Task 3 live write DEFERRED)

The daily ranked queue is **code-complete and pytest-green**, and the DataDoe write path is
**verified live**. The plan's one human-gated step — Task 3, the first real mutating spend-up
against the live Amazon account — was **deferred to a focused session by Rami's explicit
decision**, on material findings that surfaced when the live path was opened.

## What Was Built (Tasks 1, 2, 4 — complete)

**Task 1 — `engine/src/habibos/harvest.py` + `test_harvest.py` (commit `baf0862`, 11 passed):**
Five pure predicates reusing `result.GateRefusal` (no new dataclass): `is_matured`
(SP≥7d, SB/SD≥14d; unknown product fail-safe not matured), `is_act_now` (inactive listing /
zero lifetime orders / enabled-on-discontinued bypass the maturity wait), `judge_later_blocked`
(efficiency verdict on an immature window → `immature_window` refusal, days surfaced never
clamped — D-10, the #1 pitfall), `consolidation_blocked` (a bid-up on a term live in >1 ENABLED
campaign → `internal_competition`, names the lowest-ACOS owner to keep — D-08), `graduates`
(≥2 orders AND acos ≤ ceiling — D-09).

**Task 2 — `engine/scripts/queue_run.py` + `test_queue_run.py` + `queue_cover_map.json`
(commit `dd7dbad`, 5 passed):** A thin wiring CLI mirroring `apply_action.py`/`gate_action.py`
(no business logic, opens no network, no seller UUID — grep-clean). `render` mode ranks → tags
→ renders the dollar-ranked table, runs the read-only gate chain on each spend-up
(margin `gate.evaluate` → `cover_gate.check` → `harvest.judge_later_blocked` →
`harvest.consolidation_blocked`) and annotates refusals, and **auto-applies each auto-class
reversible via `apply.apply` UNCHANGED** (a real spine call — verified by an `apply.apply` spy);
a needs-approval row is never auto-applied. `apply --approve` fires a gate-passed spend-up
through the Phase-8 spine (over-ceiling refused, not clamped, D-11); without `--approve` it
refuses any needs-approval row (D-06 batch gate).

**Task 4 — `ppc-analysis` SKILL daily-queue operating-rhythm section (commit `ba9a399`):**
Documents the on-open/on-demand queue, the live reads (+ DataDoe export fallback), class-based
autonomy (reversibles auto-apply; spend-ups wait for `--approve`), the full spend-up gate chain,
and refuse-not-clamp.

**Full engine suite: 83 passed, 5 skipped** — all three Wave-1 RED contracts + the two new
09-05 contracts are GREEN; no regression.

## Task 3 — Live first-write: DEFERRED (the one outstanding item)

Rami approved the live run and confirmed the org-enable. On opening the live path, two material
findings changed the picture and Rami chose to **defer the first real write to a focused
session** (the recommended option):

1. **DataDoe write path verified LIVE (read-only proof).** `AMAZON_ADS_CAMPAIGNS_FIND`
   completed in <1s (actionId `c20389c3…`); `actions_list` shows **5 actions ever, all
   FINDs — zero mutating writes have ever landed** (consistent with "0 real writes"). 16
   ENABLED Sponsored Products campaigns, almost all $10/day (one $5/day), most `SALES_DOWN_ONLY`.
2. **agentcentral is expired** (`trial_expired`; Seller Central + Amazon Ads both `missing`
   for CA) → the plan's named live-read tools (`get_days_of_cover`, etc.) are unavailable;
   reads must come from DataDoe exports.
3. The 2026-06-16 "funded winners" are mostly **new-campaign** proposals (`CAMPAIGNS_ADD` =
   Phase-10, held; several already built). A clean Phase-9 spend-up is a `budget_up`/`bid_up`
   on an existing enabled winner that the margin + cover gate pass — which needs **current**
   matured ACOS + **current** days-of-cover. The only cached cover file is `top5, 2026-06-02`
   (~3 weeks stale; unsafe to gate GG-0DC1's sub-cover refusal on).

### To complete Task 3 (focused session)
Pull a fresh **FBA Inventory Health** (cover) + matured **ad-campaign performance** (ACOS,
spend-vs-budget) export → run the engine gate over the 16 enabled campaigns → `queue_run.py
render` the live dollar-ranked table (confirm a sub-cover SKU renders REFUSED) → dryRun the
best gate-passed `budget_up` → show Rami the exact raise → `queue_run.py apply --approve` →
poll COMPLETED + `*_FIND` echo → log to `state/decisions.md` + `brain/raw`. Also demonstrate an
over-ceiling raise refused-not-clamped.

## Verification

- `cd engine && uv run pytest -q` → **83 passed, 5 skipped** (full suite green).
- `grep -nE "requests|urllib|http\.client|socket|fetch" scripts/queue_run.py src/habibos/harvest.py` → nothing.
- `grep -rnE "AMAZON_CA_SELLER_ID|seller_id|sellerId" scripts/queue_run.py` → nothing.
- DataDoe write path reachability confirmed live (FIND COMPLETED); no mutating write made.

## Outstanding (human / live)
- **Task 3 live first-write** — deferred to a focused session (above). Phase-9 verification
  of the *live* goal (one gate-passed spend-up reconciled; GG-0DC1 refused sub-cover;
  over-ceiling refused-not-clamped) is pending that session.

## Self-Check: PASSED (code) · DEFERRED (live Task 3)

- `engine/src/habibos/harvest.py` — FOUND · `engine/scripts/queue_run.py` — FOUND
- Commits `baf0862` (harvest) · `dd7dbad` (queue_run) · `ba9a399` (SKILL) — FOUND
- `test_harvest.py` 11 passed · `test_queue_run.py` 5 passed · full suite 83 passed
- Task 3 live write — deliberately DEFERRED (not executed); no account change made
