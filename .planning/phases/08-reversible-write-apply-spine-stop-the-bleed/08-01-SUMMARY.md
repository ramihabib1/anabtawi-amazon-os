---
phase: 08-reversible-write-apply-spine-stop-the-bleed
plan: 01
subsystem: engine (apply-spine Wave-0 contracts)
status: COMPLETE — all 3 tasks done (Task 1 live-pinned by orchestrator MCP recon)
tags: [write-spine, tdd-red, fixtures, idempotency, denylist, magnitude-cap, schema-pin]
requires:
  - engine/src/habibos/result.py (ProposedAction, GateVerdict — extended in place)
  - engine/tests/fixtures/{dryrun_validated,actions_get_completed,campaigns_find}.json (style refs)
provides:
  - engine/src/habibos/result.py: ProposedAction.{entity_type,entity_id,params} + AppliedResult
  - engine/tests/fixtures/{actions_get_inflight,campaigns_find_echo}.json, actions_ledger_seed.jsonl, owned_asins_test.toml
  - engine/tests/{test_apply,test_ledger,test_denylist,test_magnitude_cap}.py (RED Wave-0 contracts)
  - engine/tests/test_find_cache.py::test_stale_cache_refused (A2 RED extension)
affects:
  - Plan 02 (ledger.py, denylist.py, magnitude.py) — GREEN target of test_ledger/test_denylist/test_magnitude_cap
  - Plan 03 (apply.py) — GREEN target of test_apply; consumes AppliedResult + ProposedAction fields
tech-stack:
  added: []   # no new packages (RESEARCH Package Legitimacy Audit: N/A)
  patterns: [RED-on-import Wave-0 baseline, fixture-anchored assertions, typed-refusal grammar]
key-files:
  created:
    - engine/tests/fixtures/actions_start_dryrun_pause.json
    - engine/tests/fixtures/actions_start_dryrun_negative.json
    - engine/tests/fixtures/actions_start_dryrun_biddown.json
    - .planning/phases/08-reversible-write-apply-spine-stop-the-bleed/08-SCHEMA-PIN.md
    - engine/tests/fixtures/actions_get_inflight.json
    - engine/tests/fixtures/campaigns_find_echo.json
    - engine/tests/fixtures/actions_ledger_seed.jsonl
    - engine/tests/fixtures/owned_asins_test.toml
    - engine/tests/test_apply.py
    - engine/tests/test_ledger.py
    - engine/tests/test_denylist.py
    - engine/tests/test_magnitude_cap.py
  modified:
    - engine/src/habibos/result.py
    - engine/tests/test_find_cache.py
decisions:
  - "AppliedResult reuses GateRefusal/Refusal for the 7 new Phase-8 codes (no new refusal dataclass)."
  - "owned_asins_test.toml mirrors the DEDICATED owned_asins.toml source (D-06a), decoupled from the COGS catalog."
metrics:
  duration: ~partial session
  completed: 2026-06-22
---

# Phase 8 Plan 01: Pin Reversible-Write Schemas + Lay RED Contracts — Summary (COMPLETE)

ProposedAction extended with the apply-spine fields, AppliedResult added, four supporting
fixtures captured, and the four RED Wave-0 test contracts (+ the A2 staleness extension) laid
down. **Task 1 — the live schema pin — is COMPLETE.** The original executor lacked the DataDoe
MCP tools; the orchestrator (which has them) ran the read-safe recon — three
`actions_details_schema_get` reads + one read-only `TARGETS_FIND` + three `actions_start
dryRun:true` validations (no live writes, no account changes) — and captured the three real
VALIDATED payloads as sanitized fixtures plus `08-SCHEMA-PIN.md`. Nothing was fabricated.

## What Was Completed

### Task 2 — result.py extension + supporting fixtures (commit `09cf048`) ✅
- `ProposedAction` gained three OPTIONAL fields with defaults — `entity_type: str | None`,
  `entity_id: str | None`, `params: dict = field(default_factory=dict)` — so the Phase-7 gate
  CLI contract (`test_gate_action.py` / `test_gate.py`) stays GREEN (the gate reads only
  sku/action_type/delta_spend). Verified: 10/10 Phase-7 contract tests pass.
- `AppliedResult` added (frozen dataclass mirroring `GateVerdict`): `action_id`, `status`
  (terminal wire status), `hash` (ledger content hash), `applied_at` (ISO), `marketplace="CA"`.
  Its docstring records the seven new Phase-8 refusal codes that reuse `Refusal`/`GateRefusal`:
  `own_asin_denied`, `over_cap`, `stale_find_cache`, `canary_unconfirmed`,
  `action_type_disabled`, `unresolved_in_flight`, `find_echo_mismatch`.
- Four sanitized fixtures captured: `actions_get_inflight.json` (status `IN_PROGRESS`),
  `campaigns_find_echo.json` (CMP-…003 `state:"PAUSED"` for the echo-confirm),
  `actions_ledger_seed.jsonl` (2 COMPLETED + 1 in-flight, Pattern-3 record schema),
  `owned_asins_test.toml` (the dedicated denylist source per D-06a, carrying B07TV972JT which
  is deliberately ABSENT from `sku_catalog_test.toml`). No seller UUID in any fixture.

