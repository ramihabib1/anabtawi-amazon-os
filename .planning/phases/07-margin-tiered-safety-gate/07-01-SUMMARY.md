---
phase: 07-margin-tiered-safety-gate
plan: 01
subsystem: margin-gate-contracts-and-red-baseline
tags: [money-logic, anti-fabrication, gate, typed-results, pytest, red-baseline, tdd]
requires:
  - "habibos.result — Refusal/Proceed/PollOutcome frozen-dataclass grammar + PREMIUM_SOURCE (Plan 02-01)"
  - "habibos.tacos.parse — window-sum reader reused by test_gate fixture wiring (Plan 02-02)"
  - "tests/fixtures/profit_by_sku_30d.csv — committed window-sum export fixture (Plan 02)"
provides:
  - "habibos.result.ProposedAction — pure-data write proposal w/ is_spend_increasing property"
  - "habibos.result.GateRefusal — typed gate refusal naming breached_value/ceiling/source (GATE-04)"
  - "habibos.result.GateVerdict — typed PASS, never a bare True (mirror of Proceed)"
  - "tests/test_gate.py — RED contract for GATE-01..05 + D-03/D-04 (Nyquist baseline for Plan 03)"
  - "repointed test_thresholds.py empty-key assertion + seeded-floor lock"
affects:
  - "07-03 gate.py implements contribution_margin_pct/ceiling_tacos_pct/projected_tacos_pct/evaluate against these tests"
  - "07-02 seeds min_net_margin_pct=15 (turns the staged seeded-floor lock GREEN) and creates tests/fixtures/sku_catalog_test.toml"
  - "07-04 CLI (gate_action.py) wires gate.evaluate -> JSON, importing the result.py gate types"
tech-stack:
  added: []
  patterns:
    - "Frozen-dataclass typed results (sibling of Refusal/Proceed) — immutable verdicts, never a bare True/None"
    - "GateRefusal carries breached_value+ceiling+source so a breach can never be silently rewritten as a clamp (T-07-01)"
    - "Pre-ad back-out asserted against committed fixture arithmetic (CM% 36.0) — anti-fabrication (T-07-02)"
    - "RED-first: tests import the future habibos.gate API; fail on the absent module (Nyquist baseline)"
    - "Strict > breach semantics (projected == ceiling PASSES) cloned from tacos._present_flag"
key-files:
  created:
    - .planning/phases/07-margin-tiered-safety-gate/07-01-SUMMARY.md
    - engine/tests/test_gate.py
  modified:
    - engine/src/habibos/result.py
    - engine/tests/test_thresholds.py
decisions:
  - "ProposedAction/GateRefusal/GateVerdict added to result.py (not gate.py) — D-08 discretion; keeps all typed siblings in one trust-spine module"
  - "Unreliable-COGS refusal (D-04) is exercised via total_sales_sum == 0 fixture rows (9Z-KUHZ-FU2I, ASW-H50); the catalog-cogs==0 cross-check is Plan 02's TEST_CATALOG (sku_catalog_test.toml)"
  - "Unset-floor refusal (GATE-02/SC-2) exercised via marketplace='XX' (no floor) — same None-ceiling trick test_tacos.py uses — independent of the live seeded 15"
  - "gate.evaluate(frame, ProposedAction, catalog_path, marketplace=...) signature pinned by the tests; Plan 03 implements against it"
metrics:
  duration_min: 6
  completed: 2026-06-21
  tasks: 3
  files_created: 2
  files_modified: 2
---

# Phase 7 Plan 01: Margin-Gate Contracts and RED Baseline Summary

The Wave 0 scaffold for the margin-tiered safety gate: three frozen-dataclass typed
contracts (`ProposedAction`, `GateRefusal`, `GateVerdict`) added to `habibos.result`
alongside the existing `Refusal`/`Proceed`, plus a seven-function RED `test_gate.py` that
pins the gate's behavior (GATE-01..05 + the D-03 pre-ad back-out and D-04 unreliable-COGS
edges) before any implementation — and one repointed `test_thresholds.py` assertion that
stages the Wave 1 → Wave 2 seeded-floor dependency signal.

## What Was Built

