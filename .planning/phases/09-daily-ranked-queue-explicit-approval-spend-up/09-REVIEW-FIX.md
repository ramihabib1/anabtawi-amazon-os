---
phase: 09-daily-ranked-queue-explicit-approval-spend-up
fixed_at: 2026-06-24T20:50:03Z
review_path: .planning/phases/09-daily-ranked-queue-explicit-approval-spend-up/09-REVIEW.md
iteration: 1
findings_in_scope: 13
fixed: 13
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-06-24T20:50:03Z
**Source review:** .planning/phases/09-daily-ranked-queue-explicit-approval-spend-up/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 13 (5 Critical, 5 Warning, 3 Info)
- Fixed: 13
- Skipped: 0

All fixes were applied inside an isolated git worktree, each committed atomically, and the
engine pytest suite (`cd engine && uv run pytest`) was re-run GREEN after every fix —
final state **91 passed, 5 skipped** (up from the 83/5 baseline; +8 new contract tests pin
the fixed behaviors). No fix violated the project constitution: every gate still REFUSES
(never clamps, never defaults), no threshold was invented, no autonomous Amazon write was
added, and `.env` / secrets were untouched.

**Money-logic / safety fixes flagged for human verification.** The fixes below change gate-chain
wiring or money-core estimation. Syntax + the new/existing tests pass, but a developer should
confirm the *semantics* before the phase proceeds: **CR-01, CR-02, CR-05, WR-01, WR-02**.

## Fixed Issues

### CR-01: Real spend-up apply path bypasses the cover/conversion, matured-window, and internal-competition gates

**Files modified:** `engine/scripts/queue_run.py`, `engine/tests/test_queue_run.py`
**Commit:** dcb3301
**Status:** fixed: requires human verification (write-path gate chain — safety-critical)
**Applied fix:** Added a `write_path: bool` parameter to `_spend_up_refusal` and a
`_candidate_from_args(args)` helper, then ran the SAME read-only gate chain (margin → cover/
conversion → matured-window → internal-competition) in `_apply_mode` BEFORE `apply.apply`,
refusing on the first `GateRefusal`. On the write path a missing cover read REFUSES
(`no_cover_data`) instead of skipping, so the EXEC-05 cover guardrail (stop GG-0DC1 at 1 FBA
unit) now runs on the path that actually fires a write. `_candidate_from_args` carries the
operator's `--delta-spend` as `delta_spend_weekly` with `window_days=7` so the CR-02 weekly→
window scale is a no-op and the margin gate here sees the EXACT delta `apply.apply` will. Added
3 tests: GG-0DC1 refuses `cover_below_floor` on apply; a spend-up with no `--cover` refuses
`no_cover_data`; an all-gates-cleared spend-up still applies.

### CR-02: Margin gate fed a weekly delta against a 30-day window sum — TACOS under-projected ~4x

