---
phase: 08-reversible-write-apply-spine-stop-the-bleed
plan: 02
subsystem: engine
tags: [idempotency, sha256, denylist, magnitude-cap, find-cache, tomllib, ppc-write-spine, anti-fabrication]

# Dependency graph
requires:
  - phase: 08-01
    provides: RED contract tests (test_ledger, test_denylist, test_magnitude_cap, extended test_find_cache) + sanitized fixtures (actions_ledger_seed.jsonl, owned_asins_test.toml, sku_catalog_test.toml) + 08-SCHEMA-PIN normalized-params map
  - phase: 07
    provides: gate.py tomllib-catalog read + strict-breach-never-clamp pattern; thresholds.read None-dial; result.py typed grammar (GateRefusal/Refusal/ProposedAction)
  - phase: 06
    provides: find_cache.py newest-wins DATA_DIR scan; logging.py append-only jsonl seam
provides:
  - "habibos.ledger — content-hash idempotency over data/actions_ledger.jsonl (action_hash/lookup/append; LedgerHit/InFlight)"
  - "habibos.denylist — own-ASIN pre-dryRun hard refuse-gate (load_owned/extract_target_asins/check)"
  - "habibos.magnitude — seeded-permissive bounded-% reversible cap (check; over_cap, never clamps)"
  - "engine/config/owned_asins.toml — dedicated authoritative owned-ASIN denylist source (26 ASINs incl. B07TV972JT)"
  - "engine/config/thresholds.toml max_reversible_pct_change dial (seeded empty = permissive)"
  - "find_cache A2 staleness window (STALE_HOURS dial; write_bearing lookup -> stale_find_cache)"
