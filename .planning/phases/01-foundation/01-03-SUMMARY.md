---
phase: 01-foundation
plan: 03
subsystem: hermes-runtime-context
tags: [persona, business-context, backup, hermes-desktop]
requires:
  - "01-01: live ~/.hermes install present; tests/ scaffold incl. test_context.py"
provides:
  - ".hermes-context/SOUL.md — operator persona (git source of truth)"
  - ".hermes-context/business-context.md — business/SKU/guardrail context (git source of truth)"
  - "~/.hermes/SOUL.md — deployed non-stub persona (stub replaced)"
  - "~/.hermes/memories/business-context.md — deployed runtime context"
  - "scripts/backup.sh — on-open ~/.hermes + Supabase backup"
  - "docs/backup-policy.md — proposed backup target/cadence + tested restore"
affects:
  - "All downstream agent behavior (persona enforces recommends-never-acts + no-invented-thresholds at runtime)"
tech-stack:
  added: []
  patterns:
    - "git (.hermes-context/) is source of truth; ~/.hermes is a deployment of it"
    - "native hermes backup/import (not hand-rolled tar); on-open not clock-cron"
key-files:
  created:
    - .hermes-context/SOUL.md
    - .hermes-context/business-context.md
    - scripts/backup.sh
    - docs/backup-policy.md
  modified: []
decisions:
  - "Backup = local ~/Backups/habib-os/ + Time Machine, on-open (option local-plus-timemachine)"
  - "Portable restore path = full `hermes backup -o <zip>` + `hermes import`; --quick is an internal state-snapshot (restored via /snapshot restore)"
  - "Supabase managed backups are primary; local pg_dump is a belt copy, no-op until SUPABASE_DB_URL set"
metrics:
  duration: "~10 min"
  completed: "2026-06-08"
  tasks: 2
  files: 4
---

# Phase 1 Plan 03: Hermes Persona + Business Context + Backup Summary

Replaced the `~/.hermes` SOUL.md template stub with a numbers-first,
recommends-never-acts operator persona and loaded the Habib business context,
both version-controlled in `.hermes-context/` and deployed to `~/.hermes`; then
scripted and documented an on-open native-`hermes backup` + `pg_dump` backup with
a verified `hermes import` restore.

## What Was Built

### Task 1 — Persona + business context (CTX-01, CTX-02) — commit `161db0e`
- **`.hermes-context/SOUL.md`** (git source of truth): numbers-first/terse;
  recommends-never-acts (forbidden "I negated/changed…" phrasings); never invents
  pricing/thresholds (reads Supabase `config`, refuses on missing); cites
  provenance on every number; states program scope (no summing SP/SB/SD; SP=7d,
  SB/SD=14d attribution); amazon.ca-first marketplace discipline.
- **`.hermes-context/business-context.md`** (git source of truth): Anabtawi
  Sweets / amazon.ca ~30 SKUs + US FBA expansion; DataDoe read-only single source
  (Seller Central + Amazon Ads connected); margin authority = premium Profit by
  SKU & Date; six CLAUDE.md guardrails; USD→CAD FX policy; CA-first/US-ready
  scope. Grounded in `docs/datadoe-source-map.md` — no fabricated numbers.
- **Deployed** non-destructively: existing stub backed up to
  `~/.hermes/SOUL.md.stub.bak.<ts>` before replacement; `SOUL.md` →
  `~/.hermes/SOUL.md` (byte-identical to git); `business-context.md` →
  `~/.hermes/memories/business-context.md` (the confirmed-empty context location).
- `uv run pytest tests/test_context.py::test_soul_and_context_deployed -x` → **passes**.

### Task 2 — Backup approach (CTX-03) — commit `cc4019b`
- **Decision (checkpoint:decision):** option `local-plus-timemachine` — local
  `~/Backups/habib-os/` + Time Machine, **on-open** (not clock-cron, Mac-awake
  constraint). Selected autonomously per the operator's "draft for review"
  disposition; flagged for operator confirmation in the policy doc + checklist.
- **`scripts/backup.sh`** (runnable, executable): `hermes backup --quick`
  (internal state-snapshot) + `hermes backup -o <zip>` (portable full zip) +
  `pg_dump "$SUPABASE_DB_URL"` (no-op when unset / pg_dump absent). Exercised
  end-to-end with `SUPABASE_DB_URL` unset — pg_dump correctly no-ops.
