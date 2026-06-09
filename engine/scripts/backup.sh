#!/usr/bin/env bash
#
# Habib OS — on-open backup of ~/.hermes + the Supabase truth store.
#
# RUNTIME: the Hermes Mac desktop app runs only while the Mac is awake/open, so
# this is an ON-OPEN / ON-DEMAND backup, NOT a clock-cron job (CLAUDE.md runtime
# rule; RESEARCH Pitfall 4). Run it by hand or wire it to an on-open trigger.
#
# WHAT IT DOES (proposed approach — operator to confirm target + cadence):
#   1. hermes backup --quick   -> fast INTERNAL state-snapshot of critical
#      ~/.hermes state (config, state.db, .env, auth, cron). NOTE: --quick
#      ignores -o and stores a snapshot under ~/.hermes/state-snapshots/,
#      restored with `/snapshot restore <id>` (verified this session). It is the
#      fast on-open safety net, not a portable file.
#   2. hermes backup -o <zip>  -> the PORTABLE full zip (config, skills,
#      sessions, memories incl. SOUL.md + business-context.md, data). This is the
#      one restored with `hermes import <zip>` — the tested restore path. On by
#      default; set RUN_FULL=0 to skip on lighter runs.
#   3. pg_dump "$SUPABASE_DB_URL" -> the Supabase truth tables. NO-OP if
#      SUPABASE_DB_URL is unset or pg_dump is unavailable (managed Supabase
#      backups remain the primary DB recovery path; this is a local belt copy).
#
# SECRETS NOTE (threat T-03-02): the hermes backup zip carries .env/auth. Keep
# BACKUP_DIR a non-shared, owned, local location. Time Machine versions it at the
# disk level. Do NOT push the secret-bearing zip to a third party.
#
# Restore paths (the full-zip path was tested once — see docs/backup-policy.md):
#   hermes import <backup-dir>/hermes-full-<date>.zip        # portable full
#   /snapshot restore <id>                                   # quick snapshot
#   psql "$SUPABASE_DB_URL" < <backup-dir>/supabase-<date>.sql

set -euo pipefail

# --- Config (override via env) ---------------------------------------------
BACKUP_DIR="${HABIB_BACKUP_DIR:-$HOME/Backups/habib-os}"
RUN_FULL="${RUN_FULL:-1}"          # 1 = also take the portable full zip (hermes import path)
DATE="$(date +%Y%m%d_%H%M%S)"
LABEL="onopen-${DATE}"

log() { printf '[backup %s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }

mkdir -p "$BACKUP_DIR"
log "backup dir: $BACKUP_DIR"

# --- 1. Hermes quick snapshot (native; do not hand-roll a tar) -------------
if command -v hermes >/dev/null 2>&1; then
  # Fast internal state-snapshot (restored via `/snapshot restore <id>`).
  log "hermes backup --quick -l $LABEL (internal state-snapshot)"
  hermes backup --quick -l "$LABEL"

  # --- 2. Portable full backup (the `hermes import` restore path) ---------
  if [ "$RUN_FULL" = "1" ]; then
    FULL_ZIP="$BACKUP_DIR/hermes-full-${DATE}.zip"
    log "hermes backup (full, portable) -> $FULL_ZIP"
    hermes backup -o "$FULL_ZIP"
    log "restore with: hermes import \"$FULL_ZIP\""
  else
    log "skipping full hermes backup (set RUN_FULL=1 to enable the portable zip)"
  fi
else
  log "WARNING: 'hermes' CLI not found on PATH — skipping ~/.hermes backup"
fi

# --- 3. Supabase truth store (pg_dump; no-op without SUPABASE_DB_URL) -------
if [ -n "${SUPABASE_DB_URL:-}" ]; then
  if command -v pg_dump >/dev/null 2>&1; then
    DUMP="$BACKUP_DIR/supabase-${DATE}.sql"
    log "pg_dump Supabase truth store -> $DUMP"
    pg_dump "$SUPABASE_DB_URL" >"$DUMP"
    log "pg_dump complete"
  else
    log "SUPABASE_DB_URL set but pg_dump not installed — skipping DB dump"
    log "(managed Supabase backups remain the primary DB recovery path)"
  fi
else
  log "SUPABASE_DB_URL unset — skipping pg_dump (no-op; managed Supabase backups apply)"
fi

log "done."
