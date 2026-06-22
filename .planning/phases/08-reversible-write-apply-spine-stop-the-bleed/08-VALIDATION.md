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
| TBD (planner fills after waves fixed) | — | — | WRITE-03 / WRITE-06 / WRITE-07 / EXEC-01 | — | apply spine, idempotency, denylist refusal, magnitude-cap (seeded permissive) | unit | `cd engine && uv run pytest` | ❌ W0 | ⬜ pending |

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
