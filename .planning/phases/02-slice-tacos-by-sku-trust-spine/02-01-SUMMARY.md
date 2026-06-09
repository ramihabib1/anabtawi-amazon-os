---
phase: 02-slice-tacos-by-sku-trust-spine
plan: 01
subsystem: trust-spine-substrate
tags: [foundation, anti-fabrication, structlog, tomllib, tenacity, polars, pytest]
requires: []
provides:
  - "habibos.result — typed Answer/Refusal/SkuRow frozen dataclasses (trust spine)"
  - "habibos.thresholds.read — (key, marketplace) tomllib reader, missing -> None (TRUST-02)"
  - "habibos.logging.configure/logged_call — structlog one-in/one-out wrapper (TRUST-03/D-12)"
  - "habibos.datadoe.poll_status/load_artifact — tenacity poll primitive + local artifact loader (agent-MCP seam)"
  - "config/thresholds.toml seeded with CA acos_ceiling_pct=30, tacos_ceiling_pct=15 (D-09)"
  - "pythonpath=[src] + [build-system] so habibos.* is importable in tests and editable installs"
affects:
  - "02-02 tacos.py imports result, thresholds, logging"
  - "02-03 CLI/skill wires the substrate together"
  - "Phases 3-5 reuse the trust spine"
tech-stack:
  added: ["polars==1.41.2", "tenacity==9.1.4", "setuptools build-system (src layout)"]
  patterns:
    - "Typed Refusal, never None/0/swallowed exception (anti-fabrication)"
    - "Missing threshold -> None, caller refuses (never a default)"
    - "One-event-in / one-event-out structured logging on every external call"
    - "Agent calls DataDoe MCP; Python only handles the local artifact (no HTTP path)"
key-files:
  created:
    - src/habibos/__init__.py
    - src/habibos/result.py
    - src/habibos/thresholds.py
    - src/habibos/logging.py
    - src/habibos/datadoe.py
    - tests/test_thresholds.py
    - tests/test_logging.py
  modified:
    - pyproject.toml
    - uv.lock
    - .gitignore
    - config/thresholds.toml
decisions:
  - "Added [build-system]+setuptools src layout so habibos.* is importable outside pytest (acceptance criteria run `uv run python -c \"from habibos...\"`)"
  - "datadoe.py imports no HTTP library and reads only local artifacts — the agent-MCP seam is enforced structurally"
metrics:
  duration_min: 7
  completed: 2026-06-09
  tasks: 2
  files_created: 7
  files_modified: 4
---

# Phase 2 Plan 01: Trust-Spine Substrate Summary

The reusable anti-fabrication trust spine (D-02) — typed `Answer`/`Refusal`/`SkuRow`
results, a `(key, marketplace)` threshold reader that returns `None` (never a default) on
a missing ceiling, a structlog one-event-in/one-event-out `logged_call` wrapper, and a
tenacity poll primitive with a local-only artifact loader — built once in an importable
`habibos.*` package and consumed by every later TACOS-by-SKU task and Phases 3-5.

## What Was Built

**Task 1 — Wave 0 setup** (`8db02e4`)
- `uv add polars==1.41.2 tenacity==9.1.4` (both named in CLAUDE.md's locked Recommended
  Stack; uv.lock diff reviewed — only polars, polars-runtime-32, tenacity added).
- `pythonpath = ["src"]` added to `[tool.pytest.ini_options]` so tests `import habibos.*`.
- `logs/` added to `.gitignore` (the `logged_call` wrapper writes runtime
  `logs/external-calls.jsonl` — runtime output, not a tracked artifact).
- `config/thresholds.toml` seeded per D-09: `acos_ceiling_pct = 30`,
  `tacos_ceiling_pct = 15` as **numbers**; `min_margin_pct`, `days_of_cover_floor`,
  `zero_conversion_spend_trigger` left empty `""` (empty still means REFUSE). Header
  comments preserved; D-09 "operator-adopted recommendation, tune later" rationale added
  inline. Seller UUID never inlined.

**Task 2 — Trust-spine substrate (TDD)** (`3395791` RED, `2017526` GREEN)
- `src/habibos/result.py` — frozen `Refusal(reason, code, export_id=None)`,
  `SkuRow(seller_sku, acos|None, tacos|None, roi|None, acos_flag, tacos_flag, suspect=False)`
  (None ratios = "no data (not in premium export)", D-10), and
  `Answer(rows, export_id, window_from, window_to, source, definitions)` with the
  **verbatim** source-map definitions (acos = "ad_spend / 14-day ad sales, %", tacos =
  "ad_spend / total_sales, %", roi = "profit / total_cost, %"). `export_id` non-optional
  on `Answer` (provenance, D-06).
- `src/habibos/thresholds.py` — `read(key, marketplace="CA") -> float | None`; tomllib
  load on `data["marketplace"][marketplace][key]`; empty `""`, `None`, or absent
  key/marketplace returns `None` (TRUST-02/D-08), otherwise `float(value)`. Never a default.
