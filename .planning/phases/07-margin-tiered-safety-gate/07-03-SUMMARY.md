---
phase: 07-margin-tiered-safety-gate
plan: 03
status: complete
requirements: [GATE-01, GATE-02, GATE-03, GATE-04, GATE-05]
subsystem: engine / money-core
tags: [margin-gate, tacos-ceiling, anti-fabrication, tdd-green]
provides: "habibos.gate — pre-ad CM%, per-SKU TACOS ceiling, worst-case projection, typed GateVerdict/GateRefusal"
requires: ["07-01 (gate result types + RED contract)", "07-02 (sku_catalog.toml + min_net_margin_pct floor)"]
affects: ["07-04 (gate_action CLI wires evaluate)", "Phase 9 spend-up queue"]
key-files:
  created: ["engine/src/habibos/gate.py"]
  modified: []
decisions:
  - "evaluate signature is (frame, action, catalog_path, marketplace=None) — matches the test_gate.py call order; marketplace defaults to action.marketplace when omitted"
  - "zero-sales no_margin checked from window sums BEFORE catalog membership so an export-present zero-sales SKU refuses for the right reason"
  - "ceiling + projected both round(...,1); strict projected > ceiling breaches (equal passes)"
metrics:
  tasks: 3
  files: 1
  duration: "~25 min"
  completed: "2026-06-22"
---

# Phase 7 Plan 03: Margin-Tiered Safety Gate Money Core Summary

`habibos.gate` — the hand-written, pytest-covered money core that computes each SKU's pre-ad
contribution margin (ad_spend added back, D-03), derives the per-SKU TACOS ceiling
(`CM% − min_net_margin_pct`, D-01), projects a spend-up's worst-case TACOS (sales held flat,
D-06), and returns a typed `GateVerdict`/`GateRefusal` — refusing (never clamping, never
defaulting) on every missing or over-ceiling input. Turns the Plan 01 RED `test_gate.py` GREEN.

## What landed

- **`engine/src/habibos/gate.py`** (new, 238 lines) — the structural twin of `tacos.py`:
  - `contribution_margin_pct(profit_sum, ad_spend_sum, total_sales_sum)` — pre-ad CM% with
    `ad_spend_sum` **added back** (D-03 Path A back-out); clones `tacos._ratio`'s
    None-on-zero-denominator grammar (`round(... * 100, 1)`, None on zero/missing sales —
    never 0, never a guess).
  - `ceiling_tacos_pct(cm_pct, floor)` → `round(cm_pct - floor, 1)` (D-01, single floor — no
    per-tier table, D-01a).
  - `projected_tacos_pct(ad_spend_sum, delta_spend, total_sales_sum)` — worst-case
    `(ad_spend_sum + delta_spend)/total_sales_sum*100`, sales held flat (D-06); None on
    zero/missing sales.
  - `_load_catalog(catalog_path)` — explicit `tomllib` read of the `[sku]` table; a missing
    file raises (no silent fallback, D-05).
  - `evaluate(frame, action, catalog_path, marketplace=None)` — the branch orchestrator.
  - Reuses `tacos.parse` / `PREMIUM_SOURCE_ID` — does not re-roll a CSV reader.

## Final evaluate branch order (recorded per plan `<output>`)

1. **spend-DECREASING** (`not action.is_spend_increasing`) → `GateVerdict(auto_pass=True)`,
   projected/ceiling/CM all None — **no catalog, no margin, no floor read** (D-06, Pitfall 5).
