---
phase: 7
slug: margin-tiered-safety-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 7-01-01 | 01 | 0 | GATE-01 | — | N/A | unit | `cd engine && uv run pytest tests/test_gate.py -q` | ❌ W0 | ⬜ pending |

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