- `src/habibos/logging.py` — `configure()` builds a structlog JSON pipeline writing to
  `LOG_PATH` (read at call time so tests can monkeypatch a temp file);
  `logged_call(op, **start_fields)` emits exactly one `<op>.start` and one `<op>.end`
  (with row_count/byte_size/duration_ms/status), and on exception still emits `.end` with
  `status="error"` + error repr and **re-raises** (TRUST-03 — never swallowed). `# noqa: BLE001`.
- `src/habibos/datadoe.py` — `poll_status(get_status)` tenacity-retried, terminal on BOTH
  `COMPLETED` and `FAILED` (`stop_after_attempt(20)`, `wait_exponential_jitter`) so a
  FAILED export is never retried forever (T-02-04); `load_artifact(path|bytes)` reads a
  **local** artifact only — no HTTP library imported (agent-MCP seam).
- `tests/test_thresholds.py` + `tests/test_logging.py` — written RED first (failed with
  ModuleNotFoundError), then GREEN. Follow the repo test convention (req-ID docstring
  header, `from __future__ import annotations`, assemble the UUID prefix at runtime).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Package not importable outside pytest**
- **Found during:** Task 2 (acceptance criteria `uv run python -c "from habibos..."`)
- **Issue:** `pythonpath=["src"]` makes `habibos` importable under pytest only; the bare
  `uv run python -c "from habibos.result import ..."` acceptance checks failed with
  ModuleNotFoundError because nothing put `src/` on the interpreter path outside pytest.
- **Fix:** Added `[build-system]` (setuptools) + `[tool.setuptools.packages.find] where=["src"]`
  so `uv sync` installs `habibos` editable. RESEARCH line 213 explicitly anticipated this
  ("Add `[build-system]` or rely on uv's editable src layout").
- **Files modified:** pyproject.toml, uv.lock
- **Commit:** 2017526

**2. [Rule 3 - Blocking] `grep httpx` acceptance gate matched docstring prose**
- **Found during:** Task 2
- **Issue:** The acceptance check `grep -rn 'httpx|requests|urllib' src/habibos/datadoe.py`
  must return nothing, but the original docstring named those libraries in prose ("never
  imports httpx/requests/urllib").
- **Fix:** Reworded the docstring to "imports no HTTP library" — same meaning, no literal
  match. No HTTP library is imported anywhere in the module.
- **Files modified:** src/habibos/datadoe.py
- **Commit:** 2017526

## Deferred Issues

None.

## Verification Evidence

- `uv run pytest tests/test_thresholds.py tests/test_logging.py -q` → **6 passed**
- `uv run pytest tests/ -q` (with `.env` present) → **8 passed, 4 skipped** (the 4 skips are
  pre-existing Supabase tests gated on plan 01-02; no regression)
- `uv run ruff check src/ tests/test_thresholds.py tests/test_logging.py` → **All checks passed!**
- `grep -rn 'httpx\|requests\|urllib' src/habibos/datadoe.py` → empty (agent-MCP seam honored)
- `grep -rn '5692b95f' src/ tests/` → empty (no inlined seller UUID, V7/V8)
- Imports/frozen-dataclass acceptance one-liners → `imports ok` / `frozen ok`

### Note on `test_env.py` in the worktree

`tests/test_env.py::test_seller_id_in_env_not_code` asserts `AMAZON_CA_SELLER_ID` is loaded
from `.env`. The gitignored `.env` is not copied into the isolated worktree, so this test
fails **only** in the bare worktree for environmental reasons. With `.env` present (as in
the main checkout) the full suite is 8 passed / 4 skipped. The security-relevant half of
that test (no UUID literal in `src/`) passes regardless. Not a regression from this plan.

## Threat Model Coverage

| Threat ID | Disposition | Where mitigated |
|-----------|-------------|-----------------|
| T-02-01 (threshold defaulting) | mitigate | `thresholds.read` returns None on ""/absent; test_thresholds::test_missing_threshold_returns_none |
| T-02-02 (secret in log) | mitigate | logged_call never emits a secret; test_logging::test_no_secret_in_log; logs/ gitignored |
| T-02-03 (swallowed error) | mitigate | logged_call re-raises + emits .end with error; test_logging::test_end_event_on_exception |
| T-02-04 (unbounded poll on FAILED) | mitigate | poll_status terminal on COMPLETED+FAILED via tenacity |
| T-02-SC (supply chain) | accept | polars/tenacity from CLAUDE.md locked stack; uv.lock diff reviewed clean |

## TDD Gate Compliance

- RED gate: `3395791` (`test(02-01): add failing tests ...`) — both tests failed with
  ModuleNotFoundError before implementation.
- GREEN gate: `2017526` (`feat(02-01): implement habibos trust-spine substrate ...`).
- REFACTOR: not needed (ruff clean, code minimal).

## Known Stubs

None. `poll_status` is a documented, fully-functional reusable poll primitive that is not
on this phase's critical path (the agent polls via the MCP) — it is not a stub.

## Self-Check: PASSED

All 9 created/modified files present on disk; all 4 commits (8db02e4, 3395791, 2017526,
4dee93c) present in git history.