### Task 3 — RED Wave-0 test contracts (commit `ab5ea2a`) ✅ (RED-as-intended)
- `test_ledger.py` (WRITE-07): `test_completed_hash_is_noop`, `test_inflight_resumes_at_poll`,
  `test_hash_excludes_date` — content-hash idempotency keyed {entity+action+params}, NOT date (D-10).
- `test_denylist.py` (EXEC-01): `test_own_asin_refused`, `test_pause_passes_denylist`,
  `test_owned_set_from_dedicated_source` — owned set from the dedicated `owned_asins` source (D-06a).
- `test_magnitude_cap.py` (SC-5/D-02): `test_magnitude_cap_refuses_when_set` (never clamps),
  `test_magnitude_cap_seeded_permissive`.
- `test_apply.py` (WRITE-03/06): `test_reversible_write_end_to_end`,
  `test_dryrun_refusal_blocks_apply`, `test_poll_loop_to_terminal`,
  `test_apply_logs_decision_and_brain`, `test_canary_one_time_confirm`,
  `test_disabled_action_refuses`, `test_find_echo_mismatch`. The agent supplies every MCP
  result as a plain dict / zero-arg callable (Python opens no socket); all payload SHAPES are
  loaded from committed fixtures — no inline fabricated DataDoe schema.
- `test_find_cache.py` extended with `test_stale_cache_refused` (A2 write-bearing staleness).

**Verified Wave-0 RED state:** the four new files fail RED on the missing
`habibos.apply`/`ledger`/`denylist`/`magnitude` modules; `test_stale_cache_refused` fails RED
on the missing `write_bearing` kwarg; the two pre-existing `test_find_cache` tests stay GREEN;
the Phase-7 gate contract (10 tests) stays GREEN. No seller UUID anywhere under `engine/tests/`.

## Task 1 — COMPLETE (live schema pin, read-safe MCP recon)

The three reversible-action payload schemas were pinned LIVE via the DataDoe MCP — read-only +
`dryRun:true` only, **no live account writes**:
- `actions_details_schema_get` for `AMAZON_ADS_CAMPAIGNS_UPDATE`, `AMAZON_ADS_TARGETS_ADD`,
  `AMAZON_ADS_TARGETS_UPDATE` (read).
- One read-only `AMAZON_ADS_TARGETS_FIND` (actionId `9c3e7cd0-…`, COMPLETED) for real
  campaign/adGroup/target IDs and the live `targetDetails.keywordTarget` shape.
- Three `actions_start dryRun:true` validations, each returning `status:"VALIDATED"`,
  `validation.valid:true`, `validation.issues:[]` (the negative-add needed `state` added on the
  second iteration — validator: "Target add action requires state").

Captured as three sanitized fixtures (`actions_start_dryrun_{pause,negative,biddown}.json`,
seller UUID stripped) + `08-SCHEMA-PIN.md` (the field-name map source of truth).

**Pinned facts (resolve RESEARCH Pitfall 1/2, Assumptions A1–A3, Open Question 1):**
- **PAUSE** = `AMAZON_ADS_CAMPAIGNS_UPDATE`, details `{campaigns:[{campaignId, state:"PAUSED"}]}`;
  **no `adProduct`** (live validator rejects it on UPDATE — confirms SKILL line 174).
- **NEGATIVE exact** = `AMAZON_ADS_TARGETS_ADD`, `negative:true` + `targetType:"KEYWORD"` +
  `targetDetails.keywordTarget.matchType:"EXACT"`. **There is NO `NEGATIVE_EXACT` literal** —
  negation is the `negative:true` flag, match-type is plain `"EXACT"` nested under
  `keywordTarget`. `state` is REQUIRED on ADD. Attachment level = **AD_GROUP** (via `adGroupId`).
- **BID-DOWN** = `AMAZON_ADS_TARGETS_UPDATE`, details `{targets:[{targetId, bid}]}`; the write
  takes a **flat** `bid` number, but a FIND echoes bid as `{bid, currencyCode}` (read `.bid.bid`).

**Downstream:** `08-SCHEMA-PIN.md` is the single source of truth `build_payload` (Plan 03) and
the ledger normalized-params map (Plan 02) are written against. The RED contracts (Task 3) now
have their fixture anchors present; they still fail RED on the missing modules (intended).

## Deviations from Plan

None. Tasks 2 and 3 executed exactly as written. Task 1 halted at its designed blocking
human-action checkpoint (live MCP unreachable), per the plan's explicit STOP instruction.

## Known Stubs

None. No production module was stubbed — Task 3 is RED-only by design (TDD RED gate); the
GREEN modules are Plans 02–03.

## Self-Check: PASSED

All three tasks complete. Task-2/Task-3 commits (`09cf048`, `ab5ea2a`) plus the Task-1 schema
pin are in the worktree branch history. Acceptance verified: the three `actions_start_dryrun_*`
fixtures parse with `status:"VALIDATED"`/`valid:true`/`issues:[]`; the pause fixture contains
no `adProduct`; no seller UUID anywhere under `engine/tests/fixtures/`; `08-SCHEMA-PIN.md`
records the per-type field map incl. the negative match-type literal + ad-group attachment;
the Phase-7 contract (10 tests) stays GREEN; the four Wave-0 test files fail RED on the missing
`habibos.apply`/`ledger`/`denylist`/`magnitude` modules (intended pre-Wave-1/2 state).
