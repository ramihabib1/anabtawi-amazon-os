---
phase: 8
slug: reversible-write-apply-spine-stop-the-bleed
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-22
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `08-RESEARCH.md` → "## Validation Architecture". The planner refines the
> Per-Task Verification Map once plans + waves are fixed.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (engine/, `uv run pytest`) |
| **Config file** | engine/pyproject.toml |
| **Quick run command** | `cd engine && uv run pytest -q` |
| **Full suite command** | `cd engine && uv run pytest` |
| **Estimated runtime** | ~under 30 seconds (engine suite, no network — DataDoe I/O is the agent's, not Python's) |

---

## Sampling Rate

- **After every task commit:** Run `cd engine && uv run pytest -q`
- **After every plan wave:** Run `cd engine && uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01·T2 | 08-01 | 0 | WRITE-03 (Open Q2) | T-08-03 | ProposedAction optional fields keep the Phase-7 gate CLI contract green; AppliedResult typed positive | unit | `cd engine && uv run pytest tests/test_gate_action.py tests/test_gate.py -x` | ✅ extends result.py | ⬜ pending |
| 08-01·T3 | 08-01 | 0 | WRITE-03 / WRITE-06 / WRITE-07 / EXEC-01 | T-08-01 | RED-on-import contracts for spine/ledger/denylist/cap; no fabricated payload, no seller UUID | unit (RED) | `cd engine && uv run pytest tests/test_apply.py tests/test_ledger.py tests/test_denylist.py tests/test_magnitude_cap.py` (expect RED on missing modules) | ❌ W0 (creates test_apply/test_ledger/test_denylist/test_magnitude_cap + extends test_find_cache) | ⬜ pending |
| 08-02·T1 | 08-02 | 1 | WRITE-07 | T-08-04 / T-08-06 | content-hash idempotency keyed entity+action+params NOT date; COMPLETED→no-op, in-flight→resume | unit | `cd engine && uv run pytest tests/test_ledger.py -x` | ❌ W0 (test_ledger green target) | ⬜ pending |
| 08-02·T2 | 08-02 | 1 | EXEC-01 | T-08-05 | own-ASIN hard GateRefusal(own_asin_denied) pre-dryRun; owned set from dedicated owned_asins.toml (D-06a) | unit | `cd engine && uv run pytest tests/test_denylist.py -x` | ❌ W0 (test_owned_set_from_dedicated_source green target) | ⬜ pending |
| 08-02·T3 | 08-02 | 1 | SC-5 (D-02) / A2 | T-08-07 / T-08-08 | magnitude cap refuses over_cap (never clamps) when set, seeded permissive when absent; A2 stale_find_cache refusal | unit | `cd engine && uv run pytest tests/test_magnitude_cap.py tests/test_find_cache.py -x` | ❌ W0 (test_magnitude_cap + test_stale_cache_refused green target) | ⬜ pending |
| 08-03·T1 | 08-03 | 2 | WRITE-03 / EXEC-01 | T-08-10 / T-08-12 / T-08-13 | spine branch-order short-circuit; dryRun STOP never fires start_apply; poll-to-terminal; FIND-echo field-equality confirm | unit | `cd engine && uv run pytest tests/test_apply.py -k "not logs and not canary" -x` | ❌ W0 (test_apply spine cases green target) | ⬜ pending |
| 08-03·T2 | 08-03 | 2 | WRITE-06 / WRITE-03 | T-08-11 / T-08-14 / T-08-15 | one-time canary marker gates first apply; every applied write (incl. auto) logs decisions.md + brain note w/ actionId, no seller UUID | unit | `cd engine && uv run pytest tests/test_apply.py -k "canary or logs" -x` | ❌ W0 (test_canary_one_time_confirm + test_apply_logs_decision_and_brain green target) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `engine/tests/test_apply.py` — RED stubs for the apply spine (build → denylist → margin → dryRun → apply → poll → FIND-echo → log) (WRITE-03)
- [ ] `engine/tests/test_ledger.py` — RED stubs for content-hash idempotency + in-flight resume (WRITE-07)
- [ ] `engine/tests/test_denylist.py` — RED stubs for owned-ASIN hard-refusal pre-dryRun (EXEC-01)
- [ ] `engine/tests/test_magnitude_cap.py` — RED stubs for the bounded-% mechanism seeded permissive (SC-5 / D-02)
- [ ] Sanitized DataDoe `actions_*` fixtures (pause / negative-create / bid-down dryRun + poll responses) under `engine/tests/fixtures/`
- [ ] decisions.md + brain/raw logging-seam assertion (WRITE-06)

*Existing infrastructure (Phase 6/7) covers lifecycle, find_cache, gate, datadoe, logging — reused, not rebuilt.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The canary first-apply lands COMPLETED against the live account | WRITE-03 | Requires the org-enabled Ads action types + a real `actions_start dryRun:false`; cannot run in CI | Operator clears the DataDoe Settings→Actions org-enable precondition, runs the canary CLI with the one-time confirm, observes `actions_get` → COMPLETED + FIND echo |
| The stop-the-bleed batch flips ~$279/mo off the 4 dead-SKU campaigns | EXEC-01 | Live account write; verified in console + `actions_get`, never via ≤24h DataDoe export | After canary confirms, run the batch; reconcile each pause via `actions_get` COMPLETED |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
