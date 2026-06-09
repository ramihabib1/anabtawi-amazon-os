# Phase 2: Slice — TACOS by SKU (+ trust spine) - Discussion Log

> **Audit trail only.** Not consumed by downstream agents. Decisions live in CONTEXT.md.

**Date:** 2026-06-09
**Phase:** 02-slice-tacos-by-sku-trust-spine
**Mode:** discuss (standard, interactive)
**Areas discussed:** Live-only scope line, Answer shape, Thresholds in answer, Trust-spine edges

## Area selection

Operator selected all four offered gray areas: Live-only scope line, Answer shape,
Thresholds in answer, Trust-spine edges.

## Questions & Answers

### Live-only scope line
- **Options:** Pure pass-through (no local persistence) / Local artifact cache (TTL'd files)
- **Chosen:** Pure pass-through — every ask pulls fresh, persists nothing locally; matches
  the Supabase-deferral note (persistence is Phase 3.5). → D-01, D-02

### Answer shape
- **Options:** All SKUs sort-by-TACOS-desc / All SKUs sort-by-ad-spend-desc / Top-N worst only
- **Chosen:** All ~30 SKUs, sorted by TACOS descending, trailing-30-day default window,
  each ratio labelled with definition + source. → D-05, D-06

### Thresholds in answer
- **Options:** Pure reporting / Report + flag vs ceilings
- **Chosen:** Report + flag vs `acos_ceiling_pct` / `tacos_ceiling_pct`. Missing ceiling →
  flag refuses ("no threshold set"), numbers still render. → D-07, D-08

### Trust-spine edges
- **Options:** Show SKU + mark 'no data' / Omit missing SKU entirely
- **Chosen:** Show the SKU with ratios = "no data (not in premium export)"; whole-export
  empty/failed → refuse. → D-10, D-11

## Follow-up: PPC ceiling values

- Operator response: "i am not an expert on advertisement so your help is needed here."
- Advisor recommendation (with rationale): `acos_ceiling_pct = 30` (conservative catalog-wide
  break-even-ACOS proxy for a food/sweets catalog), `tacos_ceiling_pct = 15` (healthy band
  for an established non-launch catalog). Framed as operator-adopted starting seeds to TUNE
  after the first real answer, and to move toward per-SKU break-even once margins reconcile
  in Phase 3.5. → D-09

## Deferred ideas captured

- metric_snapshots / cogs FX / decision_ledger / config-table migration → Phase 3.5
- Per-SKU break-even ACOS ceiling → Phase 3.5
- Wasted-spend ranking + deeper flagging → Phase 3
