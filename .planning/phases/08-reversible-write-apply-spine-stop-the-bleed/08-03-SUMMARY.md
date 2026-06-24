---
phase: 08-reversible-write-apply-spine-stop-the-bleed
plan: 03
subsystem: engine
tags: [apply-spine, reversible-write, idempotency, canary, find-before-write, poll-loop, decisions-log, anti-fabrication, ppc-write-path]

# Dependency graph
requires:
  - phase: 08-02
    provides: ledger.py (action_hash/lookup/append; LedgerHit/InFlight), denylist.py (own-ASIN refuse-gate), magnitude.py (seeded-permissive cap), find_cache A2 staleness window, owned_asins.toml
  - phase: 08-01
    provides: RED contract test_apply.py + support fixtures (actions_get_{completed,inflight,error}.json, campaigns_find_echo.json, actions_start_dryrun_pause.json) + 08-SCHEMA-PIN payload field map
  - phase: 07
    provides: gate.evaluate (spend-down auto-pass, strict-breach-never-clamp), result.py typed grammar (ProposedAction/AppliedResult/Refusal/GateRefusal/Proceed/PollOutcome)
  - phase: 06
    provides: lifecycle.classify_dryrun/classify_poll, datadoe.poll_action_status tenacity loop, find_cache.write/lookup, logging.logged_call append-only seam
provides:
  - "habibos.apply — the reversible-write apply spine (apply, build_payload, log_decision)"
  - "engine/scripts/apply_action.py — thin argv->apply->JSON CLI with --confirm-canary one-time gate"
  - "build_payload per 08-SCHEMA-PIN (pause omits adProduct, bid_down flat number, negative ad-group attach)"
  - "log_decision seam — every applied write (incl. auto) appends a decisions.md line + brain/raw note carrying the actionId"
  - "the phase-8 one-time canary marker (data/phase8_canary_confirmed)"
affects: [08-04, apply-spine, ppc-write-path, reversible-actions, live-write-wiring]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Linear typed orchestration twin of gate.evaluate — short-circuit on the FIRST refusal at every gate, never clamp/default"
    - "Python-opens-no-socket seam: every MCP result is an agent-supplied zero-arg callable (start_dryrun/start_apply/get_status/find_echo)"
    - "dryRun STOP (incl. schema-drift) refuses BEFORE any dryRun:false fires — the real write never runs on an unvalidated dryRun"
    - "poll loop drives poll_action_status + classify_poll to terminal; 20-attempt exhaustion -> unresolved_in_flight carrying the actionId (resumable)"
    - "FIND-echo confirm compares the action-type's mutated field against build_payload's intended value (08-SCHEMA-PIN); any mismatch -> find_echo_mismatch, never recorded applied"
    - "one-time canary gate (D-08/D-09): marker written only after success; subsequent moves auto-apply"
    - "autonomy != silence — standing-approved auto writes log a decisions.md line + brain note too"

key-files:
  created:
    - engine/src/habibos/apply.py
    - engine/scripts/apply_action.py
  modified: []

key-decisions:
  - "The spine re-points find_cache.DATA_DIR and ledger.DATA_DIR at apply.DATA_DIR at call time, so all idempotency + FIND-cache + canary writes share ONE data root (tests monkeypatch only apply.DATA_DIR; production resolves all three to <repo>/data anyway)"
  - "FIND-before-write seeds the cache from the agent's find_echo() result then write-bearing-lookups the entity_id; the SAME find_echo callable is re-read post-poll for the mutated-field echo confirm (pre-write verifies id-presence, post-write verifies the mutation)"
  - "A schema-drift / unvalidatable dryRun (classify_dryrun raises) is caught and surfaced as a typed Refusal(dryrun_invalid) — never an exception that escapes past the guard and never a dryRun:false fire (T-08-10)"
  - "The ledger record writes the REAL computed action_hash into the `hash` field (carry-forward from 08-02); lookup still treats recomputed identity as authoritative, never the stored field"
  - "unresolved_in_flight carries the actionId in the Refusal.export_id slot so the poll is resumable; never assumes success on exhaustion"

