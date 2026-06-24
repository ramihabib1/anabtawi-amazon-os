---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
reviewed: 2026-06-24T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - .claude/skills/ppc-analysis/SKILL.md
  - engine/config/thresholds.toml
  - engine/scripts/queue_run.py
  - engine/src/habibos/cover_gate.py
  - engine/src/habibos/harvest.py
  - engine/src/habibos/queue.py
  - engine/src/habibos/rank_queue.py
  - engine/src/habibos/result.py
  - engine/tests/fixtures/queue_candidates.json
  - engine/tests/fixtures/queue_cover_map.json
  - engine/tests/test_cover_gate.py
  - engine/tests/test_harvest.py
  - engine/tests/test_queue.py
  - engine/tests/test_queue_run.py
  - engine/tests/test_rank_queue.py
  - engine/tests/test_thresholds.py
findings:
  critical: 5
  warning: 5
  info: 3
  total: 13
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-06-24T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

Phase 9 adds the daily dollar-ranked PPC queue: a money-core ranker (`rank_queue.py`),
two new gates (`cover_gate.py`, `harvest.py`), a class-tagger/renderer (`queue.py`), and a
CLI orchestrator (`queue_run.py`) that fans rank → gate → render → apply. The pure predicate
modules (`cover_gate`, `harvest`, `queue`) are well-structured, mirror the established
refuse-never-default / strict-breach-never-clamp grammar, and their unit contracts are sound.
All 34 listed tests pass.

The defects concentrate in the **integration layer** — `queue_run.py` — and in the **estimator
model**. The most serious findings are correctness/safety gaps the unit tests do not exercise:

1. The real spend-up write path (`apply` mode) runs **only the margin gate**, silently skipping
   the cover/conversion, matured-window, and internal-competition gates that render mode runs and
   that SKILL.md + the cover_gate docstring promise. The EXEC-05 guardrail (stop GG-0DC1 at 1 FBA
   unit) never executes on the path that actually fires a write.
2. The margin gate is fed a **weekly** delta against a **30-day window** sum, under-projecting
   TACOS ~4x and weakening the over-ceiling refusal.
3. Two unhandled crash paths in `queue_run.py` (a present-but-null `days_of_data`; a spend-up
   `apply --approve` without `--artifact`) produce uncaught tracebacks where the engine is
   contractually required to return a typed refusal.
4. The "live at 50%" reversible magnitude cap never fires on the auto-apply path because the
   configured threshold is never read/injected.

These are exactly the failure classes the project constitution targets (missing-input-must-refuse,
no-fabricated-number, no-gate-bypass on a money move). The unit tests are green because they pin
each pure predicate in isolation; the integration wiring that composes them is where the gaps are.

## Critical Issues

### CR-01: Real spend-up apply path bypasses the cover/conversion, matured-window, and internal-competition gates

**File:** `engine/scripts/queue_run.py:221-270` (`_apply_mode`)
**Issue:** `_apply_mode` is the only path that fires a real spend-up write. It builds the
`ProposedAction` and calls `apply.apply(...)`, which internally runs **only** the margin gate
(`gate.evaluate`), the denylist, and the magnitude cap (see `apply.py:169-184`). It never calls
`cover_gate.check`, `harvest.judge_later_blocked`, or `harvest.consolidation_blocked`.

The full gate chain (`margin → cover/conversion → matured-window → internal-competition`) is run
**only in render mode** via `_spend_up_refusal` (`queue_run.py:64-125`) — but render mode never
applies a spend-up. So the chain that decides whether a spend-up is *actionable* and the chain
that *executes* it are different chains.

Concrete consequence: GG-0DC1 at 1 FBA unit (cover 2d, far below the 42-day floor) is the named
EXEC-05 case. In render mode it correctly annotates `REFUSED:cover_below_floor`. But if the
operator runs `queue_run.py apply --approve --sku GG-0DC1-SKHG --action-type bid_up …`, the cover
gate never runs and the over-sell-into-stockout raise can fire. SKILL.md:84-89 and
`cover_gate.py:5-8` both promise this guardrail blocks the write; it does not.

