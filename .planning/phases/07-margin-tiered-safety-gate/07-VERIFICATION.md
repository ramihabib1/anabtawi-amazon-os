---
phase: 07-margin-tiered-safety-gate
verified: 2026-06-22T00:00:00Z
status: passed
score: 7/7 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 7: Margin-Tiered Safety Gate — Verification Report

**Phase Goal:** A per-SKU margin-tiered TACOS safety gate that protects net margin >= ~15% (NOT a flat 25%), refuses any spend-increase that would push net margin below the floor, surfaces typed refusals (never silent defaults / clamps), and is hand-written + pytest-covered (money-truth layer). The gate must be invocable as a CLI emitting typed JSON, ready for the Phase 8 apply spine to consume.

**Verified:** 2026-06-22
**Status:** GOAL MET — all 7 must-haves verified
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `gate.py` implements `contribution_margin_pct` with D-03 ad-spend add-back (profit is POST-ad) | VERIFIED | `gate.py` line 73: `round((profit_sum + ad_spend_sum) / total_sales_sum * 100, 1)`; `test_profit_is_post_ad_addback` asserts CM% 36.0 differs from naive profit/sales 35.8; test PASSES |
| 2 | `gate.py` implements `ceiling_tacos_pct` as CM% - single floor (D-01a, no per-tier table) | VERIFIED | `gate.py` line 83: `round(cm_pct - floor, 1)`; `thresholds.toml` carries one `min_net_margin_pct = 15` under `[marketplace.CA]`; `test_ceiling_and_unset_floor_refuses` asserts 36.0 - 15.0 = 21.0 PASSES |
| 3 | `gate.py` implements `projected_tacos_pct` as worst-case hold-flat projection (D-06) | VERIFIED | `gate.py` lines 97-101: `(ad_spend_sum + delta_spend) / total_sales_sum * 100`; zero-sales -> None; runtime spot-check confirms delta=1000 projects 357.4 |
| 4 | `gate.evaluate()` returns typed refusals (never clamps, never silent defaults) for: `over_ceiling`, `no_margin`, `sku_not_in_catalog`, `no_threshold_set` | VERIFIED | `evaluate()` branch order documented in docstring and implemented in lines 150-238; `test_breach_refuses_never_clamps` asserts `isinstance(result, GateRefusal)` AND `breached_value == projected` (not ceiling) AND `not isinstance(result, GateVerdict)`; all 7 `test_gate.py` tests PASS |
| 5 | `min_net_margin_pct = 15` seeded in `thresholds.toml`; missing/empty threshold returns refusal, never a default | VERIFIED | `thresholds.toml` line 33: `min_net_margin_pct = 15`; `thresholds.read("min_net_margin_pct","CA")` returns `15.0`; `thresholds.read("min_net_margin_pct","XX")` returns `None`; gate branch 6 in `evaluate()` converts None -> `GateRefusal(code="no_threshold_set")` |
| 6 | `sku_catalog.toml` is the machine-readable source of truth (per-SKU tier+COGS, no stored margin); absent SKU -> `sku_not_in_catalog` | VERIFIED | `sku_catalog.toml` contains 16 SKUs (each with `asin`, `tier`, `cogs`; no computed margin); `_load_catalog()` raises `FileNotFoundError` on missing file (never silent fallback); `test_sku_not_in_catalog_refuses` PASSES; 14 absent-COGS SKUs are intentionally omitted (Rami's conservative decision, documented in 07-02-SUMMARY) |
| 7 | `gate_action.py` is a thin CLI (no money math in script), emits typed JSON, invocable from Phase 8 apply spine; spend-DOWN auto-passes | VERIFIED | CLI has zero inline math (grep confirms no round/ratio/CM terms); `argv -> gate.parse + gate.evaluate -> dataclasses.asdict -> JSON stdout`; spend-down: `{"auto_pass": true, "projected_tacos": null}`; over-ceiling: `{"code": "over_ceiling", "breached_value": 357.4, "ceiling": 21.0, "source": "DataDoe premium..."}` with exit code 0; 3/3 `test_gate_action.py` tests PASS |

**Score:** 7/7 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/src/habibos/gate.py` | Four functions + evaluate(), 238 lines | VERIFIED | Exists; substantive (not stub); imported by test_gate.py and gate_action.py; all exports wired |
| `engine/src/habibos/result.py` | ProposedAction, GateRefusal, GateVerdict as frozen dataclasses | VERIFIED | All three present as `@dataclass(frozen=True)`; correct field shapes; `is_spend_increasing` property works |
| `engine/scripts/gate_action.py` | Thin CLI wrapping gate.evaluate, no money math | VERIFIED | 107 lines, zero inline arithmetic; mirrors `answer_tacos.py` pattern |
| `engine/tests/test_gate.py` | 7 tests covering GATE-01..05 + D-03/D-04 | VERIFIED | All 7 functions present and passing GREEN |
| `engine/tests/test_gate_action.py` | 3 CLI contract tests | VERIFIED | All 3 functions present and passing GREEN |
| `engine/config/thresholds.toml` | `min_net_margin_pct = 15` under `[marketplace.CA]` | VERIFIED | Key present; `thresholds.read("min_net_margin_pct","CA")` returns `15.0` |
| `engine/config/sku_catalog.toml` | 16 SKUs with asin/tier/cogs (no stored margin) | VERIFIED | Present; 16 entries; no pre-computed margin fields; policy header documents intent |
| `engine/tests/fixtures/sku_catalog_test.toml` | Edge-case catalog for gate refusal tests | VERIFIED | Present; contains HERO (valid cogs), ZZ-ZERO-COGS0 (cogs=0), deliberately omits NX-NOTIN-CAT0 |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `test_gate.py` | `habibos.gate` | `from habibos import gate` | WIRED | All 7 tests call gate.contribution_margin_pct, gate.ceiling_tacos_pct, gate.evaluate |
| `test_gate.py` | `habibos.result` | `from habibos.result import GateRefusal, GateVerdict, ProposedAction` | WIRED | Used in every test for isinstance assertions |
| `gate_action.py` | `habibos.gate` | `from habibos import gate` | WIRED | gate.parse + gate.evaluate called in main() |
| `gate_action.py` | `habibos.result` | `from habibos.result import GateRefusal, GateVerdict, ProposedAction, Refusal` | WIRED | Used for isinstance dispatch and dataclasses.asdict |
| `gate.py` | `habibos.thresholds` | `from . import thresholds` | WIRED | `thresholds.read("min_net_margin_pct", mkt)` in evaluate() branch 6 |
| `gate.py` | `habibos.tacos` | `from .tacos import PREMIUM_SOURCE_ID, parse` | WIRED | Re-exports parse; uses PREMIUM_SOURCE_ID for logged_call |
| `gate.py` | `engine/config/sku_catalog.toml` | `_load_catalog(catalog_path)` via `tomllib` | WIRED | Explicit file read; missing file raises, never silent fallback |

---

## Data-Flow Trace (Level 4)

The gate is not a rendering component — it is a pure-computation money module. The data flows verified instead are:

| Function | Input Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `contribution_margin_pct` | `profit_sum`, `ad_spend_sum`, `total_sales_sum` | `tacos.parse()` (polars DataFrame from DataDoe premium export fixture) | Yes — round arithmetic, None on zero-denominator | FLOWING |
| `ceiling_tacos_pct` | `cm_pct`, `floor` | CM% from above; `thresholds.read("min_net_margin_pct", mkt)` | Yes — single subtraction, no default | FLOWING |
| `projected_tacos_pct` | `ad_spend_sum`, `delta_spend`, `total_sales_sum` | Frame row + ProposedAction.delta_spend | Yes — worst-case hold-flat projection | FLOWING |
| `evaluate()` | `frame`, `action`, `catalog_path`, `marketplace` | parse output, ProposedAction, toml catalog, thresholds.toml | Yes — typed GateVerdict or GateRefusal on all branches | FLOWING |

No stub returns. No hardcoded empty data sources. Every None return is a deliberate "undefined signal" (zero-denominator), not a placeholder.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full pytest suite green | `uv run pytest -q` | 36 passed, 5 skipped in 0.28s | PASS |
| Gate tests (10) all pass | `uv run pytest tests/test_gate.py tests/test_gate_action.py -v` | 10 passed in 0.22s | PASS |
| CM% add-back arithmetic | `contribution_margin_pct(100.27, 0.5, 279.95)` | 36.0 (differs from naive 35.8) | PASS |
| Ceiling formula | `ceiling_tacos_pct(36.0, 15.0)` | 21.0 | PASS |
| Spend-down auto-pass (CLI) | `gate_action.py --delta-spend -5.0` | `{"auto_pass": true, "projected_tacos": null}` | PASS |
| Over-ceiling refusal (CLI) | `gate_action.py --delta-spend 1000.0` | `{"code": "over_ceiling", "breached_value": 357.4, "ceiling": 21.0, "source": "DataDoe..."}` | PASS |
| No threshold set refusal | `thresholds.read("min_net_margin_pct", "XX")` -> None in evaluate() | `GateRefusal(code="no_threshold_set")` | PASS |
| CLI exit code | `gate_action.py --delta-spend -5.0 > /dev/null; echo $?` | 0 | PASS |
| CLI has no inline math | `grep -E "round\(|/ total_sales|profit_sum|\* 100" gate_action.py` | no matches | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GATE-01 | 07-01, 07-03 | Pre-ad contribution margin from window sums | SATISFIED | `contribution_margin_pct` adds back `ad_spend_sum`; asserted by `test_contribution_margin_pre_ad` and `test_profit_is_post_ad_addback` |
| GATE-02 | 07-01, 07-03 | Ceiling = CM% - floor; unset floor refuses every spend-up | SATISFIED | `ceiling_tacos_pct` function + evaluate() branch 6; `test_ceiling_and_unset_floor_refuses` PASSES |
| GATE-03 | 07-01, 07-03, 07-04 | Spend-direction branch: spend-down auto-passes | SATISFIED | evaluate() branch 1; `test_spend_direction_branch` and `test_cli_spend_down_emits_auto_pass` PASS |
| GATE-04 | 07-01, 07-03, 07-04 | Over-ceiling spend-up refuses (never clamps); breached_value + source named | SATISFIED | evaluate() branch 7 returns `GateRefusal(code="over_ceiling", breached_value=projected...)`; `test_breach_refuses_never_clamps` asserts is GateRefusal, not GateVerdict; `test_cli_over_ceiling_emits_refusal` asserts `"auto_pass" not in payload` |
| GATE-05 | 07-01, 07-02, 07-03, 07-04 | SKU absent from catalog -> `sku_not_in_catalog` refusal | SATISFIED | evaluate() branch 3; `sku_catalog.toml` + `sku_catalog_test.toml` as machine-readable authority; `test_sku_not_in_catalog_refuses` and `test_cli_absent_sku_emits_refusal` PASS |
| D-01 / D-01a | 07-02, 07-03 | One floor, no per-tier table; `min_net_margin_pct = 15` | SATISFIED | `thresholds.toml` comment explicitly states "no per-tier ceiling table"; single `min_net_margin_pct = 15` key |
| D-03 | 07-01, 07-03 | Pre-ad back-out: profit_sum is POST-ad; add_spend_sum added back | SATISFIED | `test_profit_is_post_ad_addback` asserts 36.0 != naive 35.8 using the committed fixture |
| D-04 | 07-01, 07-03 | Unreliable/zero COGS or zero-sales -> `no_margin`; no guessed margin | SATISFIED | evaluate() branches 2, 4; `test_unreliable_cogs_refuses` PASSES for both NOSALES SKUs |
| D-05 | 07-02, 07-03 | Explicit catalog; absent SKU refuses; no silent export-rows fallback | SATISFIED | `_load_catalog()` raises on missing file; evaluate() branch 3 checks catalog membership |
| D-06 | 07-03 | Worst-case projection: sales held flat; spend-decrease bypasses gate entirely | SATISFIED | `projected_tacos_pct` holds sales flat; evaluate() branch 1 returns auto_pass before any catalog or config read |
| D-07 / D-08 | 07-02, 07-03 | Missing threshold -> refusal, never default; no clamping | SATISFIED | evaluate() branch 6 returns GateRefusal on None floor; GATE-04 test confirms breach returns refusal not clamped GateVerdict |

---

## Anti-Patterns Found

No blockers found. Full scan of all 8 phase-modified files:

| File | Pattern Searched | Result |
|------|-----------------|--------|
| `gate.py` | TBD/FIXME/XXX/TODO/HACK/placeholder, return null/[]/{}  | Clean |
| `result.py` | Same | Clean |
| `gate_action.py` | Same + inline math | Clean — no arithmetic in CLI |
| `test_gate.py` | Same | Clean |
| `test_gate_action.py` | Same | Clean |
| `thresholds.toml` | Same | Clean |
| `sku_catalog.toml` | Same | Clean |
| `test_thresholds.py` | Same | Clean |

**Pre-existing `min_margin_pct` in `test_config_seed.py`:** This references the Phase 1 Supabase `config` table schema key (DATA-04 contract), is SKIP-gated on `SUPABASE_DB_URL`, and is not a reference to the `thresholds.toml` key renamed by this phase. Out of scope per the stated known/accepted context. Not flagged.

**5 skipped tests:** Pre-existing Supabase/context gates from Phase 1 (`test_config_seed`, `test_context`, `test_schema` x3). Not regressions; consistent across phases.

---

## Known / Accepted Context (Not Flagged as Gaps)

- **16-SKU catalog coverage** (vs ~30 active SKUs): intentional. Only SKUs with both a tier (rollup authority) and a reviewed landed COGS are included. Absent SKUs refuse-on-funding with `sku_not_in_catalog`. Rami's conservative decision recorded in 07-02-SUMMARY.md. Correct surfaced behavior.
- **`test_config_seed.py` `min_margin_pct`**: Phase 1 Supabase DATA-04 schema key; SKIP-gated; unrelated to `thresholds.toml` rename. Left intact intentionally (renaming it would alter the Phase 1 DATA-04 seed contract).
- **`gate.evaluate` signature is `(frame, action, catalog_path, marketplace=None)`** (frame-first): matches the committed test contract; documented deviation from plan prose in 07-03-SUMMARY.

---

## Human Verification Required

None. All gate behaviors are deterministic pure functions or file I/O, fully verifiable programmatically. No UI, no real-time behavior, no external service integration tested in this phase.

---

## Verdict

**GOAL MET.**

Phase 7 delivers a complete, hand-written, pytest-covered per-SKU margin-tiered TACOS safety gate. Every capability in the phase goal is present and verified:

1. `gate.py` computes pre-ad contribution margin (D-03 add-back), per-SKU ceiling (D-01a single floor), and worst-case projection (D-06) — all as pure typed functions, no prose math, no inline computation in the CLI.
2. `evaluate()` returns typed `GateVerdict` or `GateRefusal` on every branch — four refusal codes, no silent defaults, no clamps.
3. `min_net_margin_pct = 15` is seeded in `thresholds.toml`; a missing value returns `None` -> `GateRefusal(code="no_threshold_set")`.
4. `sku_catalog.toml` is the machine-readable single source of truth (16 SKUs with asin/tier/cogs; no stored margin); absent SKU -> `sku_not_in_catalog`.
5. `gate_action.py` is the thin CLI seam (no money math) ready for the Phase 8 apply spine: `argv -> gate.evaluate -> typed JSON stdout`, exit 0.
6. Spend-DOWN actions auto-pass before any catalog or threshold read.
7. Full pytest suite: **36 passed, 5 skipped** (5 skips are pre-existing Supabase/context gates, not regressions). All 10 gate tests pass. All 9 phase commits verified in git history.

---

_Verified: 2026-06-22_
_Verifier: Claude (gsd-verifier)_
