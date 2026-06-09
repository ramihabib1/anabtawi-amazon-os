---
phase: 2
slug: slice-tacos-by-sku-trust-spine
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-09
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> See `02-RESEARCH.md` → ## Validation Architecture for how each success criterion is provable against real data.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 (harness already scaffolded in `tests/`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (uv env in place; `pythonpath=["src"]` added Wave 0) |
| **Quick run command** | `uv run pytest -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5–15 seconds (unit + fixture-based) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Populated from each PLAN.md `<verify><automated>` command. The 5 autonomous tasks across the
> 3 plans each carry an automated verify; the 3 checkpoint tasks in Plan 02-03 are manual-only
> (see Manual-Only Verifications). Each money-touching primitive (ratio surfacing, sanity guard,
> threshold flag, refusal/no-data) gets a unit test against the export fixture per CLAUDE.md
> ("runs against a real DataDoe export").

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01 T1 | 02-01 | 1 | TRUST-02 (seed) | T-02-01 | Seeded ceilings as numbers; pythonpath/gitignore set; no defaults baked in | config/setup | `uv run python -c "import polars,tenacity,tomllib; d=tomllib.load(open('config/thresholds.toml','rb')); m=d['marketplace']['CA']; assert m['acos_ceiling_pct']==30 and m['tacos_ceiling_pct']==15; print('thresholds ok')" && grep -A4 '[tool.pytest.ini_options]' pyproject.toml | grep -E 'pythonpath\s*=\s*\[.*"src".*\]' && grep -q '^logs/' .gitignore && echo "wave0 ok"` | ✅ | ⬜ pending |
| 02-01 T2 | 02-01 | 1 | TRUST-02, TRUST-03 | T-02-01, T-02-02, T-02-03, T-02-04 | Missing threshold→None (refuse, never default); one-in/one-out logging; no secret in log | unit | `uv run pytest tests/test_thresholds.py tests/test_logging.py -x -q && uv run python -c "from habibos.result import Answer; from habibos.thresholds import read; from habibos.logging import logged_call; from habibos.datadoe import poll_status, load_artifact; print('ok')"` | ❌ W0 | ⬜ pending |
| 02-02 T1 | 02-02 | 2 | PROF-01, TRUST-01 | T-02-05, T-02-06, T-02-07, T-02-08 | Ratios read not recomputed; no-data sentinel; empty/failed→Refusal; units pinned | unit | `uv run pytest tests/test_tacos.py -x -q` | ❌ W0 | ⬜ pending |
| 02-02 T2 | 02-02 | 2 | PROF-01, TRUST-01, TRUST-03 | T-02-09, T-02-10, T-02-16 | Explicit committed catalog (D-10 reachable); coverage_basis stated; one-in/one-out log; no UUID; no action-claim | integration | `uv run python scripts/answer_tacos.py --artifact tests/fixtures/profit_by_sku_30d.csv --export-id exp-test-001 --marketplace CA | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('coverage_basis'), 'coverage_basis missing'; assert d.get('export_id')=='exp-test-001' or d.get('code'); rows=d.get('rows') or []; assert any(r.get('acos') is None and r.get('acos_flag')=='no data' for r in rows) or d.get('code'), 'D-10 no-data row not reachable'; print('cli ok')"` | ❌ W0 | ⬜ pending |
| 02-03 T1 | 02-03 | 3 | DATA-05, PROF-01, TRUST-04 | T-02-13, T-02-14 | SKILL.md drives MCP seam (groupBy, raw_download); env-var not literal UUID; recommendation voice | static/skill | `test -f ~/.hermes/skills/tacos-by-sku/SKILL.md && grep -q 'groupBy seller_sku' ~/.hermes/skills/tacos-by-sku/SKILL.md && grep -q 'answer_tacos.py' ~/.hermes/skills/tacos-by-sku/SKILL.md && [ "$(grep -c '5692b95f' ~/.hermes/skills/tacos-by-sku/SKILL.md)" = "0" ] && { command -v skills-ref >/dev/null 2>&1 && skills-ref validate ~/.hermes/skills/tacos-by-sku || echo "skills-ref unavailable — fallback: manual frontmatter review"; } && echo "skill ok"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

> Checkpoint tasks 02-03 T2 (MCP wiring), T3 (live pull + lock A1/A2/A3 + re-point fixture/catalog),
> and T4 (TRUST-04 Seller-Central spot-check) are `checkpoint:human-verify` — manual-only, listed below.

---

## Wave 0 Requirements

- [x] `pythonpath = ["src"]` added to `[tool.pytest.ini_options]` (02-01 T1) so `habibos.*` is importable
- [x] `logs/` gitignored (02-01 T1) for the structlog audit file
- [ ] `uv add polars==1.41.2 tenacity==9.1.4` — locked-stack libs (02-01 T1, per RESEARCH §Package Legitimacy Audit)
- [ ] `tests/test_thresholds.py` + `tests/test_logging.py` — trust-spine unit tests (02-01 T2)
- [ ] `tests/fixtures/profit_by_sku_30d.csv` — synthetic scaffold first (02-02 T1), re-pointed to the real capture once the MCP connection is live (02-03 T3)
- [ ] `tests/fixtures/ca_catalog_skus.txt` — explicit committed CA catalog (02-02 T2) so the D-10 not-in-export path is reachable at runtime; re-seeded from the real catalog at the first live pull (02-03 T3)
- [ ] `tests/test_tacos.py` — money-logic unit tests against the fixture (02-02 T1)

*Existing `tests/` harness (conftest, test_config_seed, test_env, test_schema, test_context) covers foundation; new money-touching primitives extend it.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DataDoe MCP wired into Hermes runtime | DATA-05 (precondition) | `~/.hermes/config.yaml` `servers:` empty; registration is an operator step in the Hermes app | 02-03 T2: `hermes mcp add`, `hermes mcp list` shows DataDoe, `hermes mcp test datadoe` responds |
| Live "what's my TACOS by SKU" pull returns correct per-SKU ratios; A1/A2/A3 locked | PROF-01, DATA-05 | Connection-gated live pull; A1 server-side aggregation confirmed at first real pull | 02-03 T3: ask in the Hermes workspace; confirm export-id cited, ~30 CA SKUs render, groupBy server-side ratio (A1), percent convention (A2), raw_download (A3); re-point fixture + re-seed catalog; `uv run pytest tests/test_tacos.py -q` green |
| Spot-check answer against Seller Central, signed off | TRUST-04 / Criterion 5 | Requires human cross-reference to Seller Central; no marketplace bleed | 02-03 T4: compare 3–5 SKUs' ACOS/TACOS against Seller Central; confirm match and CA-only scope |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (5 autonomous tasks mapped; 3 checkpoints are manual-only)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
