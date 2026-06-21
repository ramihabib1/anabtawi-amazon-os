---
phase: 06-find-lifecycle-substrate
plan: 02
subsystem: engine (actions lifecycle classifiers + thin write-path CLIs)
tags: [write-path, actions-lifecycle, dryrun-gate, poll-classify, wave-2, tdd-green, secret-hygiene]
requires:
  - engine/src/habibos/datadoe.py (ACTION_* sets + poll_action_status — Plan 01)
  - engine/src/habibos/result.py (Refusal / Proceed / PollOutcome — Plan 01)
  - engine/src/habibos/logging.py (logged_call one-in-one-out)
  - engine/tests/test_lifecycle.py (the 8-case RED contract — Plan 01)
provides:
  - habibos.lifecycle.classify_dryrun (WRITE-01 dryRun PROCEED/STOP gate)
  - habibos.lifecycle.classify_poll (WRITE-05 single-response actions_get classifier)
  - habibos.lifecycle.classify_poll_logged (logged_call-wrapped, no-secret seam)
  - engine/scripts/classify_dryrun.py + classify_poll.py (thin CLIs mirroring answer_tacos.py)
affects:
  - Phase 8 apply spine (drives datadoe.poll_action_status end-to-end; consumes these classifiers)
tech-stack:
  added: []
  patterns: [typed-result-anti-fabrication, pydantic-validate-or-raise, logged_call-one-in-one-out, thin-cli-over-core, repo-root-relative-paths]
key-files:
  created:
    - engine/src/habibos/lifecycle.py
    - engine/scripts/classify_dryrun.py
    - engine/scripts/classify_poll.py
  modified: []
decisions:
  - "PROCEED requires all three positive conditions (status==VALIDATED && validation.valid && issues==[]); any other state refuses (no silent default)"
  - "An unmodeled actions_get status -> Refusal(unknown_status), never assumed-terminal nor infinite-polled; the export terminal FAILED falls here (export status is not an action confirmation)"
  - "classify_poll classifies ONE response; the in-flight->terminal poll LOOP is deferred-by-design to Phase 8's apply spine"
  - "Partial terminals (PARTIALLY_COMPLETED/COMPLETED_WITH_ISSUES) -> done_with_issues, surfacing error.message verbatim when present"
metrics:
  tasks-completed: 2
  files-created: 3
  files-modified: 0
  completed: 2026-06-21
requirements: [WRITE-01, WRITE-05]
---

# Phase 6 Plan 02: Lifecycle Classifiers + Thin Write-Path CLIs Summary

Implemented the hand-written `habibos.lifecycle` classifiers that turn an
`actions_start dryRun:true` response (WRITE-01) and a single `actions_get` response (WRITE-05)
into typed PROCEED / STOP / poll-state / refuse verdicts, plus the two thin CLIs
(`classify_dryrun.py` / `classify_poll.py`) that wrap each op in `logged_call` mirroring
`answer_tacos.py`. This turns the Wave 0 RED contract (`test_lifecycle.py`, 8 cases) fully
GREEN. No `dryRun:false` ever fires; the classifiers operate on agent-handed JSON and open no
socket. The in-flight→terminal poll LOOP is intentionally NOT driven here — that is Phase 8's
apply spine; Phase 6 ships single-response classification + the capped poll primitive (Plan 01).

## What Was Built

### Task 1 — `habibos.lifecycle`: classify_dryrun + classify_poll (+ classify_poll_logged) (813a190)
- `lifecycle.py` (159 lines), package-relative imports, `from __future__ import annotations`,
  pydantic `BaseModel/ConfigDict/ValidationError`. No HTTP/socket import (the seam holds —
  the DataDoe `actions_*` calls are the agent's MCP tool calls, never Python's).
- **dryRun shape, NESTED** (RESEARCH Pitfall 2): `_ActionValidationIssue(path, code, message)`,
  `_ActionValidationResult(valid: bool, issues: list[...])`, `_ActionStartResponse(type, status,
  validation)` — `extra="ignore"`. `classify_dryrun(resp) -> Proceed | Refusal`: PROCEED
  (typed `Proceed(action_type=<type>)`, never a bare True) iff `status=="VALIDATED" and
  validation.valid is True and validation.issues==[]`; otherwise `Refusal(<issue messages joined
  verbatim>, "dryrun_invalid")`. Validate-or-raise on drift (`ValueError("... schema mismatch
  (drift?): ...")`) exactly like `tacos.parse` — an untrusted shape can never read as PROCEED.
