---
phase: 7
slug: margin-tiered-safety-gate
status: draft
nyquist_compliant: true
wave_0_complete: false  # Wave 1 holds the RED scaffold (07-01); set true after 07-01 lands
created: 2026-06-21
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via `uv`) |
| **Config file** | `engine/pyproject.toml` |
| **Quick run command** | `cd engine && uv run pytest tests/test_gate.py -q` |
| **Full suite command** | `cd engine && uv run pytest` |
| **Estimated runtime** | ~5–15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd engine && uv run pytest tests/test_gate.py -q`
- **After every plan wave:** Run `cd engine && uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

> Populated by the planner from PLAN.md task IDs. Every money-touching task (margin
> computation, ceiling derivation, projected-TACOS check, refusal grammar) MUST map to a
> `test_gate.py` unit test — money logic is hand-written + tested, never prose (CLAUDE.md
> hard rule 3).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | GATE-01..05 | T-07-01/02 | typed contracts; frozen verdicts | unit | `cd engine && uv run python -c "from habibos.result import ProposedAction, GateRefusal, GateVerdict"` | ❌ W1 | ⬜ pending |
| 07-01-02 | 01 | 1 | GATE-01..05 | T-07-01/02 | RED contract; back-out asserted vs fixture | unit | `cd engine && uv run pytest tests/test_gate.py -q` (RED) | ❌ W1 | ⬜ pending |
| 07-01-03 | 01 | 1 | GATE-02 | T-07-04 | empty-key refusal repoint | unit | `cd engine && uv run pytest tests/test_thresholds.py::test_missing_threshold_returns_none -q` | ❌ W1 | ⬜ pending |
| 07-02-01 | 02 | 1 | GATE-05 | T-07-03 | catalog = single source; remnants omitted | unit | `cd engine && uv run python -c "import tomllib; tomllib.load(open('engine/config/sku_catalog.toml','rb'))"` | ❌ W1 | ⬜ pending |
| 07-02-02 | 02 | 1 | GATE-02 | T-07-04 | seed floor=15; edge fixtures | unit | `cd engine && uv run pytest tests/test_thresholds.py::test_missing_threshold_returns_none -q` | ❌ W1 | ⬜ pending |
| 07-03-01 | 03 | 2 | GATE-01 | T-07-07 | pre-ad CM% back-out (D-03) | unit | `cd engine && uv run pytest tests/test_gate.py::test_contribution_margin_pre_ad tests/test_gate.py::test_profit_is_post_ad_addback -q` | ❌ W2 | ⬜ pending |
| 07-03-02 | 03 | 2 | GATE-02..05 | T-07-06/08/09 | branch order; refuse never clamp/default | unit | `cd engine && uv run pytest tests/test_gate.py -q` | ❌ W2 | ⬜ pending |
| 07-03-03 | 03 | 2 | GATE-01..05 | — | full-suite regression | unit | `cd engine && uv run pytest` | ❌ W2 | ⬜ pending |
| 07-04-01 | 04 | 3 | GATE-03/04/05 | T-07-11/12/13 | thin CLI; refusal serializes as refusal; no UUID | unit | `cd engine && uv run python scripts/gate_action.py --artifact tests/fixtures/profit_by_sku_30d.csv --export-id x --sku EU-Z87B-ZRBZ --action-type pause --delta-spend -5` | ❌ W3 | ⬜ pending |
| 07-04-02 | 04 | 3 | GATE-03/04/05 | T-07-11 | JSON verdict/refusal contract locked | unit | `cd engine && uv run pytest tests/test_gate_action.py -q` | ❌ W3 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `engine/tests/test_gate.py` — failing test stubs for GATE-01..GATE-05 (margin compute, ceiling derivation, projected-TACOS pass/refuse, empty-floor refusal, SKU-not-in-catalog refusal)
- [ ] `engine/tests/test_thresholds.py` — repoint the `min_margin_pct → None` assertion (line 31) to a still-empty key after the D-07a `min_net_margin_pct` rename + `=15` seed
- [ ] Reuse existing `engine/tests/conftest.py` fixtures + `tests/fixtures/` premium-export fixtures (incl. the `ad_spend`-only edge fixture proving the POST-ad back-out)

*Existing pytest infrastructure covers the framework; no install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification — the gate is a pure, testable function over typed inputs (no Amazon write, no network in this phase).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
