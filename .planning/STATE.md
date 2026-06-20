---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Execution Era — Gated PPC Write Path
status: planning
last_updated: "2026-06-20T18:19:29.463Z"
last_activity: 2026-06-20
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State: Habib OS

<!-- Project memory. Updated at phase/plan transitions. -->

## Project Reference

- **Core value:** From the Hermes desktop workspace, ask real PPC/profit questions and get correct answers against live DataDoe data — with zero risk of changing anything on Amazon.
- **Milestone:** 1 — Foundation + read-only PPC/profit intelligence (conversational, on-demand)
- **Current focus:** Phase 02 — slice-tacos-by-sku-trust-spine
- **Project mode:** mvp (Vertical MVP) — shared foundation, then one end-to-end acceptance question per slice

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-06-20 — Milestone v2.0 started

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases complete | 0/5 |
| Requirements mapped | 21/21 |
| Acceptance questions answered | 0/4 |

## Accumulated Context

### Key Decisions (constrain execution)

- Data layer is READ-ONLY (DataDoe). No write path to Amazon in any M1 phase.
- Margin authority = DataDoe premium "Profit by SKU & Date"; `cogs` (FX-aware SCD) is fallback/reconciliation. Never hand-roll ACOS/TACOS when the premium column exists.
- `metric_snapshots` grain = daily × SKU × marketplace; unique on `(marketplace, seller_sku, snapshot_date)`; carries `captured_at` + `datadoe_export_id` (restatement-safe).
- `config` keyed `(key, marketplace)`; missing threshold → refusal, never a default. Empty config is a fabrication invitation.
- Trust spine (provenance on every number, config-driven thresholds, wrapped/logged calls) is built in Phase 2 (first slice) and reused by all later slices.
- Runtime = Hermes Mac desktop app; on-demand/on-open only (no clock-cron assumed in M1).
- One resident agent; money-touching math in hand-written Python primitives, never in skill prose.

### Open Items (resolve in phase discussion)

- DataDoe exact source columns + per-source timezone basis + premium enablement → resolve empirically in Phase 1 via `exports_sources_get`.
- Real `config` seed values (min margin %, ACOS ceiling, days-of-cover) → operator input in Phase 1.
- `~/.hermes` + Supabase backup target/schedule → decide in Phase 1.

### Todos / Watch-fors

- 2500-row DataDoe cap: handle by design in the first PPC primitive (Phase 3).
- TACOS ≤ ACOS sanity guard on the margin primitive (Phase 2).
- Don't sum attributed sales across SP/SB/SD; state program scope on every spend figure.
- Recommendation voice only — proposals logged to `decision_ledger`, never "I did X".

### Blockers

None.

## Session Continuity

- **Last action:** Roadmap + STATE created from PROJECT/REQUIREMENTS/research (2026-06-08).
- **Next action:** `/gsd:plan-phase 1` to decompose Foundation into executable plans.

---
*State initialized: 2026-06-08*
