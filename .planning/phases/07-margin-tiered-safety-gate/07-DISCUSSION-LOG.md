# Phase 7: Margin-Tiered Safety Gate - Discussion Log

> **Audit trail only.** Not consumed by planning, research, or execution agents.
> Decisions captured in `07-CONTEXT.md` — this log preserves the discussion.

**Date:** 2026-06-21
**Phase:** 07-margin-tiered-safety-gate
**Mode:** discuss
**Areas selected by operator:** Ceiling formula, Margin source, SKU→margin table, Projected TACOS (all four), + net-margin floor

## Area selection
Operator selected **all four** offered gray areas to discuss (the researcher/planner cannot
write `gate.py` without them — they are the open Q2/Q3 plus the projected-TACOS modeling rule).

## Questions & selections

### Ceiling formula
- **Options:** (a) Margin minus floor `ceiling = CM% − min_net_margin_pct` [recommended];
  (b) Margin minus floor capped at 25%; (c) Per-tier flat ceilings.
- **Selected:** (a) Margin minus floor. → D-01 / D-01a.

### Contribution-margin source
- **Options:** (a) Pre-ad, reconciled from the premium export (verify pre/post-ad, add ad
  back if needed) [recommended]; (b) Raw `profit_sum/total_sales`; (c) Static COGS-based
  margin.
- **Selected:** (a) Pre-ad, reconciled from export. → D-02 / D-03.

### SKU→tier/margin table (GATE-05)
- **Options:** (a) New file, margin computed live [recommended]; (b) New file, static margin
  stored; (c) Rows in `thresholds.toml`.
- **Selected:** (a) New file, margin computed live. → D-04 / D-05.

### Projected TACOS (GATE-03)
- **Options:** (a) Conservative, sales held flat [recommended]; (b) Target-ACOS/bid proxy;
  (c) Proportional lift.
- **Selected:** (a) Conservative, sales held flat. → D-06.

### Net-margin floor (operator policy)
- **Options:** (a) Seed 15% now [recommended]; (b) Leave empty for now; (c) Seed a different
  value.
- **Selected:** (a) Seed `min_net_margin_pct = 15` now (empty-refusal path still built +
  tested). → D-07 / D-07a.

## Notes
- Every selection took the recommended option, yielding a fully margin-derived gate with no
  flat-number knobs — each ceiling traces to one floor figure and one live margin.
- Key consistency item surfaced and folded in: file has `min_margin_pct = ""`; roadmap/
  research use `min_net_margin_pct`. Standardize on the latter (D-07a).
- Critical correctness flag handed to the researcher: verify whether the premium source's
  `profit_sum` is pre- or post-ad to avoid a circular gate (D-03).

## Deferred ideas raised
- None new beyond the roadmap's existing phase boundaries (apply spine → P8; queue → P9;
  portfolios → P10; Supabase migration → P3.5).