affects: [08-03, apply-spine, ppc-write-path, reversible-actions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Content-hash identity excludes date (re-run = no-op) with documented param normalization"
    - "Dedicated config source decoupled from the COGS catalog (owned set != funded set)"
    - "Seeded-permissive cap — None means PASS (asymmetric to the margin floor where None REFUSES)"
    - "Write-bearing staleness window as a named, commented dial — not a bare literal"

key-files:
  created:
    - engine/src/habibos/ledger.py
    - engine/src/habibos/denylist.py
    - engine/src/habibos/magnitude.py
    - engine/config/owned_asins.toml
  modified:
    - engine/config/thresholds.toml
    - engine/src/habibos/find_cache.py

key-decisions:
  - "action_hash is sha256 over {entity_type+entity_id+action_type+normalized_params}, NEVER date — re-pausing on a later day yields the same hash (D-10)"
  - "lookup recomputes each record's identity hash from its fields; the stored `hash` field is informational provenance, never trusted as identity"
  - "owned set read from the DEDICATED owned_asins.toml (26 ASINs incl. B07TV972JT), decoupled from sku_catalog.toml's 16 COGS rows (D-06/D-06a)"
  - "magnitude cap seeded permissive: None cap -> pass at any magnitude (D-01/D-02), the documented asymmetry vs the margin floor; over_cap refuses, never clamps"
  - "A2 staleness window = STALE_HOURS=24 named dial; only write_bearing=True lookups enforce it (non-write reads keep newest-wins)"

patterns-established:
  - "Date-free content-hash idempotency with explicit param normalization for write de-dup"
  - "Decoupled denylist source: owned ASINs (broad) separate from funded COGS catalog (narrow)"
  - "Asymmetric None-dial: permissive-on-absent for a reversible cap vs refuse-on-absent for a money floor"

requirements-completed: [WRITE-07, EXEC-01]

# Metrics
duration: 18min
completed: 2026-06-22
---

# Phase 8 Plan 02: Pre-dryRun Engine Pieces (Ledger + Denylist + Magnitude Cap) Summary

**Three hand-written, pytest-covered gates that fire BEFORE a real Amazon ad write: a date-free sha256 idempotency ledger (no-op on re-run, resume on in-flight), an own-ASIN hard refuse-gate from a dedicated 26-ASIN source, and a seeded-permissive bounded-% magnitude cap — plus the A2 find-cache staleness window.**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-06-22T20:15Z (approx)
- **Completed:** 2026-06-22T20:34Z
- **Tasks:** 3
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments
- **Idempotency ledger (WRITE-07/D-10):** `action_hash` is sha256 over entity+action+normalized_params and INVARIANT to date, so a re-proposed write hashes identically and the spine never fires a second `actions_start`. `lookup` recomputes each record's identity and classifies COMPLETED → `LedgerHit` (no-op) vs in-flight → `InFlight` (resume at poll). `append` is append-only jsonl, no socket, no seller UUID.
- **Own-ASIN denylist (EXEC-01/D-06/D-07):** seeded the dedicated `owned_asins.toml` (26 owned ASINs incl. the named private-label exclusion B07TV972JT), decoupled from the COGS catalog. `check` hard-refuses a write that targets an owned ASIN pre-dryRun (`own_asin_denied`); pauses/bid-downs carry no target ASIN and pass cleanly. Missing owned file RAISES (no silent fallback).
- **Magnitude cap (SC-5/D-02):** built + tested but seeded PERMISSIVE — a None cap passes at any magnitude (the deliberate asymmetry vs the margin floor). An over-cap move refuses (`over_cap`) and NEVER clamps. Added the `max_reversible_pct_change` thresholds dial seeded empty with a documented "permissive" comment.
- **A2 staleness window:** added `STALE_HOURS = 24` as a named, commented dial and a `write_bearing` param to `find_cache.lookup` — a write-bearing lookup against an over-window cache file refuses (`stale_find_cache`); non-write reads keep the Phase-6 newest-wins behavior unchanged.

## Task Commits

Each task was committed atomically (TDD GREEN against Plan 01's RED contracts):

1. **Task 1: ledger.py — content-hash idempotency** - `92f9bef` (feat)
2. **Task 2: denylist.py + owned_asins.toml — own-ASIN refuse-gate** - `196d6f9` (feat)
3. **Task 3: magnitude.py + thresholds dial + find_cache staleness window** - `9b3ed88` (feat)

_Note: the RED contract tests were authored in Plan 01; this plan provides the GREEN implementation, so each task is a single `feat` GREEN commit._

## Files Created/Modified
- `engine/src/habibos/ledger.py` (created) - content-hash idempotency ledger; `action_hash`/`lookup`/`append` + `LedgerHit`/`InFlight`
- `engine/src/habibos/denylist.py` (created) - own-ASIN refuse-gate; `load_owned`/`extract_target_asins`/`check`
- `engine/src/habibos/magnitude.py` (created) - seeded-permissive bounded-% cap; `check`
- `engine/config/owned_asins.toml` (created) - dedicated authoritative owned-ASIN denylist source (26 ASINs incl. B07TV972JT)
- `engine/config/thresholds.toml` (modified) - added `max_reversible_pct_change = ""` dial (permissive by default) under `[marketplace.CA]`
- `engine/src/habibos/find_cache.py` (modified) - added `STALE_HOURS` dial + `write_bearing` param + `_file_date` helper for the A2 staleness window

## Decisions Made
- **Hash identity excludes date and is recomputed at lookup.** The seed fixture's `hash` field is a placeholder; `lookup` therefore recomputes each record's identity from its own entity/action/normalized_params rather than trusting the stored hash. This is the only correct design given the contract (the test computes `action_hash(...)` then looks it up) and is strictly safer — provenance, not identity, lives in the stored field.
- **Param normalization is documented as load-bearing:** literal/enum fields (`state`, `matchType`) canonicalize UPPER to the wire literal; other strings lowercase+strip; bids round to 2 dp (CAD cents); dict keys sort. Two equivalent payloads collide on one hash.
- **Owned set seeded from the authoritative SKU→ASIN table (25 ASINs) + B07TV972JT = 26.** The 5 inactive-remnant SKUs carry no ASIN in the authoritative table and so contribute no row (never invented). Gap documented in the file header per D-06a.
- **Cap dial is asymmetric to the margin floor:** None/empty → permissive (pass), the opposite of the margin gate where None refuses. Documented in both `magnitude.py` and the thresholds.toml comment.

## Deviations from Plan

None - plan executed exactly as written. The three modules, the dedicated config, the thresholds dial, and the staleness window were all built per the task specs; all targeted RED contracts are GREEN.

## Issues Encountered
- **`test_env.py::test_seller_id_in_env_not_code` fails in the isolated worktree** (1 failure in the full suite). This is a PRE-EXISTING, out-of-scope environment-config gap unrelated to this plan's changes: `test_env.py` imports no `habibos` code and asserts the gitignored `.env` carries `AMAZON_CA_SELLER_ID`, which is absent in a fresh worktree (gitignored, never copied). NOT auto-fixed — materializing the seller UUID into the worktree would violate CLAUDE.md hard rule 5. Logged to `08-.../deferred-items.md`. It passes in the primary checkout where `.env` exists. The rest of the suite is green.

## Test Results
- **Targeted contracts (this plan):** `test_ledger.py` (3/3), `test_denylist.py` (3/3), `test_magnitude_cap.py` (2/2), `test_find_cache.py` (3/3) — **11/11 GREEN**.
- **Full engine suite (excluding Plan 03's `test_apply.py`, which stays RED until Wave 2):** 44 passed, 5 skipped, 1 failed (the out-of-scope `test_env` worktree env-gap above). No regression to Phase 6/7 logic.
- **Cap dial verified:** `thresholds.read("max_reversible_pct_change")` → `None` (permissive seed confirmed).

## Threat Model Coverage
- **T-08-04 / T-08-06 (double-apply / weak idempotency):** mitigated — `test_completed_hash_is_noop` + `test_hash_excludes_date` enforce date-free sha256 identity.
- **T-08-05 (own-ASIN self-cannibalization):** mitigated — `denylist.check` hard-refuses from the dedicated `owned_asins.toml` incl. B07TV972JT.
- **T-08-07 (stale-entity write):** mitigated — `write_bearing` staleness window → `stale_find_cache`.
- **T-08-08 (magnitude killing a winner):** ACCEPTED per D-01/D-02 — cap built + tested, seeded permissive; tightening is a thresholds dial, no code change.
- **T-08-09 (seller-UUID disclosure):** mitigated — ledger records and `owned_asins.toml` carry only public entity/ASIN data, never the seller UUID.

## Next Phase Readiness
- **Plan 08-03 (apply spine) is unblocked:** `ledger.lookup`/`append`, `denylist.check`, `magnitude.check`, and `find_cache.lookup(..., write_bearing=True)` are the pre-dryRun gates the apply orchestrator wires in sequence. `test_apply.py` (Plan 03) stays RED on the missing `habibos.apply` module — that is the intended Wave-2 state.
- **No live writes performed.** This plan built local Python + config and ran pytest only.

---
*Phase: 08-reversible-write-apply-spine-stop-the-bleed*
*Completed: 2026-06-22*