**Files modified:** `engine/scripts/queue_run.py`, `engine/src/habibos/gate.py`
**Commit:** 66917da
**Status:** fixed: requires human verification (money-core projection — strengthens the over-ceiling refusal)
**Applied fix:** In `_spend_up_refusal`, scaled the weekly delta to the gate's window before
building the `ProposedAction` (`delta_spend_window = delta_spend_weekly * window_days / 7`,
`window_days` from the candidate, default 30 = the fixture's documented trailing-30d window —
not an invented threshold, it is the window the candidate's own sums were computed over). The
downstream cover/harvest gates read only the SIGN (`is_spend_increasing`), which positive
scaling preserves. Documented the explicit UNIT CONTRACT on `gate.projected_tacos_pct`
(delta must be window CAD, never weekly). This makes the over-ceiling refusal fire when it
should — strengthening the guardrail in the conservative direction.

### CR-03: Present-but-null `days_of_data` crashes the entire render run

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** a94ed0f
**Status:** fixed
**Applied fix:** Replaced the key-presence guard (`"days_of_data" in live` then `int(live[...])`)
with `live.get("days_of_data")` and a `is not None` check before casting, so a present-but-null
value (a failed/partial agent read) is treated as "no data" and the maturity gate is skipped
rather than raising `TypeError: int(None)` and aborting every row. Mirrors `cover_gate`'s
None-is-no-data discipline (hard rule 4 — never crash on a missing live read).

### CR-04: Spend-up `apply --approve` without `--artifact` crashes instead of refusing

**Files modified:** `engine/scripts/queue_run.py`, `engine/tests/test_queue_run.py`
**Commit:** b427a0a
**Status:** fixed
**Applied fix:** In `_apply_mode`, after parsing `--artifact`, added an early typed refusal:
a spend-increasing action reaching the write path with `gate_frame is None` returns
`GateRefusal(code="no_margin")` and returns 0 — never reaching `apply.apply` →
`gate.evaluate(None, ...)` (which would raise `AttributeError 'NoneType'.to_dicts`). A missing
money-gate input now surfaces the typed refusal the constitution requires. Updated the existing
`test_apply_mode_with_approve_applies` (which had ENCODED THE BUG — it expected a spend-up to
apply with no margin frame) to supply `--artifact`, and added a new test asserting the
`no_margin` refusal when `--artifact` is absent.

### CR-05: "Live at 50%" reversible magnitude cap never fires on the auto-apply path

**Files modified:** `engine/scripts/queue_run.py`, `engine/tests/test_queue_run.py`
**Commit:** 3fa6af1
**Status:** fixed: requires human verification (safety guardrail — confirm config-vs-param precedence)
**Applied fix:** In `_auto_apply`, read `thresholds.read("max_reversible_pct_change", marketplace)`
and `setdefault` it into a copy of the action's params, so `apply._max_reversible_pct` (which
reads only `params["max_reversible_pct_change"]`) now sees the live cap (50) instead of None
(seeded permissive). `setdefault` keeps an explicit agent-injected per-action cap winning; a
None cap (key unset) stays permissive — the documented seeded-permissive asymmetry. Added a
test asserting the auto-applied action carries `max_reversible_pct_change == 50.0`. (The cap
only fires when the candidate also carries `params["pct_change"]` — confirm Phase 8's intent
that the agent supplies the bounded-% magnitude.)

### WR-01: `is_act_now` maturity-bypass is never wired into the gate chain

**Files modified:** `engine/scripts/queue_run.py`, `engine/tests/test_queue_run.py`
**Commit:** b231bed
**Status:** fixed: requires human verification (gate-chain maturity bypass on a money move)
**Applied fix:** Gated the matured-window check on `not harvest.is_act_now(live or {})`, so an
obviously-dead signal (inactive listing / zero lifetime orders / enabled-on-discontinued — fields
the live cover/signal map carries) bypasses the maturity wait per the harvest D-10 contract
instead of being wrongly refused `immature_window`. Added 2 tests: an immature window refuses for
a normal signal; the SAME immature window with an act-now signal returns None (bypassed).

### WR-02: Estimator extrapolates average ACOS to marginal spend, producing implausibly large $/wk

**Files modified:** `engine/src/habibos/rank_queue.py`, `engine/scripts/queue_run.py`, `engine/tests/test_rank_queue.py`
**Commit:** 00c185b
**Status:** fixed: requires human verification (money-core estimator — operator must decide the bar)
**Applied fix:** Documented the average-ACOS-extrapolation model assumption + its limit on
`estimate_weekly_usd` so a reader reads the ~$2100/wk as a MODEL ARTIFACT, not a forecast. Added
an OPTIONAL, seeded-permissive `materiality_min_ad_spend` bar threaded `estimate_weekly_usd` ←
`rank` ← the CLI (`thresholds.read("materiality_min_ad_spend", ...)`): below the bar a candidate's
estimate is None (undefined — the same None-on-undefined grammar) so a tiny/anomalous denominator
cannot rank #1. The bar is **unset** in `thresholds.toml` today → None → permissive → ZERO
behavior change now (mirrors the magnitude-cap seeded-permissive pattern). Constitution-compliant:
no number was invented — clamping/falling-back on an engine-chosen floor would have violated hard
rule 4, so the floor is left as operator policy (a future `thresholds.toml` edit). Added 2 tests:
unset bar is permissive; a set $5 bar nullifies the EU-Z87B 0.5-spend artifact.
**Human action:** decide whether to set `materiality_min_ad_spend` in `thresholds.toml` (and to
what value) — the mechanism is built + tested but seeded off pending that operator decision.