2. **zero-sales window** (the SKU's frame row has `total_sales_sum == 0/None`) →
   `GateRefusal(code="no_margin")`. Checked from the window sums **before** catalog membership
   so an export-present zero-sales SKU (`9Z-KUHZ-FU2I`, `ASW-H50`) refuses for the *right*
   reason (no margin), not "not in catalog".
3. **SKU ∉ catalog** → `GateRefusal(code="sku_not_in_catalog")` (D-05, explicit catalog).
4. **catalog `cogs` ≤ 0 / null / missing** → `GateRefusal(code="no_margin")` (D-03/D-04).
5. **SKU absent from the export frame** (no window sums) → `GateRefusal(code="no_margin")`.
6. **floor unset** (`thresholds.read("min_net_margin_pct", mkt)` → None) →
   `GateRefusal(code="no_threshold_set")` on every spend-up (D-07) — never a default.
7. **compute** `cm` → `ceiling = cm − floor` → `projected`; **strict `projected > ceiling`** →
   `GateRefusal(code="over_ceiling", breached_value=projected, ceiling=ceiling,
   source=PREMIUM_SOURCE)` naming the breaching number (**never a clamped GateVerdict**, GATE-04);
   else `GateVerdict(projected_tacos=projected, ceiling=ceiling, contribution_margin=cm)`.

## Rounding / precision chosen

- **CM%, ceiling, projected** all use `round(..., 1)` (one decimal place) — mirrors
  `tacos._ratio`'s `round(... * 100, 1)` so the gate's numbers match the rest of the engine's
  percent grammar. Worked fixture: `EU-Z87B-ZRBZ` CM% = (100.27 + 0.5)/279.95×100 = **36.0**;
  ceiling = 36.0 − 15 = **21.0**.

## Verification

- `cd engine && uv run pytest tests/test_gate.py -q` → **7 passed** (all GATE-01..05 + D-03/D-04 GREEN).
- `cd engine && uv run pytest tests/test_gate.py::test_contribution_margin_pre_ad
  tests/test_gate.py::test_profit_is_post_ad_addback -q` → **2 passed** (Task 1 pure functions).
- `cd engine && uv run pytest` → **33 passed, 5 skipped** (full suite green; the 5 skips are
  pre-existing Supabase/context gates — `test_config_seed`, `test_context`, `test_schema` ×3 —
  expected, not regressions). No previously-green test regressed.

Final pytest summary line:
```
======================== 33 passed, 5 skipped in 0.28s =========================
```

## Deviations from Plan

### 1. [Rule 3 — interface correction] evaluate argument order follows the tests, not the prose

The plan `<action>` prose described `evaluate(action, frame, catalog_path)`, but the committed
RED contract `test_gate.py` calls `gate.evaluate(_frame(), spend_up, TEST_CATALOG)` — frame
**first**, action second. The tests are the binding contract (and the plan's
`<critical_project_rules>` forbid weakening them), so `evaluate(frame, action, catalog_path,
marketplace=None)` was implemented to match the test call order. `marketplace` defaults to
`None` and resolves to `action.marketplace` when omitted, so the `"XX"` unset-floor test
(which sets `marketplace="XX"` on the `ProposedAction`) routes correctly.

### 2. [Rule 1 / scope-boundary] no_margin precedence reordered ahead of catalog membership

The plan's stated branch order put catalog lookup (step 2) before the margin/zero-sales check.
But the tests fund two **zero-sales** SKUs that are **absent from `TEST_CATALOG`**
(`9Z-KUHZ-FU2I`, `ASW-H50`) and assert `code == "no_margin"` — while a third absent SKU
(`SKU-NOT-IN-CATALOG`, also absent from the **frame**) asserts `code == "sku_not_in_catalog"`.
A strict catalog-first order would have returned `sku_not_in_catalog` for the two zero-sales
SKUs and failed the contract. Resolution: the zero-sales `no_margin` check (read from the
window sums) runs **before** catalog membership; the distinguishing signal is frame presence
(zero-sales → no_margin; frame-absent → sku_not_in_catalog). This preserves every D-04/D-05
intent and is the only ordering that satisfies all seven tests. Documented because it differs
from the plan's literal step numbering.

### 3. [scope boundary — NOT fixed, logged] `min_margin_pct` in test_config_seed.py left intact

The plan's Task 3 acceptance criterion `grep -rn "min_margin_pct" engine/ | grep -v
"min_net_margin_pct"` expects empty, with guidance to "fix any escaped reference to the new key
name." One match remains: `engine/tests/test_config_seed.py:18` lists `"min_margin_pct"` in its
`REQUIRED_KEYS` set. This is **a different layer** — the Phase 1 **DATA-04 Supabase `config`
table** schema key (the DB column the operator seeds), asserted only when `SUPABASE_DB_URL` is
set (currently SKIPPED). It is **not** an escaped reference to the `thresholds.toml` key this
phase renamed (that rename was completed in Plan 02 and no live `thresholds.toml`-layer code
references the old key). Renaming the Supabase required-key would alter the Phase 1 DATA-04
seed contract — out of scope for this money-core plan and a potential break to a future
Supabase plan. Left intact deliberately; the suite is green and the threshold-layer rename is
clean. (The only other grep hit, in `test_thresholds.py`, is the word inside a comment
documenting the rename, not a live reference.)

## Tasks

- **Task 1 (pure functions)** and **Task 2 (`evaluate` branch order)** were implemented in the
  single new file `gate.py` and committed together as one cohesive `feat` (a new file has no
  meaningful intermediate committable state between "pure functions only" and "full module").
  Both TDD verify gates were run and passed before the commit.
- **Task 3 (full-suite regression)** required no code change — the full suite is green and the
  `min_margin_pct` grep was evaluated (see Deviation 3). No commit needed for Task 3.

## Commits

- `183c1de` feat(07-03): implement habibos.gate margin-tiered safety money core (Tasks 1+2)

## Self-Check: PASSED

- `engine/src/habibos/gate.py` — FOUND
- commit `183c1de` — FOUND in `git log`
- `test_gate.py` 7/7 GREEN; full suite 33 passed / 5 skipped — verified
