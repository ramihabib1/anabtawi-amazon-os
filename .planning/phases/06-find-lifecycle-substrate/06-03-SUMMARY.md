---
phase: 06-find-lifecycle-substrate
plan: 03
subsystem: engine (FIND-before-write cache)
tags: [write-path, find-cache, missing-refuse, wave-2, tdd-green, anti-fabrication]
requires:
  - engine/src/habibos/result.py (Refusal — the typed miss return)
  - engine/tests/test_find_cache.py (the Wave 0 RED contract from Plan 01)
  - engine/tests/fixtures/campaigns_find.json (the FIND result shape)
provides:
  - habibos.find_cache.write (persist an agent-handed FIND result to a dated local file)
  - habibos.find_cache.lookup (newest-wins cache scan; HIT dict | find_cache_miss Refusal)
  - habibos.find_cache.DATA_DIR (repo-root-relative data/, monkeypatchable)
affects:
  - Phase 8 apply spine (a real UPDATE/REMOVE refuses at BUILD on an uncached/stale ID)
tech-stack:
  added: []
  patterns: [missing-refuse-grammar, pydantic-validate-or-raise, repo-root-relative-paths, newest-wins-staleness, no-socket-seam]
key-files:
  created:
    - engine/src/habibos/find_cache.py
  modified: []
decisions:
  - "Implemented to the TEST signatures (write/lookup take entity_type, ad_product, result/entity_id), not the plan-prose 2-arg shape — the committed test_find_cache.py is the binding contract"
  - "ad_product is part of the cache key + filename (ads_<entity>_<adproduct>_find_<date>.json) so an SP FIND can never satisfy an SB/SD lookup"
  - "Staleness window left as a Phase-8 operator dial (RESEARCH A2) — newest-dated-file-wins is the only staleness rule in Phase 6, no silent hard-coded cutoff"
metrics:
  tasks-completed: 1
  files-created: 1
  files-modified: 0
  completed: 2026-06-21
requirements: [WRITE-02]
---

# Phase 6 Plan 03: FIND-before-write Cache Summary

Implemented `habibos.find_cache` — the load-bearing anti-fabrication gate that turns the
Wave 0 RED `test_find_cache.py` GREEN. `write()` persists an agent-handed FIND result to a
dated local file after pydantic validate-or-raising each item on its id field; `lookup()`
reads the newest matching cache file and returns the cached entity dict on a HIT or a typed
`Refusal("stale/missing entity ID", "find_cache_miss")` on a MISS — so a later UPDATE/REMOVE
whose IDs are not cached is refused at BUILD, never executed on a fabricated or stale ID
(WRITE-02). No socket; the FIND JSON is handed in by the agent (the seam holds).

## What Was Built

### Task 1 — `find_cache.py`: write() + lookup() with missing→refuse (219d002)
- **`DATA_DIR = Path(__file__).resolve().parents[2] / "data"`** — repo-root-relative (mirrors
  `thresholds.CONFIG_PATH`); the test monkeypatches it to `tmp_path` so no real `data/` writes
  happen.
- **`_ENTITY_MAP`** maps each entity type to its `(FIND result list key, id field)`:
  campaigns→`campaignId`, adGroups→`adGroupId`, targets→`targetId`, ads→`adId` (the pinned
  FIND shapes, 06-RESEARCH 300-305). An unknown `entity_type` raises `ValueError` (fail loud,
  never a silent default).
- **`write(entity_type, ad_product, find_result) -> Path`**: pulls the row list from under the
  result key; a missing key raises `ValueError("FIND result schema mismatch (drift?)…")`. Each
  item is pydantic validate-or-raised by a dynamically-typed `_FindItem(BaseModel)` whose only
  REQUIRED field is the id field (`model_config = ConfigDict(extra="ignore")` tolerates the many
  utility FIND columns) — a renamed/missing id raises `ValueError` via `ValidationError` (drift
  surfaced, never silently cached, T-06-08). Writes the full result to
  `data/ads_<entity>_<adproduct>_find_<today>.json` and returns the path.
- **`lookup(entity_type, ad_product, entity_id) -> dict | Refusal`**: globs
  `ads_<entity>_<adproduct>_find_*.json`, sorts **reverse** (date is the filename tail, so
  newest-wins — Pitfall 3 / T-06-09), scans rows for a matching id field, returns that dict on a
  HIT. No file / no match → `Refusal("stale/missing entity ID", "find_cache_miss")` — never a
  default, never a fabricated ID (T-06-07, the FIND-before-write gate).