**Fix:** Run the same read-only gate chain in `_apply_mode` before calling `apply.apply`, refusing
on the first `GateRefusal` exactly as render mode does. Factor the chain so both modes share it:
```python
# in _apply_mode, after the --approve check, before apply.apply:
refusal = _spend_up_refusal(
    _candidate_from_args(args),
    gate_frame=gate_frame,
    catalog_path=args.catalog,
    cover_map=_load(args.cover) if args.cover else {},
    term_acos_map=_load(args.term_acos) if args.term_acos else {},
    marketplace=args.marketplace,
)
if refusal is not None:
    json.dump(dataclasses.asdict(refusal), sys.stdout); sys.stdout.write("\n")
    return 0
```
Note this requires `apply` mode to accept `--cover` / `--term-acos`; absent them the cover gate
must **refuse** (no_cover_data), not silently skip — see CR-02 for why "skip when absent" is unsafe
on the write path.

### CR-02: Margin gate fed a weekly delta against a 30-day window sum — TACOS under-projected ~4x

**File:** `engine/scripts/queue_run.py:84` and `:138` (`delta_spend=float(candidate.get("delta_spend_weekly", 0.0))`)
**Issue:** `gate.projected_tacos_pct` computes `(ad_spend_sum + delta_spend) / total_sales_sum`,
where `ad_spend_sum` and `total_sales_sum` are **window** sums (the fixture window is trailing
30d). `_spend_up_refusal` passes `delta_spend = candidate["delta_spend_weekly"]` — a **weekly**
figure — as that `delta_spend`. Adding ~1 week of incremental spend to a 30-day spend sum, then
dividing by 30-day sales, understates the projected TACOS impact by roughly 4x. The gate therefore
refuses an over-ceiling raise far less often than intended — it weakens the core money guardrail
in the permissive direction. The same `delta_spend_weekly` is (correctly) weekly for the
`rank_queue` estimate but (incorrectly) used un-scaled for a window projection.

**Fix:** Scale the weekly delta to the gate's window before projecting, or carry an explicit
window-scaled `delta_spend_window` in the candidate so the unit is unambiguous:
```python
# match the delta unit to the gate's window (e.g. window_days from the candidate/header):
window_days = candidate.get("window_days", 30)
delta_window = float(candidate.get("delta_spend_weekly", 0.0)) * (window_days / 7.0)
action = ProposedAction(..., delta_spend=delta_window, ...)
```
Document the unit on `ProposedAction.delta_spend` / `projected_tacos_pct` so the contract is
explicit (window CAD, not weekly).

### CR-03: Present-but-null `days_of_data` crashes the entire render run

**File:** `engine/scripts/queue_run.py:111-113`
**Issue:** The matured-window branch guards only on key presence: `if live is not None and
"days_of_data" in live:` then `int(live["days_of_data"])`. A cover-map entry from a failed/partial
agent read can plausibly carry `"days_of_data": null` (the key is present, the value is None).
`int(None)` raises `TypeError`, which escapes `_spend_up_refusal` and aborts the whole `render`
run for every row — not just the affected SKU. The engine's discipline is "no data → typed refusal,
never crash"; `cover_gate.check` correctly treats a None live read as a refusal, but this branch
does not.

Reproduced: `int(None)` → `TypeError: int() argument must be ... not 'NoneType'`.

**Fix:** Treat a missing/null `days_of_data` as "no data" and skip (or refuse) instead of casting:
```python
days_of_data = live.get("days_of_data") if live is not None else None
if days_of_data is not None:
    ad_product = live.get("ad_product", "SPONSORED_PRODUCTS")
    refusal = harvest.judge_later_blocked(action, ad_product, int(days_of_data))
    if isinstance(refusal, GateRefusal):
        return refusal
```

### CR-04: Spend-up `apply --approve` without `--artifact` crashes instead of refusing

**File:** `engine/scripts/queue_run.py:245-262`
**Issue:** In `_apply_mode`, `gate_frame` is left `None` when `--artifact` is not supplied. For a
spend-increasing action (`delta_spend > 0`), `apply.apply` → `_evaluate_margin` →
`gate.evaluate(None, action, …)` → `frame.to_dicts()` raises
`AttributeError: 'NoneType' object has no attribute 'to_dicts'`. An operator who approves a
spend-up but forgets `--artifact` gets an uncaught traceback instead of the typed
`no_margin`/`no data` refusal the constitution requires (a missing money-gate input must refuse,
never crash, never proceed).

Reproduced: `queue_run.py apply --approve --action-type budget_up … (no --artifact)` →
`AttributeError 'NoneType' object has no attribute 'to_dicts'`.