- **`docs/backup-policy.md`** (marked PROPOSED): target, on-open cadence, the
  secrets boundary (zip carries `.env`/auth — keep local, don't push to a third
  party), and the tested restore. Restore actually exercised: full zip (79 MB)
  contained the non-stub `SOUL.md` (3663 B) + `memories/business-context.md`
  (4116 B); `hermes import` into an isolated `HERMES_HOME` reproduced both with
  the live install untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `hermes backup --quick -o` does not produce a portable zip**
- **Found during:** Task 2 (first script run).
- **Issue:** `--quick` ignores `-o` and stores an *internal* state-snapshot under
  `~/.hermes/state-snapshots/` (restored via `/snapshot restore <id>`), not a
  portable file. The plan's `interfaces` block implied `--quick` + a zip; the
  `hermes import` restore path needs the **full** `hermes backup -o <zip>`.
- **Fix:** Restructured `scripts/backup.sh` so `--quick` is the fast on-open
  snapshot and the **full** `hermes backup -o <zip>` (default `RUN_FULL=1`) is
  the portable, `hermes import`-restorable artifact. Documented both restore
  paths in `docs/backup-policy.md`.
- **Files modified:** scripts/backup.sh, docs/backup-policy.md
- **Commit:** cc4019b

### Note on the test skip-guard
The plan action said "flip the skip guard" on `test_context.py`. The test has no
separate skip decorator — it skips only when the files are absent. Authoring +
deploying the files made the skip-when-absent branch fall through to the
assertions, which now pass. No code change to the test was needed.

## Threat Model Coverage
- **T-03-01 (availability of ~/.hermes):** mitigated — native backup + pg_dump,
  on-open; `hermes import` restore exercised once.
- **T-03-02 (zip carries .env/auth):** mitigated — backup target documented as
  non-shared/owned/local; explicit "don't push the secret zip to a third party"
  clause in the script header + policy.
- **T-03-03 (persona drift):** mitigated — SOUL.md encodes
  never-invent-thresholds + recommends-never-acts; git is the reviewable source,
  ~/.hermes a deployment of it.

## Known Stubs
None. (The replaced `~/.hermes/SOUL.md` template stub is intentionally retained
once as `~/.hermes/SOUL.md.stub.bak.<ts>` per the non-destructive deploy.)

## Deferred Issues (out of scope for this plan)
- `tests/test_env.py::test_seller_id_in_env_not_code` **FAILS** because
  `AMAZON_CA_SELLER_ID` is not in the environment — that is plan **01-01 Task 2**'s
  deliverable (`.env`), not this plan's. Not fixed (scope boundary).
- `tests/test_schema.py` (3) and `tests/test_config_seed.py` (1) **SKIP** pending
  `SUPABASE_DB_URL` — plan **01-02**'s deliverable. Not fixed (scope boundary).
- This plan's own test (`test_context.py::test_soul_and_context_deployed`) passes.

## Operator Review Checklist
- [ ] **Persona tone** — review `.hermes-context/SOUL.md`: is the numbers-first,
      terse, recommends-never-acts voice right for how you want the agent to talk?
- [ ] **Business specifics** — review `.hermes-context/business-context.md`: SKU
      count (~30), US-expansion framing, guardrail wording, FX (USD→CAD) policy.
- [ ] **Backup target** — confirm `~/Backups/habib-os/` (or set `HABIB_BACKUP_DIR`),
      and whether to add an off-machine copy later (external disk / Drive — note
      the secrets-exposure caveat before pushing the zip anywhere shared).
- [ ] **Backup cadence** — confirm the on-open / on-demand trigger and whether
      `RUN_FULL=1` (portable zip every run) is the right default.
- [ ] **pg_dump** — once `SUPABASE_DB_URL` is in `.env`, run `scripts/backup.sh`
      and confirm the DB dump + `psql` restore against a scratch DB.

## Self-Check: PASSED
- All 5 created files present; both deployed `~/.hermes` files present.
- Commits `161db0e` and `cc4019b` exist in history.
