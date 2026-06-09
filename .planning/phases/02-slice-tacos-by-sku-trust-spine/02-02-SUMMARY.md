---
phase: 02-slice-tacos-by-sku-trust-spine
plan: 02
subsystem: tacos-money-logic-core
tags: [money-logic, anti-fabrication, polars, pydantic, cli, trust-spine, pytest]
requires:
  - "habibos.result — Answer/Refusal/SkuRow (Plan 02-01)"
  - "habibos.thresholds.read — (key, marketplace) ceiling reader, None on unset (Plan 02-01)"
  - "habibos.logging.configure/logged_call — one-in/one-out wrapper (Plan 02-01)"
provides:
  - "habibos.tacos.parse — read+pydantic-validate a premium export artifact; FAILED -> Refusal"
  - "habibos.tacos.classify — typed TACOS-by-SKU Answer|Refusal (ratios READ, never recomputed)"
  - "scripts/answer_tacos.py — thin CLI: artifact+export-id -> JSON, explicit committed catalog, coverage_basis"
  - "tests/fixtures/profit_by_sku_30d.csv — synthetic-scaffold premium export fixture (re-pointed in Plan 03)"
  - "tests/fixtures/ca_catalog_skus.txt — explicit committed CA catalog (re-seeded in Plan 03)"
affects:
  - "02-03 Hermes skill calls scripts/answer_tacos.py after the DataDoe MCP downloads the artifact"
  - "02-03 re-points the fixture + re-seeds the catalog from the first real pull"
  - "Phases 3-5 reuse classify()/the trust-spine refusal pattern"
tech-stack:
  added: []
  patterns:
    - "Ratios READ from source columns, never recomputed (D-03 / anti-recompute grep gate)"
    - "pydantic extra='forbid' schema-drift guard — raise, never coerce (Pitfall 1)"
    - "Missing catalog SKU -> None+'no data' sentinel; empty/FAILED -> typed Refusal w/ export_id"
    - "Explicit committed catalog (never a silent export-rows fallback) with stated coverage_basis (T-02-16)"
    - "Thin CLI: argv -> habibos.* inside logged_call -> JSON stdout; no business logic, no date math"
key-files:
  created:
    - src/habibos/tacos.py
    - scripts/answer_tacos.py
    - tests/fixtures/profit_by_sku_30d.csv
    - tests/fixtures/ca_catalog_skus.txt
    - tests/test_tacos.py
  modified: []
decisions:
  - "Used pydantic BaseModel with extra='forbid' per-row to detect column drift (raise -> caller Refusal), not pl schema coercion"
  - "Strict breach compare (value > ceiling): a value EXACTLY at the ceiling flags 'ok', not 'breach' (SKU-EDGE-OK pins this)"
  - "CLI loads the committed catalog by default; export-derived catalog is a labelled last-resort only, never silently presented as D-10-satisfied"
  - "Reworded two trailing comments + the module docstring so the anti-recompute acceptance grep stays clean (no false positive on hyphens/prose)"
metrics:
  duration_min: 9
  completed: 2026-06-09
  tasks: 2
  files_created: 5
  files_modified: 0
---

# Phase 2 Plan 02: TACOS-by-SKU Money-Logic Core Summary

The phase's only hand-written money-touching code: `habibos.tacos` reads (never
recomputes) per-SKU ACOS/TACOS/ROI from the premium export columns, applies the
TACOS<=ACOS sanity guard and threshold-breach flags, emits a "no data" sentinel for
catalog SKUs absent from the export, and refuses (typed `Refusal`, with provenance) on an
empty or failed export — surfaced through a thin `scripts/answer_tacos.py` CLI that states
its catalog coverage basis explicitly and logs one event in / one event out.

## What Was Built

**Task 1 — Synthetic fixture + `tacos.py` money-logic core (TDD)** (`3bb17a9` RED, `4bfcee9` GREEN)
- `tests/fixtures/profit_by_sku_30d.csv` — a 7-row SYNTHETIC scaffold mirroring the
  documented premium columns (`seller_sku, acos, tacos, roi, ad_spend, ad_sales,
  total_sales, profit, total_cost, currency`). Rows cover every edge the tests need:
  OK rows, two breach rows (acos>30 / tacos>15), an exactly-at-ceiling row
  (`SKU-EDGE-OK` acos=30.0 / tacos=15.0 → "ok", not "breach"), and an inversion row
  (`SKU-INVERT-01` tacos 14.0 > acos 10.0 → suspect). **PERCENT** convention pinned
  (30.0, not 0.30) so the breach compare matches `acos_ceiling_pct=30` (A2). Scaffold —
  Plan 02-03 re-points it to the real captured export. No seller UUID.
