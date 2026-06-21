---
phase: 06-find-lifecycle-substrate
plan: 01
subsystem: engine (actions lifecycle + FIND-cache substrate)
tags: [write-path, actions-lifecycle, find-cache, wave-0, tdd-red, secret-hygiene]
requires:
  - engine/src/habibos/datadoe.py (export TERMINAL/poll_status, tenacity config)
  - engine/src/habibos/result.py (Refusal)
  - engine/src/habibos/logging.py (logged_call)
  - engine/tests/test_env.py (UUID secret scan)
provides:
  - datadoe.ACTION_TERMINAL + ACTION_IN_FLIGHT/SUCCESS/PARTIAL/FAIL + poll_action_status
  - result.Proceed + result.PollOutcome typed results
  - test_env.py SCAN_SUFFIXES now covers .json
  - test_lifecycle.py (8 RED cases) + test_find_cache.py (2 RED cases) — the contract for Plans 02/03
  - five sanitized fixtures + one FIND cache seed
affects:
  - Plan 02 (habibos.lifecycle implements classify_dryrun/classify_poll/classify_poll_logged)
  - Plan 03 (habibos.find_cache implements write/lookup with DATA_DIR)
  - Phase 8 apply spine (poll_action_status drives the in-flight->terminal loop)
tech-stack:
  added: []
  patterns: [typed-result-anti-fabrication, tenacity-poll-primitive, logged_call-one-in-one-out, repo-root-relative-paths]
key-files:
  created:
    - engine/tests/test_lifecycle.py
    - engine/tests/test_find_cache.py
    - engine/tests/fixtures/campaigns_find.json
    - engine/tests/fixtures/dryrun_validated.json
    - engine/tests/fixtures/dryrun_invalid.json
    - engine/tests/fixtures/actions_get_completed.json
    - engine/tests/fixtures/actions_get_error.json
    - data/ads_campaigns_find_2026-06-20.json
  modified:
    - engine/src/habibos/datadoe.py
    - engine/src/habibos/result.py
    - engine/tests/test_env.py
decisions:
  - "Pin actions_get terminal enum verbatim from the live spec (no FAILED; CANCELED one-L) — a wrong enum causes an infinite poll"
  - "campaigns_find.json is spec-derived from the pinned ActionAdsCampaignsFindResult shape (the live capture data/ads_sp_campaigns_live_2026-06-20.json was absent from the worktree)"
  - "dryRun fixtures are spec-derived pending the Plan 04 live read-only eyeball"
metrics:
  tasks-completed: 4
  files-created: 8
  files-modified: 3
  completed: 2026-06-21
requirements: [WRITE-01, WRITE-02, WRITE-05]
---

# Phase 6 Plan 01: FIND + Lifecycle Substrate Summary

Pinned the verified `actions_get` terminal-status enum and the `poll_action_status` poll
primitive into `datadoe.py`, added the typed `Proceed`/`PollOutcome` results, extended
`test_env.py`'s secret scan to cover committed JSON, and laid the Wave 0 RED contract
(`test_lifecycle.py` 8 cases + `test_find_cache.py` 2 cases) with five sanitized fixtures and
one FIND cache seed — the executable contract Plans 02/03 implement against.

## What Was Built

### Task 1 — `datadoe.ACTION_*` enum + `poll_action_status`; `result.Proceed`/`PollOutcome` (5eb454a)
- `datadoe.py`: added `ACTION_IN_FLIGHT`, `ACTION_TERMINAL_SUCCESS`, `ACTION_TERMINAL_PARTIAL`,
  `ACTION_TERMINAL_FAIL`, and `ACTION_TERMINAL` (their union) PINNED VERBATIM from the live
  spec with a `# verified against api.datadoe.com/api/v1/docs/json 2026-06-20` source comment.
  There is NO `FAILED` (it is `ERROR`) and `CANCELED` is one-L. Added `_action_not_terminal`
  and `poll_action_status` reusing the EXACT tenacity config of `poll_status`
  (`stop_after_attempt(20)`, `wait_exponential_jitter`, `retry_if_result`). The export
  `TERMINAL = {"COMPLETED", "FAILED"}` and `poll_status` are untouched.
- `result.py`: added frozen `Proceed(action_type)` and
  `PollOutcome(status, state, issues=[])` (`state` ∈ `done | done_with_issues | in_flight`).
  `Refusal`, `SkuRow`, `Answer`, `DEFINITIONS`, `PREMIUM_SOURCE` unchanged.

### Task 1b — `test_env.py` secret scan covers `.json` (d283c36)
- Added `".json"` to `SCAN_SUFFIXES`. The standing UUID secret-scan now walks committed
  `tests/**/*.json` fixtures/cache files (it did NOT before — a UUID-bearing fixture would
  have passed silently). One-token additive change; scan loop, `TRACKED_SOURCE_DIRS`, UUID
  assembly unchanged. The T-06-01 mitigation can now legitimately cite `test_env.py`.

### Task 2 — five sanitized fixtures + FIND cache seed (144e6e9)
- `tests/fixtures/campaigns_find.json` — `ActionAdsCampaignsFindResult` shape
  (`{campaigns:[…]}`, item keys `campaignId, name, adProduct, state, budgets,
  optimizations, status`).
- `dryrun_validated.json` / `dryrun_invalid.json` — `ActionStartResponse`
  (`status:"VALIDATED"`, nested `validation.valid` + `issues[{path,code,message}]`).
