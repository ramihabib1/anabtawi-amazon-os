# 02-03 — Live TACOS-by-SKU acceptance (SUMMARY)

**Plan:** 02-03 · **Phase:** 02 (slice: TACOS-by-SKU + trust spine) · **Status:** complete
**Requirements:** DATA-05 (live), PROF-01 (live), TRUST-04 · **Date:** 2026-06-09

## What was delivered

The acceptance answer end-to-end against **live DataDoe data** (CLAUDE.md DoD: "runs
against a real export, not mocked"), plus the A1/A2/A3 resolutions and a runtime pivot.

- **Task 1 — skill authored.** `~/.hermes/skills/tacos-by-sku/SKILL.md` (v1.1) drives the
  DataDoe seam → `answer_tacos.py` → recommendation-voice render. Updated to the resolved
  wiring (see A1 below).
- **Task 3 — live pull + A1/A2/A3 (done in-session via the DataDoe MCP).**
  - **Export `103e0769…`** (daily, 455 rows) and **`d5b05c10…`** (per-SKU `groupBy` sum,
    22 rows) executed live, CA, trailing 30d. Read-only.
  - **A1 (locked):** source computes acos/tacos/roi at DAILY grain only; no window-ratio
    column and `groupBy` cannot aggregate a ratio. **Resolved:** pull `groupBy sku` + `sum`
    components; reviewed `habibos.tacos` computes the window ratio from the sums
    (`tacos=Σad_spend/Σtotal_sales`, etc.), source definitions verbatim. Escalated +
    operator-approved — not silent recomputation (T-02-11 honored).
  - **A2:** percent convention (`30.0`=30%), verified row-wise; matches thresholds.
  - **A3:** `exports_raw_download` inline; aggregated pull is small.
  - **Wire-fact:** column is `sku`, not `seller_sku`. Fixed in code + skill.
  - **Fixture re-pointed** to the real, sanitized per-SKU export
    (`tests/fixtures/profit_by_sku_30d.csv`; no seller UUID — `groupBy` collapsed utility
    columns). Catalog re-seeded from the 22 live SKUs (`ca_catalog_skus.txt`).
- **Task 4 — TRUST-04 sign-off.** Operator spot-checked the live answer vs Seller Central:
  reconciles, CA-only, no marketplace bleed.

## Code changes

- `src/habibos/tacos.py` — A1 refactor: `parse` validates the `*_sum` component schema
  (extra="ignore" tolerates utility cols); `classify` computes window ratios from sums,
  distinguishes "no data" (absent) from "no sales" (present, zero denominator).
- `scripts/answer_tacos.py` — read the `sku` column.
- `tests/test_tacos.py` — rewritten against the real fixture (window-aggregation, A2,
  suspect guard via synthetic frame, no-data vs no-sales, breach/refuse, provenance).

## Verification

- `uv run pytest -q` → **17 passed / 4 skipped** (Supabase skips pre-existing); ruff clean.
- End-to-end CLI run on the real fixture returns the typed Answer with provenance, breach
  flags, and honest no-sales handling. Spot values match operator-confirmed numbers
  (FX-M8MA-MMSA tacos 69.2 / acos 74.0 / roi −27.1; 18-116Z-1R77 tacos 46.5).

## Headline finding (recommendation, not action)

CA ad efficiency is poor this window — most SKUs breach the 30% ACOS / 15% TACOS ceilings.
Worst, all negative ROI: **FX-M8MA-MMSA** (TACOS 69.2, ROI −27.1), **18-116Z-1R77** (46.5,
−7.5), **KP-MEL9-XYGW** (40.6, −3.7). **9Z-KUHZ-FU2I** spent $25.28 on ads for $0 sales.
Surfaced for operator review; the system never acts.

## Runtime pivot

Daily runtime decided as **Claude Cowork** (Max subscription), superseding Hermes. Code
is runtime-agnostic and unchanged. Operator setup + paste-in Project instructions:
`docs/cowork-setup.md`. A1/A2/A3 recorded in `docs/datadoe-source-map.md` §6.

## Deviations

- Plan assumed the source emits a per-SKU window ratio via `groupBy seller_sku` (A1). Live
  data disproved it; resolved as above (escalated + approved). This adjusted the 02-02
  `tacos.py` contract (read→compute) — a sanctioned, reviewed money-logic change.

## Follow-ups

- Update CLAUDE.md / PROJECT.md runtime section (Hermes → Cowork) — binding-doc edit.
- Full known CA catalog (~30) vs the 22 export-observed SKUs lands with `sku_master`
  (Phase 3.5); until then catalog = export-observed set.
