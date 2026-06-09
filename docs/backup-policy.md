# Backup Policy — `~/.hermes` + Supabase truth store (CTX-03)

> **Status: PROPOSED — operator to confirm cadence and target.** This documents
> the recommended approach and records the restore test that was actually run.
> The operator should confirm (1) the backup target directory and (2) the
> on-open cadence before this is treated as settled.

## Decision

**Recommended option: local `~/Backups/` + Time Machine, triggered on-open**
(plan option `local-plus-timemachine`).

Rationale: zero extra service; Time Machine already versions the disk as a
belt-and-suspenders disk-level copy; it is the simplest to test-restore. The
operator may later add an off-machine copy (external disk or the connected
Drive) — that is a manual add-on, not required for Milestone 1.

The runtime is the **Hermes Mac desktop app**, which runs only while the Mac is
awake and open. Therefore the backup is **on-open / on-demand, NOT clock-cron**
(CLAUDE.md runtime rule; RESEARCH Pitfall 4 — a 02:00 cron silently never fires
when the Mac is asleep, making `~/.hermes` loss unrecoverable).

## What gets backed up, and how

`scripts/backup.sh` performs three steps (all native; no hand-rolled tar):

| # | Command | Covers | Restore with |
|---|---------|--------|--------------|
| 1 | `hermes backup --quick -l <label>` | Fast **internal state-snapshot** of critical state (config, `state.db`, `.env`, auth, cron) under `~/.hermes/state-snapshots/`. | `/snapshot restore <id>` |
| 2 | `hermes backup -o <zip>` | **Portable full zip** — config, skills, sessions, `memories/` (incl. `SOUL.md` + `business-context.md`), data. | `hermes import <zip>` |
| 3 | `pg_dump "$SUPABASE_DB_URL" > <file>.sql` | The Supabase **truth store** (`sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config`). **No-op** if `SUPABASE_DB_URL` is unset or `pg_dump` is absent. | `psql "$SUPABASE_DB_URL" < <file>.sql` |

> **Note on `--quick`:** verified this session that `hermes backup --quick`
> ignores `-o` and writes an *internal* state-snapshot (restored via
> `/snapshot restore`), not a portable file. The portable, `hermes import`-able
> artifact is the **full** `hermes backup -o <zip>` — that is the primary
> recovery path for `~/.hermes`.

### Target directory and cadence (proposed — confirm)

- **Target:** `~/Backups/habib-os/` (override with `HABIB_BACKUP_DIR`).
- **Cadence:** on-open / on-demand. Run `scripts/backup.sh` when opening the
  workspace for a session, and before any risky change (migration, skill edit).
  `RUN_FULL=1` (the default) produces the portable full zip; set `RUN_FULL=0`
  for a lighter quick-snapshot-only run.
- **Supabase:** managed Supabase backups remain the **primary** DB recovery
  path. The local `pg_dump` is a periodic belt copy of the truth tables, and is
  a no-op until `SUPABASE_DB_URL` is set in the environment.

## Secrets boundary (threat T-03-02)

The `hermes backup` zip **contains `.env` and auth tokens**. Keep the backup
target a **non-shared, owned, local** location. Time Machine versions it at the
disk level. **Do not push the secret-bearing zip to a third party** (e.g. Drive)
without explicitly accepting and documenting that secret exposure here first.

## Restore test (exercised once — required by the plan)

The portable restore path was **tested this session**:

1. `hermes backup -o <tmp>/hermes-full-test.zip` produced a 79 MB zip.
   Verified it contained the deployed non-stub `SOUL.md` (3663 bytes) and
   `memories/business-context.md` (4116 bytes).
2. `HERMES_HOME=<isolated-tmp> hermes import <tmp>/hermes-full-test.zip`
   restored into an **isolated** `HERMES_HOME` (the live install was untouched).
3. Verified the restored `SOUL.md` was the non-stub persona
   ("Habib OS — Operator Persona", contains "recommend") and that
   `memories/business-context.md` was present.

Result: **restore confirmed working.** Test artifacts were cleaned up.

## Open items for the operator

- [ ] Confirm the backup target directory (`~/Backups/habib-os/` or other).
- [ ] Confirm the on-open cadence (and whether to add an off-machine copy later).
- [ ] Once Supabase strings are in `.env`, confirm the `pg_dump` step runs and
      the `psql` restore works against a scratch database.