# Metrics
metrics:
  duration: ~25min
  completed: 2026-06-24
  tasks: 2
  files: 2
  commits: 2
---

# Phase 8 Plan 03: Reversible-Write Apply Spine Summary

The hand-written, typed apply SPINE — the linear orchestration twin of `gate.evaluate` — now threads a `ProposedAction` end-to-end through every Phase 6/7/8 gate to a logged, idempotent reversible write, plus the thin CLI with the one-time canary confirm; `test_apply.py` is fully GREEN (7/7) and the full engine suite holds (only the pre-existing env-gated `test_env` seller-UUID check fails, because `.env` is gitignored and absent in the worktree).

## What was built

**Task 1 — `engine/src/habibos/apply.py` (the spine).**
- `build_payload(action)` builds the `actions_start` `details` per action type against 08-SCHEMA-PIN: pause sends ONLY `{campaignId, state}` and omits `adProduct`; bid_down sends ONLY `{targetId, bid:<flat number>}`; negative attaches a negative exact-match keyword at AD_GROUP level (`negative:true`, `matchType` nested under `keywordTarget`, `state` required on ADD).
- `apply(action, *, owned_source, start_dryrun, start_apply, get_status, find_echo, confirm_canary=False, catalog_path=None, gate_frame=None, ad_product="SPONSORED_PRODUCTS")` threads the branch order, short-circuiting on the FIRST refusal: denylist → margin gate (spend-down auto-pass) → magnitude cap → ledger lookup (LedgerHit no-op / InFlight resume) → canary one-time gate → FIND-before-write → dryRun classify → `start_apply` (the ONE real write, wrapped in `logged_call`, 412 → `action_type_disabled` no-retry) → poll-to-terminal → FIND-echo confirm → `ledger.append` (with the real computed hash) + `log_decision` → `AppliedResult`.
- The poll loop reuses `datadoe.poll_action_status` (tenacity 20-attempt) by handing it a status-extracting wrapper that captures each FULL response, then `classify_poll`s the captured terminal one; a `RetryError` (exhaustion) → `Refusal(unresolved_in_flight)` carrying the actionId.
- `log_decision(action, action_id, result)` appends one dated pipe-delimited line to `state/decisions.md` AND writes one `brain/raw/` note, both carrying the actionId; no seller UUID. (Built here in Task 1 because the two log/canary contract tests live in the same `test_apply.py` and exercise the spine directly.)

**Task 2 — `engine/scripts/apply_action.py` (the CLI).**
- Mirrors `gate_action.py`: argparse the `ProposedAction` fields + `--params` JSON + the four agent-handed MCP fixture paths (`--dryrun-resp / --apply-resp / --status-resp / --find-echo`) + `--confirm-canary`.
- Wraps `apply.apply(...)` in `logging.logged_call("apply_action", marketplace=...)`; `end_fields["status"]` is derived from `isinstance(result, (Refusal, GateRefusal))` so a refusal can never serialize as "applied"; `json.dump(dataclasses.asdict(result))`.
- Python opens no socket — the dryRun/apply/poll/echo responses are read from local files the agent already downloaded.

## How to verify

```bash
cd engine && uv run pytest tests/test_apply.py -q          # 7 passed
cd engine && uv run pytest -q                              # 51 passed, 5 skipped, 1 env-gated fail (test_env)
grep -E "confirm[-_]canary" engine/scripts/apply_action.py # FOUND
```

CLI smoke (against committed fixtures, paths redirected to a scratch dir): a first apply with the marker absent and `--confirm-canary` omitted returns `code == "canary_unconfirmed"`; the same apply WITH `--confirm-canary` returns an `AppliedResult` and writes `data/phase8_canary_confirmed`; a subsequent apply auto-applies WITHOUT the flag; `decisions.md` + a `brain/raw` note both carry the actionId and contain no UUID.

## Deviations from Plan

### Plan-contract drift (no code change required)