**Fix:** Refuse early when a spend-up reaches the write path with no margin frame:
```python
if ProposedAction(..., delta_spend=args.delta_spend, ...).is_spend_increasing and gate_frame is None:
    refusal = GateRefusal("no margin — no premium export supplied for the spend-up gate",
                          code="no_margin")
    json.dump(dataclasses.asdict(refusal), sys.stdout); sys.stdout.write("\n")
    return 0
```
(Alternatively make `gate.evaluate` refuse on a None frame rather than dereferencing it — but the
crash must become a typed refusal at one of the two layers.)

### CR-05: "Live at 50%" reversible magnitude cap never fires on the auto-apply path

**File:** `engine/scripts/queue_run.py:128-154` (`_auto_apply`), reading
`engine/config/thresholds.toml:70` (`max_reversible_pct_change = 50`)
**Issue:** Phase 9 flipped `max_reversible_pct_change` live to 50, and the docstrings + SKILL.md
state the cap "refuses an over-cap reversible — never clamps" and is "live at 50%"
(`queue_run.py:131-133`, `SKILL.md:73-74`). But the cap actually applied is read by
`apply._max_reversible_pct(action)` (`apply.py:336-340`), which reads **only**
`action.params["max_reversible_pct_change"]` — it never calls
`thresholds.read("max_reversible_pct_change", marketplace)`. `_auto_apply` builds the action from
`candidate.get("params", {})`, and the candidate fixtures inject no such param. So the cap passed
to `magnitude.check` is `None` → seeded permissive → **the 50% cap never fires**. A reversible
bid_down of -90% would auto-apply unbounded, contradicting the documented guardrail.

**Fix:** Read the live cap and inject it into the action's params (or thread it through
`apply.apply`) so the auto-apply path actually enforces it:
```python
cap = thresholds.read("max_reversible_pct_change", marketplace)
params = dict(candidate.get("params", {}))
if cap is not None:
    params.setdefault("max_reversible_pct_change", cap)
action = ProposedAction(..., params=params)
```
The same gap affects `_apply_mode` if a reversible is ever routed there. Confirm whether Phase 8
intended the cap to come from config or from agent-injected params and make the wiring consistent
with the "live at 50%" claim.

## Warnings

### WR-01: `is_act_now` maturity-bypass is never wired into the gate chain