- `actions_get_completed.json` / `actions_get_error.json` — `ActionStatusResponse`
  (`COMPLETED`; `ERROR` + `ActionExecutionErrorResult{status,code,message}`), with
  `AMAZON_ADS_`-prefixed type strings and non-UUID placeholder action IDs.
- `data/ads_campaigns_find_2026-06-20.json` — the FIND cache seed Plan 03 reads.
- No seller UUID anywhere (`grep -rl 5692b95f tests/fixtures/ data/…` returns nothing — the
  named, sole automated guard for these files).

### Task 3 — failing contract tests, RED (d553bd0)
- `test_lifecycle.py` (8): `test_action_terminal_enum_pinned`, `test_dryrun_validated_proceeds`,
  `test_dryrun_invalid_stops`, `test_poll_terminal_classification`,
  `test_poll_error_surfaces_message`, `test_unknown_status_refuses`,
  `test_export_not_confirmation`, `test_ops_logged_no_secret`.
- `test_find_cache.py` (2): `test_find_write_and_lookup`, `test_uncached_id_refuses`.
- Both import `from habibos import lifecycle` / `find_cache` (not yet existing) → RED on
  `ImportError: cannot import name 'lifecycle'/'find_cache'`, the intended Wave 0 state. No
  UUID literal in either file.

## Deviations from Plan

### [Rule 3 - Blocking issue] Live CAMPAIGNS_FIND capture absent from worktree
- **Found during:** Task 2.
- **Issue:** The plan instructs copying `data/ads_sp_campaigns_live_2026-06-20.json` (the live
  91-campaign capture) into `campaigns_find.json` and the cache seed. That file does not exist
  in this worktree (`ls` and a repo-wide `find` both return nothing); it was never committed.
- **Fix:** Constructed `campaigns_find.json` and the cache seed as a sanitized, representative
  3-campaign object matching the research-PINNED `ActionAdsCampaignsFindResult` shape
  (06-RESEARCH.md lines 300-305: keys `campaignId, name, adProduct, state, budgets,
  optimizations, status`, `adProduct == "SPONSORED_PRODUCTS"`), using non-UUID placeholder IDs.
  Because the shape — not the specific campaign rows — is what the Wave 0 RED tests assert
  against (`test_find_write_and_lookup` reads `campaigns[0].campaignId`; the find_cache write/
  lookup is row-count-agnostic), the fixture is contract-valid. This mirrors the plan's own
  stated provenance posture (dryRun fixtures are spec-derived pending the Plan 04 live eyeball).
- **Files:** engine/tests/fixtures/campaigns_find.json, data/ads_campaigns_find_2026-06-20.json
- **Commit:** 144e6e9
- **Follow-up:** if/when the real 91-campaign capture is restored, re-seed both files from it
  (sanitizing `sellerOrVendorId`) before the Phase 6 gate; the cache-lookup logic is unaffected.

## Deferred Issues

### Pre-existing: `test_env.py::test_seller_id_in_env_not_code` fails in this worktree (OUT OF SCOPE)
- The test asserts `AMAZON_CA_SELLER_ID` is present in the environment (loaded from the
  gitignored `.env` by `conftest.py`). This worktree has no `.env`, so the env-var assertion
  fails — IDENTICALLY before and after this plan's changes. It is an environment gap, not a
  code regression.
- The portion of `test_env.py` this plan OWNS — the UUID source scan, now extended to `.json`
  — was verified to run clean across all tracked dirs (`src`/`db`/`tests`) via a direct
  execution of the scan loop. In the orchestrator's real environment (with `.env` present)
  this test goes green.
- **Not fixed** (no `.env` provisioning is in this plan's scope); flagged for the orchestrator.

## Known Stubs
None. The two not-yet-implemented modules (`habibos.lifecycle`, `habibos.find_cache`) are the
intended Wave 0 RED gap, implemented by Plans 02/03 — they are tracked by the failing tests,
not silent stubs.

## Verification
- `cd engine && uv run python -c "from habibos import datadoe; assert datadoe.ACTION_TERMINAL == {…verified set…}"` → exits 0.
- `grep -q '"\.json"' engine/tests/test_env.py` → present; UUID scan loop runs clean across tracked dirs.
- `grep -rl 5692b95f engine/tests/fixtures/ data/ads_campaigns_find_2026-06-20.json` → nothing (no UUID leak).
- `cd engine && uv run pytest tests/test_lifecycle.py tests/test_find_cache.py` → RED on `cannot import name 'lifecycle'/'find_cache'` (expected — Plans 02/03 implement).
- `cd engine && uv run pytest --ignore=tests/test_lifecycle.py --ignore=tests/test_find_cache.py` → 15 passed, 5 skipped, 1 failed (the pre-existing `.env`-absent env-var assertion only).

## Self-Check: PASSED
- engine/src/habibos/datadoe.py — FOUND (ACTION_TERMINAL defined)
- engine/src/habibos/result.py — FOUND (Proceed + PollOutcome)
- engine/tests/test_env.py — FOUND (.json in SCAN_SUFFIXES)
- engine/tests/test_lifecycle.py — FOUND (8 test_ defs)
- engine/tests/test_find_cache.py — FOUND (2 test_ defs)
- engine/tests/fixtures/{campaigns_find,dryrun_validated,dryrun_invalid,actions_get_completed,actions_get_error}.json — FOUND
- data/ads_campaigns_find_2026-06-20.json — FOUND
- Commits 5eb454a, d283c36, 144e6e9, d553bd0 — FOUND in git log