- `src/habibos/tacos.py`:
  - `PREMIUM_SOURCE_ID = "57a0cb319c"`; `EXPECTED_COLUMNS` mirrors the source map.
  - `parse(artifact, status)` — `status == "FAILED"` → `Refusal("failed_export")` (D-11);
    else `pl.read_csv` the local artifact (path or bytes) and pydantic-validate each row
    via a `_PremiumRow(BaseModel, extra="forbid")` so a renamed/extra column **raises**
    (caller → Refusal) rather than being coerced (RESEARCH Pitfall 1 / T-02-07).
  - `classify(frame, export_id, window_from, window_to, catalog_skus, marketplace="CA")` —
    empty frame → `Refusal("empty_export", export_id)` (D-11); reads `acos_ceiling_pct` /
    `tacos_ceiling_pct` via `thresholds.read` (None → "no threshold set", D-08); for each
    catalog SKU, absent → `SkuRow(None,None,None,"no data","no data")` (D-10), present →
    **READ** acos/tacos/roi from the row (never recomputed, D-03), `suspect` on TACOS>ACOS
    (D-04), `_flag` for breach/ok/no-threshold-set (D-07/D-08). Rows sorted TACOS desc with
    no-data last (D-05). Returns `Answer` citing the export id (D-06 / TRUST-01).
  - The ONLY arithmetic is the two comparisons (suspect guard + breach `value > ceiling`).
- `tests/test_tacos.py` — 8 asserts-now tests (no skip; runs against the committed
  fixture): reads-not-recompute (PROF-01/D-03), units (A2), sanity guard (D-04), sort
  (D-05), no-data sentinel (D-10), empty+failed refusal (D-11), provenance (TRUST-01),
  breach/no-threshold flagging (D-07/D-08). Written RED first (ModuleNotFoundError), then GREEN.

**Task 2 — `scripts/answer_tacos.py` thin CLI + committed catalog** (`343dbed`)
- `tests/fixtures/ca_catalog_skus.txt` — explicit committed CA catalog: the 7 fixture SKUs
  PLUS `SKU-NOT-IN-EXPORT` (deliberately absent) so the D-10 "no data (not in premium
  export)" path is reachable **at runtime**, not only inside the unit test. Header marks it
  a scaffold to be re-seeded from the first real pull (Plan 03). No seller UUID.
- `scripts/answer_tacos.py` — thin wiring, no business logic. `argparse` for `--artifact`,
  `--export-id`, `--marketplace` (default CA), `--status` (default COMPLETED),
  `--window-from`/`--window-to` (threaded to `classify` **unmodified** — the CLI computes
  no dates), `--catalog` (default the committed file). Catalog source is **explicit**: load
  the committed file and set `coverage_basis = "committed catalog (<name>, <N> SKUs)"`; only
  if no catalog file exists does it derive from the export rows AS A LABELLED LAST RESORT
  (coverage_basis says so honestly) — never a silent fallback that masks D-10 (T-02-16).
  Runs `parse` then `classify` inside `logged_call("tacos_export", source_id="57a0cb319c", …)`,
  fills `row_count`/`byte_size`/`status`, and serializes the `Answer|Refusal` to JSON on
  stdout via `dataclasses.asdict` with `coverage_basis` added at top level. Exit 0 for any
  rendered result (Answer or Refusal). Returns DATA only — recommendation voice, never an
  action claim, never the seller UUID.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Anti-recompute acceptance grep false-positived on prose/comment hyphens**
- **Found during:** Task 1 verification
- **Issue:** The acceptance grep `(acos|tacos|roi)[a-z_]* *= *[^=].*[/*+-]` matched the
  module docstring line `acos = ad_spend / 14-day ad sales (%)` and two `name = value`
  lines whose **trailing comments** contained a hyphen (`# … (D-03)` / `# … refuse flag`).
  None were ratio arithmetic — they were a doc string, a `thresholds.read(...)` assignment,
  and a tuple-read of source columns.
- **Fix:** Reworded the docstring to point at `result.DEFINITIONS` (no `acos = … /` prose)
  and removed the hyphens from those two trailing comments. The grep now returns nothing;
  no logic changed.
- **Files modified:** src/habibos/tacos.py
- **Commit:** 4bfcee9

**2. [Rule 3 - Blocking] Unused import flagged by ruff**
- **Found during:** Task 1 verification
- **Issue:** `tests/test_tacos.py` imported `SkuRow` but only uses `Answer`/`Refusal`
  (rows are inspected by attribute) → ruff F401.
- **Fix:** Dropped `SkuRow` from the import. Tests still green; ruff clean.
- **Files modified:** tests/test_tacos.py
- **Commit:** 4bfcee9

## Deferred Issues

None.

## Verification Evidence