- **No socket:** zero HTTP/network imports; only `json`, `datetime.date`, `pathlib`, pydantic,
  and `.result.Refusal`. Local file I/O only — the seam (CLAUDE.md hard rule 1).

## Deviations from Plan

### [Rule 1 - Contract mismatch] Implemented the TEST signature, not the plan-prose signature
- **Found during:** Task 1, reading the contract before coding.
- **Issue:** The plan prose specifies `write(find_result, entity_type)` and
  `lookup(entity_id, entity_type)` (two args). The actually-committed RED contract
  `test_find_cache.py` (Plan 01, the binding executable contract per the project's TDD posture)
  calls `find_cache.write("campaigns", "SPONSORED_PRODUCTS", result)` and
  `find_cache.lookup("campaigns", "SPONSORED_PRODUCTS", cached_id)` — **three** args, with
  `ad_product` as a first-class cache-key dimension.
- **Fix:** Implemented to the test signatures (tests are the contract — CLAUDE.md "Tests are the
  contract"). `ad_product` is folded into the cache key and the on-disk filename
  (`ads_<entity>_<adproduct>_find_<date>.json`) so an SP campaign FIND can never satisfy an
  SB/SD lookup — a strictly safer key than the plan's entity-only scheme. All of the plan's
  must-have truths still hold verbatim (write persists a dated file, miss returns the named
  Refusal, build-time refusal, no socket, newest-wins staleness).
- **Files modified:** engine/src/habibos/find_cache.py
- **Commit:** 219d002

## Deferred Issues

### Pre-existing: `test_env.py::test_seller_id_in_env_not_code` fails in this worktree (OUT OF SCOPE)
- The test asserts `AMAZON_CA_SELLER_ID` is loaded from the gitignored `.env`. This worktree has
  no `.env`, so the env-var assertion fails — IDENTICALLY before and after this plan (documented
  in 06-01-SUMMARY). It is an environment gap, not a code regression; goes green in the
  orchestrator's real environment. Not in this plan's scope.

### Out of scope by ownership: `test_lifecycle.py` RED on missing `habibos.lifecycle`
- `test_lifecycle.py` (and `habibos.lifecycle`) are owned by the parallel plan 06-02, not yet
  merged into this worktree, so the full `uv run pytest` errors on `cannot import name
  'lifecycle'`. Untouched here by design. After the wave merges (06-02 + 06-03), the full suite
  goes green per the plan's verification note.

## Known Stubs
None. `find_cache.write`/`lookup` are fully implemented against the contract; no placeholder
values, no empty-default returns. A miss is an explicit typed `Refusal`, not a stub.

## Threat Flags
None. No new network endpoints, auth paths, or trust-boundary schema beyond the plan's
`<threat_model>` — the module imports no HTTP/socket library and only reads/writes local files.
T-06-07/08/09 are mitigated as planned (build-time miss-refusal, validate-or-raise on the item
shape, newest-dated-file-wins).

## Verification
- `cd engine && uv run pytest tests/test_find_cache.py -x` → **2 passed**
  (test_find_write_and_lookup, test_uncached_id_refuses both GREEN).
- `grep -n "def write\|def lookup" src/habibos/find_cache.py` → both present (lines 75, 111).
- `grep -n "find_cache_miss\|stale/missing entity ID" src/habibos/find_cache.py` → the refusal
  string + code present.
- `grep -n "DATA_DIR = Path(__file__).resolve().parents\[2\]" src/habibos/find_cache.py` →
  repo-root-relative path confirmed.
- `grep -nE "^(import|from) +(httpx|requests|urllib|socket|boto3)" src/habibos/find_cache.py` →
  nothing (the seam holds — no network import).
- `grep -n "ValidationError" src/habibos/find_cache.py` → present (drift surfaced, not swallowed).
- `cd engine && uv run pytest --ignore=tests/test_lifecycle.py` → 17 passed, 5 skipped, 1 failed
  (only the pre-existing `.env`-absent env-var assertion; +2 vs Plan 01's 15-passed baseline are
  the now-GREEN find_cache nodes).

## Self-Check: PASSED
- engine/src/habibos/find_cache.py — FOUND (def write @75, def lookup @111)
- Commit 219d002 — FOUND in git log
- test_find_cache.py — 2 passed (GREEN)