**1. [Rule note - acceptance criteria reference non-existent test names]**
- **Found during:** Task 1 verification.
- **Issue:** Task 1's acceptance criteria name `tests/test_apply.py::test_magnitude_cap_refuses_when_set` and `tests/test_apply.py::test_magnitude_cap_seeded_permissive`, but the committed Wave-0 RED contract `test_apply.py` contains exactly 7 tests and NONE by those names. The magnitude-cap behavior is exercised by `magnitude.check` (called in the spine's branch 3) and pinned by Plan 02's dedicated `test_magnitude.py`, not by `test_apply.py`.
- **Resolution:** The binding artifact is the committed RED contract (`test_apply.py`), which is fully GREEN (7/7). The spine threads `magnitude.check` in branch order per the plan body; the named-but-absent tests are a plan-authoring slip, not a missing implementation. No code change.

### Auto-added for correctness (Rule 2 / Rule 3)

**2. [Rule 3 - Blocking] dryRun schema-drift caught as a typed refusal**
- **Found during:** Task 1 (`test_dryrun_refusal_blocks_apply`).
- **Issue:** The test's `bad_dryrun` fixture omits the `type` field, so `classify_dryrun` raises `ValueError` on schema drift rather than returning a `Refusal`; the bare exception would escape the spine and `start_apply` would be left ambiguous.
- **Fix:** The dryRun step wraps `classify_dryrun` in a `try/except ValueError` → `Refusal(dryrun_invalid)`. This preserves the T-08-10 guarantee (an unvalidatable/drifted dryRun STOPs BEFORE any `dryRun:false` fires — the real write never runs) and matches the anti-fabrication grammar (drift is a refusal, never a swallow).
- **Files:** engine/src/habibos/apply.py — Commit a5df0e8.

**3. [Rule 3 - Blocking] Shared data root for the reused find_cache/ledger seams**
- **Found during:** Task 1 (the `spine_dirs` fixture monkeypatches only `apply.DATA_DIR`).
- **Issue:** `find_cache.DATA_DIR` and `ledger.DATA_DIR` are independent module variables; the test patches neither, so without intervention the spine would read/write the real `<repo>/data` for the FIND cache, ledger, and canary marker during tests.
- **Fix:** `apply._point_seams_at_data_dir()` re-points `find_cache.DATA_DIR` and `ledger.DATA_DIR` at `apply.DATA_DIR` at call time. Tests stay hermetic (all writes land in tmp_path); in production all three resolve to `<repo>/data` anyway, so it is a no-op there.
- **Files:** engine/src/habibos/apply.py — Commit a5df0e8.

## Threat surface

No new security surface beyond the plan's `<threat_model>`. The spine opens no socket (the one real account mutation is the agent-supplied `start_apply` callable, gated behind denylist/gate/cap/ledger/canary/dryRun); `logged_call`, the decisions line, and the brain note carry only op/marketplace/entity/actionId — never the seller UUID (T-08-15 / hard rule 5, verified by the CLI smoke's no-UUID assertion). The mitigations for T-08-10 (dryRun-stop-before-write), T-08-11 (canary), T-08-12 (412 no-retry), T-08-13 (reconcile via poll-terminal + FIND-echo only), and T-08-14 (auto writes still log) are all implemented as described.

## Known stubs

None. The spine is fully wired against committed fixtures; the only "deferred" surface is the live MCP wiring (Plan 08-04), which is intentionally out of scope per the plan and the parallel-execution constraint (no live Amazon/DataDoe writes in this plan).

## Self-Check: PASSED

- FOUND: engine/src/habibos/apply.py
- FOUND: engine/scripts/apply_action.py
- FOUND: .planning/phases/08-reversible-write-apply-spine-stop-the-bleed/08-03-SUMMARY.md
- FOUND commit a5df0e8 (Task 1 — apply spine)
- FOUND commit 3685fb3 (Task 2 — apply_action.py CLI)
- tests/test_apply.py: 7 passed; full engine suite: 51 passed, 5 env-gated skips, 1 pre-existing env-gated fail (test_env, .env absent in worktree)