**Task 1 — Gate types in `result.py`** (`eed0fc2`)
- `ProposedAction(sku, action_type, delta_spend, marketplace="CA")` with an
  `is_spend_increasing` property returning `delta_spend > 0`. `delta_spend` is
  caller-computed (Open Q3) — the gate treats it as given.
- `GateRefusal(reason, code, breached_value=None, ceiling=None, source=None)` — the
  sibling of `Refusal` that carries the three extra provenance fields GATE-04 needs to
  *name the breached number and its source*, so a breach can never be silently rewritten
  as a clamp (T-07-01). The four `code` values
  (`no_threshold_set` | `no_margin` | `sku_not_in_catalog` | `over_ceiling`) are
  documented on the class.
- `GateVerdict(projected_tacos, ceiling, contribution_margin, auto_pass=False)` — the
  typed PASS, never a bare `True` (mirror of `Proceed`). `auto_pass=True` /
  `projected_tacos=None` is the spend-decreasing branch (D-06).
- All three are `@dataclass(frozen=True)`; the existing `Refusal`, `Proceed`,
  `PollOutcome`, `SkuRow`, `Answer` definitions and the reused `PREMIUM_SOURCE` constant
  are unchanged. No per-SKU margin is stored anywhere (D-04: margin is computed live in
  Plan 03).
- Verify: `... ProposedAction(...).is_spend_increasing` prints `True False`, exit 0.

**Task 2 — RED `test_gate.py` contract** (`e18585b`)
- Mirrors `test_tacos.py`'s fixture-driven layout: same
  `REPO_ROOT = Path(__file__).resolve().parent.parent`,
  `FIXTURE = REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"`, and a `_frame()`
  helper calling `tacos.parse(FIXTURE, "COMPLETED")`. Imports the future gate API
  (`from habibos import gate`) and the types from `habibos.result`.
- Seven failing test functions (names are the contract):
  - `test_contribution_margin_pre_ad` (GATE-01) — `gate.contribution_margin_pct` from
    window sums with `ad_spend_sum` added back; `None` on zero/missing denominator.
  - `test_profit_is_post_ad_addback` (D-03) — asserts EU-Z87B-ZRBZ CM% ==
    `(100.27 + 0.5)/279.95*100` == **36.0**, and that this differs from the naive
    `profit/sales`, proving the back-out (anti-fabrication, T-07-02).
  - `test_ceiling_and_unset_floor_refuses` (GATE-02) — `ceiling_tacos_pct(36.0, 15.0) ==
    21.0`; a spend-up under `marketplace="XX"` (no floor) returns
    `GateRefusal(code="no_threshold_set")`.
  - `test_spend_direction_branch` (GATE-03) — a spend-increasing action under the ceiling
    returns a `GateVerdict` (`auto_pass=False`, `projected_tacos <= ceiling`); a
    spend-decreasing action returns `GateVerdict(auto_pass=True, projected_tacos=None)`.
  - `test_breach_refuses_never_clamps` (GATE-04) — an over-ceiling spend-up returns
    `GateRefusal(code="over_ceiling")` whose `breached_value` equals the projected TACOS
    (not a clamped ceiling), `breached_value > ceiling`, and `source` is set.
  - `test_sku_not_in_catalog_refuses` (GATE-05) — a SKU absent from the catalog returns
    `GateRefusal(code="sku_not_in_catalog")`.
  - `test_unreliable_cogs_refuses` (D-04) — `9Z-KUHZ-FU2I` and `ASW-H50` (both
    `total_sales_sum == 0`) return `GateRefusal(code="no_margin")`.
- Strict `>` breach semantics throughout (projected exactly at the ceiling PASSES).
- The tests reference `tests/fixtures/sku_catalog_test.toml` by its constant path
  (`TEST_CATALOG`) — created in Plan 02 — so they fail RED on the absent gate module, not
  on a typo. Pinned gate signature: `gate.evaluate(frame, ProposedAction, catalog_path,
  marketplace=...)` plus the three helper functions.