- `uv run pytest tests/test_tacos.py -q` → **8 passed**
- `uv run pytest tests/ -q` → **15 passed, 4 skipped, 1 failed** — the only failure is the
  pre-existing `test_env.py::test_seller_id_in_env_not_code`, which fails **only in the bare
  worktree** because the gitignored `.env` (holding `AMAZON_CA_SELLER_ID`) is not copied in.
  Confirmed env-only: `AMAZON_CA_SELLER_ID=… uv run pytest tests/test_env.py -q` → **1 passed**.
  The security-relevant half (no UUID literal in `src/`/`tests/`) passes regardless:
  `grep -rn '5692b95f' src/ tests/` → empty. **Not a regression from this plan** (same
  condition documented in the 02-01 SUMMARY).
- `uv run ruff check src/habibos/tacos.py scripts/answer_tacos.py tests/test_tacos.py` → **All checks passed!**
- Anti-recompute grep on `tacos.py` → **empty** (ratios READ, not recomputed).
- CLI smoke (`--artifact … --export-id exp-test-001`): exits **0**, prints JSON with
  `coverage_basis = "committed catalog (ca_catalog_skus.txt, 8 SKUs)"`, a runtime no-data
  row (`SKU-NOT-IN-EXPORT`, acos/tacos/roi null, flags "no data"), real flagged rows, and
  top row sorted by TACOS desc (`SKU-BREACH-02`, 31.0).
- Window threading: `--window-from 2026-05-10 --window-to 2026-06-09` → JSON
  `window_from`/`window_to` equal the passed values.
- Logging: a fresh run writes exactly one `tacos_export.start` + one `tacos_export.end` to
  `logs/external-calls.jsonl` (TRUST-03).
- FAILED status → JSON `code=failed_export` with `coverage_basis` present (Refusal still
  states coverage).
- Secret grep `grep -n '5692b95f' scripts/answer_tacos.py tests/fixtures/ca_catalog_skus.txt` → empty.
- Recommendation-voice grep `grep -niE 'i (changed|negated|adjusted|paused|lowered)' scripts/answer_tacos.py` → empty.

## Threat Model Coverage

| Threat ID | Disposition | Where mitigated |
|-----------|-------------|-----------------|
| T-02-05 (recomputing a ratio) | mitigate | Ratios READ from columns (D-03); anti-recompute grep empty; test_reads_ratios_from_premium asserts SkuRow == fixture column |
| T-02-06 (fabricated 0 instead of refusal/sentinel) | mitigate | classify → Refusal on empty/FAILED (D-11) + None+"no data" sentinel on missing SKU (D-10); test_empty_export_refuses + test_missing_sku_no_data |
| T-02-07 (schema/column drift) | mitigate | parse pydantic-validates (extra="forbid") and raises on mismatch, never coerces (Pitfall 1) |
| T-02-08 (percentage unit mismatch) | mitigate | Fixture pins PERCENT (30.0); test_ratio_units asserts the unit matches acos_ceiling_pct=30 |
| T-02-09 (seller UUID inlined) | mitigate | grep gates in both tasks empty; test_env.py UUID-literal scan of src/+tests/ clean |
| T-02-10 (CLI claiming an Amazon action) | mitigate | CLI returns data only; recommendation-voice grep empty; SOUL.md voice |
| T-02-16 (silent export-rows catalog fallback masking D-10) | mitigate | CLI loads an EXPLICIT committed catalog (ca_catalog_skus.txt) with a not-in-export SKU; coverage_basis stated in JSON; runtime no-data row asserted; export-derived catalog is a labelled last resort |

## TDD Gate Compliance

- RED gate: `3bb17a9` (`test(02-02): add failing tests …`) — tests failed with
  ModuleNotFoundError (`habibos.tacos`) before implementation.
- GREEN gate: `4bfcee9` (`feat(02-02): implement TACOS-by-SKU money-logic core …`).
- REFACTOR: not needed (ruff clean, code minimal; the two GREEN-commit edits were a
  blocking-gate fix folded into the GREEN commit, not a behavior refactor).

## Known Stubs

The synthetic fixture (`profit_by_sku_30d.csv`) and the committed catalog
(`ca_catalog_skus.txt`) are intentional SCAFFOLDS, explicitly labelled in their headers and
the test docstring. Plan 02-03 re-points the fixture and re-seeds the catalog from the
first real DataDoe pull. The money-logic core and CLI are fully functional — they run
end-to-end against the committed fixture today; only the data behind them is interim. This
is by-design per the plan (live pull is gated to Plan 02-03), not an unfinished stub.

## Self-Check: PASSED

All 5 created files present on disk; all 3 commits (3bb17a9, 4bfcee9, 343dbed) present in
git history.
