---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
plan: 02
subsystem: engine
tags: [exec-05, cover-gate, conversion-gate, spend-up-guard, pure-predicate, refuse-never-default]
requires:
  - "engine/src/habibos/result.py (GateRefusal, ProposedAction typed grammar)"
  - "engine/config/thresholds.toml (days_of_cover_floor=42, conversion_benchmark=12 — set live by Plan 09-01)"
provides:
  - "engine/src/habibos/cover_gate.py — pure inventory+conversion spend-up gate: check(action, cover, conversion, floors) -> None | GateRefusal"
affects:
  - "the Phase-9 daily ranked queue (a spend-up proposal must clear this gate before reaching an operator)"
tech-stack:
  added: []
  patterns:
    - "pure predicate (structural twin of magnitude.py) — no socket, no I/O; the agent reads live cover/conversion via MCP and passes the numbers in (D-04)"
    - "refuse-never-default: a None floor REFUSES (no_threshold_set), the asymmetry vs magnitude's permissive-on-None seed"
    - "strict-breach-never-clamp: cover/conversion below floor surfaces the breaching value verbatim in breached_value, never rewritten to the floor"
    - "spend-direction-first: a spend-down auto-passes with no floor read (mirror gate.evaluate)"
key-files:
  created:
    - "engine/src/habibos/cover_gate.py"
  modified: []
decisions:
  - "Followed the EXECUTABLE CONTRACT (test_cover_gate.py) signature over the plan <action> prose where they diverged: floors are CALLER-supplied keyword args (days_of_cover_floor, conversion_benchmark) mirroring magnitude.check(action, cap), NOT read inside the gate via thresholds.read; and a clean PASS returns None (the magnitude.check positive grammar), NOT a GateVerdict. The plan's parallel-execution note explicitly granted signature authority ('mirror magnitude.check(action, floor)'). Branch-order semantics (spend-first, refuse-on-None-floor, strict-< breach, never-clamp, never-default) are identical between plan and test."
  - "No new dataclass added to result.py — reused GateRefusal; GateVerdict/ProposedAction not imported because the test contract returns None on pass (the gate computes no TACOS; the margin gate owns that math)."
metrics:
  duration: "~1 task, single GREEN commit (RED contract pre-existed on base)"
  completed: 2026-06-24
---

# Phase 9 Plan 02: Inventory + Conversion Spend-Up Gate Summary

EXEC-05 guardrail shipped: a hand-written, pytest-covered pure predicate (`cover_gate.check`) that hard-refuses any ad spend-UP onto a SKU below the 6-week stock-cover floor (D-03) or below the 12% conversion benchmark (D-05), surfacing the breaching value verbatim and never clamping it — auto-passing spend-downs and refusing on a missing floor or missing live number.

## What Was Built

`engine/src/habibos/cover_gate.py` (135 lines) — the structural twin of `magnitude.py` with `gate.evaluate`'s branch order:

```
check(action, days_of_cover, conversion_pct, days_of_cover_floor, conversion_benchmark) -> None | GateRefusal
```

Branch order (refuse, never clamp, never default):
1. spend-DOWN → PASS (None), no floor read (D-06 spend-direction-first).
2. `days_of_cover_floor is None` → `GateRefusal(no_threshold_set)` — refuse-never-default (D-03), never a default 42.
3. `days_of_cover is None` → `GateRefusal(no_cover_data)` — never assume cover (hard rule 4).
4. STRICT `days_of_cover < floor` → `GateRefusal(cover_below_floor, breached_value=cover, ceiling=floor)` — equal-to-floor passes; cover surfaced verbatim, never clamped to 42.
5. `conversion_benchmark is None` → `GateRefusal(no_threshold_set)` (D-05), never a default 12.
6. `conversion_pct is None` → `GateRefusal(no_conversion_data)`.
7. STRICT `conversion_pct < benchmark` → `GateRefusal(conversion_below_floor, breached_value=conversion, ceiling=benchmark)` — equal passes, never clamped.
8. both clear → PASS (None).

The engine opens NO socket: the live cover/conversion arrive as arguments the agent read via MCP (D-04); the operator floors arrive as arguments the caller read from `thresholds.read(...)`. This module only decides (CLAUDE.md hard rule 1: data layer is read-only; hard rule 3: money logic hand-written + tested).

## How It Was Verified

- `cd engine && uv run pytest tests/test_cover_gate.py -x -q` → **6 passed** (the Wave-1 RED contract turned GREEN). Covers: cover-below-floor never-clamps (breached_value verbatim), cover exactly 42 passes (strict `<`), conversion-below-benchmark refuses, missing floor → `no_threshold_set`, spend-down passes without reading a floor, and the named GG-0DC1 (1-FBA-unit) edge.
- `grep -nE "requests|urllib|http\.client|socket" src/habibos/cover_gate.py` → only docstring prose stating "opens NO socket" — **no network imports** (confirmed engine opens no socket).
- Full suite (excluding not-yet-built `test_queue.py` / parallel `test_rank_queue.py`): **58 passed, 5 skipped**, no regression. `result.py` untouched, so `test_gate`/`test_magnitude` unaffected.

## Deviations from Plan

### Contract-driven signature reconciliation (not a deviation rule — explicit plan grant)

The plan `<action>` text described `check(action, days_of_cover, conversion_pct, marketplace=None) -> GateVerdict | GateRefusal` reading the floors internally via `thresholds.read`. The Wave-1 executable contract (`test_cover_gate.py`, on the base commit) instead pins:
- floors as CALLER-supplied keyword args (`days_of_cover_floor`, `conversion_benchmark`) — mirroring `magnitude.check(action, cap)`,
- a clean PASS returning `None` (not a `GateVerdict`).

The plan's parallel-execution note explicitly granted signature authority ("The test's final predicate signature is yours to decide — mirror `magnitude.check(action, floor)` per the plan"). I followed the executable contract. The guardrail SEMANTICS (spend-direction-first, refuse-on-None-floor, strict-`<` breach, never-clamp, never-default) are identical to both the plan and the test. No new dataclass was added to `result.py`.

No auto-fixes (Rules 1-3) or architectural escalations (Rule 4) were needed; no auth gates occurred.

## Known Stubs

None. The gate is fully wired as a pure predicate; cover/conversion/floors are all caller-supplied per D-04 (the agent's MCP read is the data source by design, not a stub).

## Threat Coverage

All `mitigate` dispositions in the plan's `<threat_model>` are implemented:
- **T-09-02-01** (EoP, spend-up path) → `cover_below_floor`/`conversion_below_floor` hard refusals; equal-to-floor passes, strict breach refuses, value surfaced verbatim never clamped.
- **T-09-02-02** (Tampering, missing floor) → `thresholds.read` None → `GateRefusal(no_threshold_set)`, never a default 42/12.
- **T-09-02-03** (Spoofing, stale/missing live number) → cover/conversion None → `no_cover_data`/`no_conversion_data`; never assumes cover/conversion.
- **T-09-02-04** / **T-09-02-SC** (accepted) → no secret read, no socket, no package installs; the seller UUID never enters this module (verified by grep — no MCP I/O here).

No new security surface introduced beyond the plan's threat model.

## Self-Check: PASSED

- `engine/src/habibos/cover_gate.py` — FOUND
- commit `233630c` — FOUND (feat(09-02): add cover_gate.py)
- `test_cover_gate.py` — 6 passed (GREEN)