**Task 3 — Repoint `test_thresholds.py` off the renamed key** (`45785b5`)
- In `test_missing_threshold_returns_none`, changed the first assertion from
  `read("min_margin_pct", "CA") is None` to `read("days_of_cover_floor", "CA") is None`
  (the key that stays empty `""` after Plan 02 seeds `min_net_margin_pct = 15`), so the
  empty-refusal path stays covered. The absent-key and absent-marketplace assertions are
  unchanged.
- Added `assert thresholds.read("min_net_margin_pct", "CA") == 15.0` to lock the seeded
  floor. This assertion is **intentionally RED until Plan 02 seeds the key** — the
  Wave 1 → Wave 2 dependency signal.
- `thresholds.py` itself is untouched (its refuse-on-empty contract is unchanged).

## Intentionally RED (expected, by design)

Per the plan's output note, two RED states are intended, not failures:

1. **`tests/test_gate.py` — entirely RED** (collection error: `cannot import name 'gate'
   from 'habibos'`). `habibos.gate` does not exist until Plan 03. This IS the Nyquist
   baseline — the seven tests are the contract Plan 03's `gate.py` is written test-first
   against.
2. **`test_thresholds.py::test_missing_threshold_returns_none` — one RED assertion**
   (`assert None == 15.0`). The repointed `days_of_cover_floor` / absent-key /
   absent-marketplace lines pass; only the new `min_net_margin_pct == 15.0` lock fails,
   pending Plan 02 seeding the floor in `thresholds.toml`.

## Deviations from Plan

None — plan executed exactly as written. The `gate.evaluate` signature and helper-function
names were pinned from RESEARCH §Code Examples + PATTERNS lines 50-74 (Claude's discretion
on argument order, within the plan's stated contract); Plan 03 implements against them.

## Deferred Issues

None.

## Verification Evidence

- `cd engine && uv run python -c "from habibos.result import ProposedAction, GateRefusal,
  GateVerdict; ..."` → prints `True False`, exit 0 (Task 1 verify).
- `cd engine && uv run pytest tests/test_gate.py -q` → RED, collection error on absent
  `habibos.gate` (the `RED-OK` grep matched `ImportError`). Intended Wave 1 baseline.
- `cd engine && uv run pytest tests/test_thresholds.py::test_missing_threshold_returns_none
  -q` → 1 failed, and the failure is precisely line 40 (`assert None == 15.0`), confirming
  the three preceding repointed assertions pass and only the staged seeded-floor lock is
  RED (Plan 02 dependency).
- `grep -rn 'read("min_margin_pct"' tests/` → empty (renamed key no longer referenced).
- Pre-existing `test_env.py::test_seller_id_in_env_not_code` fails only in the bare
  worktree (gitignored `.env` not copied) — not a regression from this plan; documented
  identically in prior SUMMARYs.

## Threat Model Coverage

| Threat ID | Disposition | Where mitigated |
|-----------|-------------|-----------------|
| T-07-01 (a breach silently rewritten as a clamp) | mitigate | `GateRefusal` is a frozen dataclass carrying `breached_value`+`ceiling`+`source`; `test_breach_refuses_never_clamps` asserts `isinstance(result, GateRefusal)`, `breached_value == projected` (not the ceiling), and `not isinstance(result, GateVerdict)` |
| T-07-02 (fabricated margin passing review) | mitigate | `test_profit_is_post_ad_addback` asserts the back-out arithmetic (CM% 36.0) against the committed fixture and that it differs from naive `profit/sales` |
| T-07-SC (package installs) | accept | No package installs in this plan — all deps (polars, pydantic, tomllib, pytest) already pinned and prior-audited; slopcheck N/A |

## Known Stubs

None introduced. `test_gate.py` deliberately fails RED (the absent `habibos.gate` module is
implemented in Plan 03) and references `tests/fixtures/sku_catalog_test.toml` (created in
Plan 02) — these are documented Wave-boundary dependencies, not unfinished stubs. The new
result-types are fully functional and import cleanly today.

## Self-Check: PASSED

- Created files present: `engine/tests/test_gate.py`, `07-01-SUMMARY.md` — FOUND.
- Modified files present: `engine/src/habibos/result.py`, `engine/tests/test_thresholds.py` — FOUND.
- Commits present in git history: `eed0fc2` (Task 1), `e18585b` (Task 2), `45785b5` (Task 3) — FOUND.