### WR-03: Auto-apply fires real writes outside `logged_call`, unlike the apply path

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** d8b1275
**Status:** fixed
**Applied fix:** Wrapped the `_render_mode` AUTO-branch `_auto_apply` call in
`habibos_logging.logged_call("queue_run", marketplace=...)` with a type-derived
`end_fields["status"]` ("refused" vs "applied"), mirroring `_apply_mode`, so every
queue-initiated real write has a consistent audit record (no seller UUID — op + marketplace only).

### WR-04: Render annotations can desync from the table (parallel lists, no row identity)

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** cc3356d
**Status:** fixed
**Applied fix:** Keyed each annotation by the row's 1-based RANK (its position in the rendered
table, which `queue.render` enumerates in the same order) — the annotation line is now prefixed
`#{rank}` rather than tied to the row only by `sku [action]`. A duplicate SKU or any future
reorder between the two emissions can no longer mismatch a refusal annotation to the wrong row.

### WR-05: Candidate identity keyed by SKU collapses multiple per-SKU candidates

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** d92d1d7
**Status:** fixed
**Applied fix:** Keyed the candidate lookup by the per-row identity `(sku, entity)` instead of
`sku` alone, and looked up each ranked row by `(row.sku, row.entity)`. `rank_queue`'s `QueueRow`
already carries the same `entity`, so multiple candidates for one SKU (several campaigns) each
map to their own candidate — gating the correct `entity_id`/params, not the last-wins one.

### IN-01: `graduates` and `render_row` are exported/tested but unused by any production path

**Files modified:** `engine/src/habibos/harvest.py`, `engine/src/habibos/queue.py`
**Commit:** d35bdc7
**Status:** fixed
**Applied fix:** Added a one-line "DELIBERATE FUTURE-USE PUBLIC API (IN-01)" note to both
docstrings stating each is tested but NOT yet on a production path, so a reader does not assume
they run. (Wiring graduation into candidate formation / `render` into the table is a feature
change with operator-policy implications — out of scope for a review fix; documenting intent is
the review-sanctioned alternative.)

### IN-02: `GateVerdict` imported in `queue_run.py` but unused

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** d067a88 (resolved together with IN-03)
**Status:** fixed
**Applied fix:** Rather than removing the import, IN-03's fix USES `GateVerdict` (a new branch in
`_status_of`), so the import is now live and the dead-import concern is resolved. This is the
correct resolution because IN-02 (remove the import) and IN-03 (add a branch using it) are
mutually exclusive — keeping + using it satisfies both.

### IN-03: `_status_of` returns `"unknown"` for a `GateVerdict`, silently dropping a pass

**Files modified:** `engine/scripts/queue_run.py`
**Commit:** d067a88
**Status:** fixed
**Applied fix:** Added an `isinstance(result, GateVerdict)` branch returning `"gate-pass"` so a
typed PASS is labelled, not bucketed as opaque "unknown". Not reachable from `_auto_apply` today
(apply.apply returns only AppliedResult/Refusal/GateRefusal), but a future positive verdict now
surfaces as a pass rather than being silently dropped.

## Skipped Issues

None — all 13 in-scope findings were fixed.

## Notes on constitution compliance

- **No invented numbers/thresholds.** CR-02's `window_days` (default 30) is the candidate set's
  own cited window, not a money threshold. WR-02 deliberately did NOT clamp to or fall back on an
  engine-chosen ACOS floor / materiality bar — those would be invented numbers; instead the bar is
  an OPTIONAL operator-set config dial, seeded permissive (unset today).
- **Gates refuse, never clamp/default.** CR-01/CR-03/CR-04 all route missing inputs to typed
  refusals (`no_cover_data` / skip-as-no-data / `no_margin`), never a swallowed error or a default.
- **Approval gate never weakened.** CR-01 ADDS the full read-only chain to the write path; the
  explicit `--approve` batch gate and the spend-up vs reversible split are unchanged.
- **Read-only data layer preserved.** No fix added any autonomous Amazon write; the agent-supplied
  MCP-result seam (zero-arg callables / local fixtures) is intact. `.env`/secrets untouched.
- **One test was changed because it encoded the bug** (`test_apply_mode_with_approve_applies`):
  it expected a spend-up to apply with no margin frame (and, after CR-01, no cover data), the exact
  unsafe path CR-04/CR-01 forbid. It was updated to supply `--artifact` + `--cover` so it tests an
  all-gates-cleared apply; separate new tests pin the refusal paths.

---

_Fixed: 2026-06-24T20:50:03Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
