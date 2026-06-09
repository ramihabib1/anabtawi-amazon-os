---
phase: 1
slug: foundation
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-08
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (locked dev dep; install via `uv add --dev pytest`) |
| **Config file** | none yet — Wave 0 creates `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10–30 seconds (schema integration tests dominate) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite green + `docs/datadoe-source-map.md` complete + `config` seeded + `hermes mcp test` transcripts captured
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| CONN-02 | `.env` carries `AMAZON_CA_SELLER_ID`, never inlined in source | unit | `uv run pytest tests/test_env.py::test_seller_id_in_env_not_code -x` | ❌ Wave 0 |
| DATA-01 | All 5 tables exist after `alembic upgrade head`; `vector` extension present | integration | `uv run pytest tests/test_schema.py::test_tables_and_vector_ext -x` | ❌ Wave 0 |
| DATA-02 | `metric_snapshots` unique on `(marketplace, seller_sku, snapshot_date)`; has `captured_at`, `datadoe_export_id` | integration | `uv run pytest tests/test_schema.py::test_snapshot_idempotency_key -x` | ❌ Wave 0 |
| DATA-03 | `cogs` SCD columns + per-row FX present; `(marketplace, seller_sku, effective_from)` unique | integration | `uv run pytest tests/test_schema.py::test_cogs_scd_fx -x` | ❌ Wave 0 |
| DATA-04 | `config` non-empty after seed; keyed `(key, marketplace)`; required threshold keys present | integration | `uv run pytest tests/test_config_seed.py::test_required_thresholds_seeded -x` | ❌ Wave 0 |
| CTX-01/02 | `SOUL.md` + `business-context.md` exist, are non-stub, deployed to `~/.hermes` | unit | `uv run pytest tests/test_context.py::test_soul_and_context_deployed -x` | ❌ Wave 0 |
| CONN-01 | Each MCP connection (DataDoe, Supabase, Gmail/Drive) responds; DataDoe confirmed read-only | manual | `hermes mcp test <name>` — capture transcript | manual (live MCP) |
| CONN-03 | DataDoe source map recorded empirically (columns, SP/SB/SD scope, tz basis, premium availability) | manual | `exports_sources_get` → inspect `docs/datadoe-source-map.md` | manual (live MCP) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> **Deferred-verify (sampling continuity) note — DATA-01/02/03:** Plan 01-02 Task 1 authors the schema and its `<automated>` verify is the *offline* `uv run alembic upgrade head --sql` (the migration compiles / renders clean DDL with no DB write). The full live schema assertions (`tests/test_schema.py::test_tables_and_vector_ext` / `::test_snapshot_idempotency_key` / `::test_cogs_scd_fx`) fire in plan 01-02 Task 3, *after* the blocking live push in 01-02 Task 2. This split is intentional, not a gap: the live push is a `checkpoint:human-action` blocking gate that cannot run mid-auto-task, so the introspection tests are sampled the moment the live DB exists. Sampling continuity holds — every task carries an automated verify, and no three consecutive tasks lack one.

---

## Wave 0 Requirements

- [ ] `pyproject.toml [tool.pytest.ini_options]` + `uv add --dev pytest` — framework not yet present
- [ ] `tests/conftest.py` — fixture spinning up a test Postgres (or a disposable Supabase schema) for schema/seed integration tests
- [ ] `tests/test_schema.py` — DATA-01/02/03 (post-`alembic upgrade` introspection)
- [ ] `tests/test_config_seed.py` — DATA-04 (required thresholds present, non-empty)
- [ ] `tests/test_env.py` — CONN-02 (UUID in `.env`, not in source)
- [ ] `tests/test_context.py` — CTX-01/02 (SOUL.md non-stub + deployed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| MCP connections respond; DataDoe read-only | CONN-01 | Depends on live MCP wiring + operator confirmation; `config.yaml servers:` currently empty | Run `hermes mcp list` then `hermes mcp test <name>` for DataDoe, Supabase, Gmail/Drive; capture transcripts |
| DataDoe source map complete | CONN-03 | Source IDs/columns/timezone/premium-availability are execution-time empirical, must not be guessed | Run `exports_sources_get`; record each confirmed source into `docs/datadoe-source-map.md`; verify premium "Profit by SKU & Date" enablement |
| `config` thresholds reflect operator's REAL values | DATA-04 | Real thresholds are blocking operator input — empty/placeholder config is forbidden | Operator supplies min margin %, ACOS ceiling, days-of-cover; confirm seeded values match operator-stated numbers |
| Backup target + cadence decided/documented | CTX-03 | Policy decision (Mac-awake-only constraint); native `hermes backup` path | Document backup target + schedule; verify `hermes backup --quick` round-trips via `hermes import` |

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-08