**File:** `engine/scripts/queue_run.py:111-116`; `engine/src/habibos/harvest.py:61-71`
**Issue:** `harvest.is_act_now` exists and is tested (it identifies obviously-dead signals —
inactive listing / zero lifetime orders / enabled-on-discontinued — that should *bypass* the
maturity wait, per the module's stated D-10 contract). But `_spend_up_refusal` calls
`judge_later_blocked` **unconditionally**, never first consulting `is_act_now`. An act-now signal
that arrives on an immature window would be refused `immature_window` even though the harvest
contract says it should not wait. The bypass logic is built and tested but disconnected from the
only caller — so the documented behavior is unreachable.
**Fix:** Gate the maturity check on `not is_act_now(signal)` once the candidate/cover map carries
the act-now signal fields, or remove the `is_act_now` export if the bypass is intentionally
deferred (and say so), so dead public API does not imply live behavior.

### WR-02: Estimator extrapolates average ACOS to marginal spend, producing implausibly large $/wk

**File:** `engine/src/habibos/rank_queue.py:40-66`
**Issue:** `expected_weekly_usd = delta_spend_weekly / (ad_spend_sum / ad_sales_sum)`. With the
`EU-Z87B-ZRBZ` fixture (`ad_spend_sum=0.5`, `ad_sales_sum=50.0` → 1% window ACOS), a $21/wk raise
yields an expected **$2100/wk** incremental sales — a 100x return treated as a defensible figure
and ranked #1. The model assumes marginal spend converts at the historical *average* ACOS, which
is economically unsound (a 1% ACOS is almost always a data artifact, and marginal ≠ average). This
is not a None-fabrication (the math is reviewable), but it lets a tiny/anomalous denominator
dominate the dollar ranking — undermining "rank by dollars" with a number no operator would trust.
**Fix:** Either bound the implied ACOS to a sane floor (and surface when the estimate was clamped),
or fall back to None when `ad_spend_sum` is below a materiality threshold (too little spend to
estimate a marginal return), mirroring the None-on-undefined discipline. At minimum, document the
"average-ACOS extrapolation" assumption on the QueueRow so a reviewer reads the $2100 as a model
artifact, not a forecast.

### WR-03: Auto-apply fires real writes outside `logged_call`, unlike the apply path

**File:** `engine/scripts/queue_run.py:205-210` (`_render_mode` AUTO branch) vs `:250-266`
(`_apply_mode`)
**Issue:** `_apply_mode` wraps `apply.apply` in `habibos_logging.logged_call("queue_run", …)` and
derives an explicit `end_fields["status"]` from the result type. The `_render_mode` AUTO branch
calls `_auto_apply` → `apply.apply` (a *real* account write per the docstring, "autonomy != silence")
with **no** surrounding `logged_call` at the queue layer. `apply._logged_start_apply` logs the
inner start, but the queue-level invocation that decides to auto-fire is unlogged. The two write
paths have inconsistent observability for an operation that mutates the live account.
**Fix:** Wrap the `_auto_apply` call in the same `logged_call` context and set a type-derived
status, mirroring `_apply_mode`, so every queue-initiated write has a consistent audit record.

### WR-04: Render annotations can desync from the table (parallel lists, no row identity)

**File:** `engine/scripts/queue_run.py:181-217`
**Issue:** `rendered` (the table rows) and `annotations` (the gate/apply notes) are built as two
parallel lists and emitted separately — the table via `queue.render(rendered)`, the notes as a
second block. There is no shared key tying an annotation line to its table row beyond positional
order plus a `sku [action]` prefix. A SKU appearing in multiple rows (e.g. two campaigns for one
SKU), or any future reordering between the two emissions, silently mismatches a refusal annotation
to the wrong row — and the refusal is what tells the operator a raise is *not* actionable.
**Fix:** Carry the gate note on the row (or render one combined table with a `note`/`status`
column) so the refusal and the row it refers to cannot drift apart. Key annotations by row index,
not by SKU.

### WR-05: Candidate identity keyed by SKU collapses multiple per-SKU candidates

**File:** `engine/scripts/queue_run.py:169` (`candidates = {c["sku"]: c for c in …}`)
**Issue:** The candidate lookup is a dict keyed by `sku`. If the candidate set ever contains more
than one proposed move for the same SKU (different campaigns/targets — entirely normal for a SKU
running several campaigns), the dict keeps only the last one. `_render_mode` then looks up each
ranked row's candidate by `row.sku` (`:186`), so multiple rows for that SKU all resolve to the
same (last) candidate — gating the wrong entity_id / params. The fixture happens to have one row
per SKU, so the test does not catch it.
**Fix:** Key the lookup by a per-row identity (e.g. `(sku, entity)` or a candidate id) and have
`rank_queue`/`QueueRow` carry that same key, so each ranked row maps to its own candidate.

## Info

### IN-01: `graduates` and `render_row` are exported/tested but unused by any production path

**File:** `engine/src/habibos/harvest.py:121-133` (`graduates`); `engine/src/habibos/queue.py:108-134`
(`render_row`)
**Issue:** Both are in `__all__` and have passing contract tests, but neither is called by
`rank_queue`, `queue.render`, or `queue_run`. `queue.render` builds its cells directly rather than
via `render_row`, and graduation is never evaluated in the pipeline. They read as wired but are
dead in the integration.
**Fix:** Either wire them into the pipeline (use `render_row` to build the table cells; evaluate
`graduates` where harvest candidates are formed) or add a one-line comment marking them as a
deliberate future-use public API so a reader does not assume they run.

### IN-02: `GateVerdict` imported in `queue_run.py` but unused

**File:** `engine/scripts/queue_run.py:41-48`
**Issue:** `GateVerdict` is imported from `habibos.result` but never referenced in the module
(`_status_of` only branches on `AppliedResult` / `Refusal` / `GateRefusal`). Minor dead import.
**Fix:** Remove `GateVerdict` from the import list.

### IN-03: `_status_of` returns `"unknown"` for a `GateVerdict`, silently dropping a pass

**File:** `engine/scripts/queue_run.py:157-163`
**Issue:** `_status_of` handles `AppliedResult` and the two refusal types but falls through to
`"unknown"` for anything else, including a `GateVerdict` (a typed PASS). `apply.apply` returns only
`AppliedResult`/`Refusal`/`GateRefusal`, so this is not currently reachable from `_auto_apply` — but
the catch-all `"unknown"` would mask an unexpected positive verdict as an opaque status in the
annotation rather than surfacing it. Low risk given the current return contract.
**Fix:** Either assert the apply contract explicitly or add a `GateVerdict` branch so a pass is
labeled, not bucketed as "unknown".

---

_Reviewed: 2026-06-24T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