- **actions_get shape**: `_ActionExecutionError(status, code, message)`, `_ActionStatusResponse(
  status, error: Optional[...])`. `classify_poll(resp) -> PollOutcome | Refusal` buckets the
  verbatim wire `status` against the PINNED `datadoe.ACTION_*` sets:
  `ACTION_TERMINAL_SUCCESS -> PollOutcome("done")`; `ACTION_TERMINAL_PARTIAL ->
  PollOutcome("done_with_issues", [error.message])`; `ACTION_IN_FLIGHT -> PollOutcome("in_flight")`;
  `ACTION_TERMINAL_FAIL -> Refusal(<error.message verbatim>, "action_error")`; a status in NONE
  of the sets -> `Refusal(f"unknown action status: {status}", "unknown_status")` (NEVER assumed
  terminal, NEVER infinite-polled). Classifies ONE response — it does NOT drive
  `datadoe.poll_action_status` (Phase 8's apply spine).
- **Reconcile guard** (RESEARCH 207-208): the export terminal `"FAILED"` is NOT in the action
  enum, so it falls through to `unknown_status` — an export status is never an action
  confirmation. (`test_export_not_confirmation` GREEN.)
- `classify_poll_logged(resp)`: wraps `classify_poll` in `logging.logged_call("actions_get")`,
  setting `end_fields["status"]` to the poll state or `"refused"`; never passes the seller UUID.

### Task 2 — thin CLIs `classify_dryrun.py` / `classify_poll.py` (<TASK2_HASH>)
- Both mirror `answer_tacos.py` exactly: module docstring framing the seam,
  `from habibos import lifecycle` + `logging as habibos_logging`, typed-result imports,
  `REPO_ROOT = Path(__file__).resolve().parent.parent`, argparse `--artifact <response JSON>`.
  Each: load the JSON, wrap `lifecycle.classify_*` in `habibos_logging.logged_call(
  "actions_start" / "actions_get")`, fill `end_fields["status"]` (`validated`/`refused` for
  dryRun; the poll `state`/`refused` for poll), `dataclasses.asdict` the typed result,
  `json.dump(..., sys.stdout)`.
- THIN — no classification logic in the CLIs (all of it is in `lifecycle.py`). NEVER passes the
  seller UUID into `logged_call` start/end fields and never prints it.
- Smoke: `classify_dryrun.py --artifact dryrun_validated.json` ->
  `{"action_type": "AMAZON_ADS_CAMPAIGNS_UPDATE"}` (exit 0); `classify_poll.py --artifact
  actions_get_completed.json` -> `{"status": "COMPLETED", "state": "done", "issues": []}`
  (exit 0). No `5692b95f` on stdout or in the runtime log.

## Deviations from Plan

None — plan executed exactly as written. The `classify_poll_logged` helper (which
`test_ops_logged_no_secret` calls) lives in `lifecycle.py` as the plan's interface block and the
test contract both imply; the CLIs remain thin wrappers over it / `classify_poll`.

## Deferred Issues

### Pre-existing: `test_env.py::test_seller_id_in_env_not_code` fails (no `.env` in worktree) — OUT OF SCOPE
- The test asserts `AMAZON_CA_SELLER_ID` is present in the environment (loaded from the
  gitignored `.env`). This worktree has no `.env`, so the assertion fails — IDENTICALLY before
  and after this plan's changes (already flagged in 06-01-SUMMARY). It is an environment gap, not
  a code regression; goes green in the orchestrator's real environment. Not in this plan's scope.

## Known Stubs
None. `engine/src/habibos/find_cache.py` (the other still-RED module, `test_find_cache.py`) is
the intended Wave-2 sibling owned by Plan 03 — tracked by its failing import, not a silent stub
in this plan.

## Threat Flags
None. No new network endpoint, auth path, or trust-boundary surface beyond the plan's
`<threat_model>` (T-06-03..06): the classifiers open no socket, refuse on drift, never default an
unmodeled status, and the CLIs leak no seller UUID.

## Verification
- `cd engine && uv run pytest tests/test_lifecycle.py` -> 8 passed (all nodes GREEN).
- `grep -nE "httpx|requests|urllib|socket|boto3"` over `lifecycle.py` + both CLIs (import lines)
  -> nothing (the seam holds).
- `grep -n "def classify_dryrun\|def classify_poll" lifecycle.py` -> both present;
  `grep -n "datadoe.ACTION_"` -> buckets against the pinned sets;
  `grep -n "unknown_status\|dryrun_invalid\|action_error"` -> all three refusal codes present.
- Smoke runs (above) exit 0 with the expected verdicts; no `5692b95f` on stdout or in `logs/`.
- `cd engine && uv run pytest --ignore=tests/test_find_cache.py` -> 23 passed, 5 skipped,
  1 failed (only the pre-existing `.env`-absent env-var assertion). `test_find_cache.py` is the
  intended Plan 03 RED (ImportError on `find_cache`), untouched.

## Self-Check: PASSED
- engine/src/habibos/lifecycle.py — FOUND (classify_dryrun + classify_poll + classify_poll_logged)
- engine/scripts/classify_dryrun.py — FOUND (thin logged_call wrapper)
- engine/scripts/classify_poll.py — FOUND (thin logged_call wrapper)
- Commit 813a190 (Task 1) — FOUND in git log
- All 8 test_lifecycle.py nodes — GREEN
