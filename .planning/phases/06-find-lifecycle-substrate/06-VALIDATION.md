---
phase: 6
slug: find-lifecycle-substrate
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-20
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `06-RESEARCH.md` → "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥9.0.3 (verified `engine/pyproject.toml`) |
| **Config file** | `engine/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["src"]`) |
| **Quick run command** | `cd engine && uv run pytest tests/test_lifecycle.py tests/test_find_cache.py -x` |
| **Full suite command** | `cd engine && uv run pytest` |
| **Estimated runtime** | < 5s quick · ~full suite (16+new passed / 5 skipped) |

---

## Sampling Rate

- **After every task commit:** Run `cd engine && uv run pytest tests/test_lifecycle.py tests/test_find_cache.py -x` (< 5s)
- **After every plan wave:** Run `cd engine && uv run pytest` (full suite must stay green)
- **Before `/gsd:verify-work`:** Full suite green + the one live read-only MCP confirmation (Success Criterion 4)
- **Max feedback latency:** < 5 seconds (quick run)

---

## Per-Task Verification Map

| Requirement | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|-------------|----------|------------|-----------|-------------------|-------------|--------|
| WRITE-01 | Clean dryRun (`status==VALIDATED`, `validation.valid`, no issues) classifies PROCEED | — | unit (fixture) | `pytest tests/test_lifecycle.py::test_dryrun_validated_proceeds -x` | ❌ W0 | ⬜ pending |
| WRITE-01 | `valid:false`/non-empty-issues dryRun classifies STOP and surfaces issues verbatim | — | unit (fixture) | `pytest tests/test_lifecycle.py::test_dryrun_invalid_stops -x` | ❌ W0 | ⬜ pending |
| WRITE-05 | `COMPLETED` → terminal success; `PENDING/IN_PROGRESS/WAITING_EXTERNAL_PROCESSING` → in-flight | — | unit (fixture) | `pytest tests/test_lifecycle.py::test_poll_terminal_classification -x` | ❌ W0 | ⬜ pending |
| WRITE-05 | `ERROR/CANCELED/BLOCKED_*` → terminal failure, surfaces error message cleanly | — | unit (fixture) | `pytest tests/test_lifecycle.py::test_poll_error_surfaces_message -x` | ❌ W0 | ⬜ pending |
| WRITE-05 | Unmodeled status → typed refusal, NOT assumed terminal nor infinite-polled | — | unit | `pytest tests/test_lifecycle.py::test_unknown_status_refuses -x` | ❌ W0 | ⬜ pending |
| WRITE-05 | `ACTION_TERMINAL` set matches verified enum verbatim (Success Criterion 4) | — | unit | `pytest tests/test_lifecycle.py::test_action_terminal_enum_pinned -x` | ❌ W0 | ⬜ pending |
| WRITE-05 | Code refuses to treat a ≤24h DataDoe export as reconciliation confirmation | — | unit | `pytest tests/test_lifecycle.py::test_export_not_confirmation -x` | ❌ W0 | ⬜ pending |
| WRITE-02 | FIND result writes `data/ads_*_find_*.json`; a cached ID looks up HIT | — | unit (tmp_path) | `pytest tests/test_find_cache.py::test_find_write_and_lookup -x` | ❌ W0 | ⬜ pending |
| WRITE-02 | Non-cached ID → `Refusal("stale/missing entity ID")` at build (FIND-before-write enforced) | — | unit | `pytest tests/test_find_cache.py::test_uncached_id_refuses -x` | ❌ W0 | ⬜ pending |
| WRITE-01/05 | Each `actions_start`/`actions_get` op wraps `logged_call` → one `.start`+`.end`, no seller UUID | T-06-01 | unit (tmp log) | `pytest tests/test_lifecycle.py::test_ops_logged_no_secret -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_lifecycle.py` — covers WRITE-01, WRITE-05 (dryRun + poll classification, enum pinning, export-not-confirmation, logging)
- [ ] `tests/test_find_cache.py` — covers WRITE-02 (cache write/read + miss-refuses-at-build)
- [ ] `tests/fixtures/dryrun_validated.json`, `dryrun_invalid.json` — captured dryRun responses
- [ ] `tests/fixtures/actions_get_completed.json`, `actions_get_error.json` — captured poll responses (one terminal-success, one `ERROR`)
- [ ] `tests/fixtures/campaigns_find.json` — seed from `data/ads_sp_campaigns_live_2026-06-20.json` (shape already verified)
- [ ] No framework install needed — pytest is present and green.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `actions_get` / `actions_details_schema_get` MCP response shape + terminal-status enum confirmed against live | WRITE-05 / Success Criterion 4 | Read-only live MCP call; cannot be unit-tested against a fixture without first capturing the live shape | Executor (agent, not pytest) runs `actions_details_schema_get` and one `actions_get` against a known prior `actionId`; confirms the enum matches the pinned `ACTION_TERMINAL` set and captures the response into the fixtures above |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

> `wave_0_complete` stays `false` until execution lands the Wave 0 (06-01) RED tests + sanitized fixtures.

**Approval:** approved 2026-06-21 (planning-time; sign-off completes at execution)
