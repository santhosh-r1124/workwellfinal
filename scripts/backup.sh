#!/usr/bin/env bash
# Back up and restore the one thing that matters.
#
# Postgres holds everything: consent history, baselines, the audit log.
# Redis holds queued jobs and rate-limit counters, all of which rebuild
# themselves - the daily sweep re-enqueues, so a lost queue costs a delay,
# not data.
#
# The point of this script is the restore half. A backup nobody has
# restored is a file, not a backup, and the failure mode - a dump that
# was silently truncated for months - is only visible by loading it.
#
#   scripts/backup.sh dump                  -> backups/workwell-<stamp>.sql.gz
#   scripts/backup.sh verify <file>         restore into a scratch database
#                                           and check it, then drop it
#   scripts/backup.sh restore <file> <db>   restore into a named database
#
# Retention note: the admin retention window deletes telemetry past its
# limit. A backup from before a retention run still holds it, so prune
# backups on the same schedule or the promise made in the Privacy Centre
# stops being true.

set -euo pipefail

HOST="${POSTGRES_HOST:-localhost}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER:-workwell}"
DB="${POSTGRES_DB:-workwell}"
DIR="${BACKUP_DIR:-backups}"

export PGPASSWORD="${POSTGRES_PASSWORD:-workwell}"

die() { echo "error: $*" >&2; exit 1; }

cmd_dump() {
  mkdir -p "$DIR"
  local out="$DIR/workwell-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
  pg_dump -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" --no-owner --no-acl \
    | gzip > "$out"

  # A dump that failed halfway still leaves a readable gzip, so check the
  # marker pg_dump writes last rather than trusting the exit code alone.
  gunzip -c "$out" | tail -5 | grep -q "PostgreSQL database dump complete" \
    || die "dump is incomplete - not keeping $out"

  echo "$out  ($(du -h "$out" | cut -f1))"
}

restore_into() {
  local file="$1" target="$2"
  [ -f "$file" ] || die "no such file: $file"

  psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -v ON_ERROR_STOP=1 -q \
    -c "DROP DATABASE IF EXISTS \"$target\";" -c "CREATE DATABASE \"$target\";"
  # -o /dev/null: a restore prints a row for every SET in the dump, which
  # buries the counts that are the actual point of verifying.
  gunzip -c "$file" \
    | psql -h "$HOST" -p "$PORT" -U "$USER" -d "$target" -q -v ON_ERROR_STOP=1 -o /dev/null
}

cmd_verify() {
  local file="${1:-}"
  [ -n "$file" ] || die "usage: $0 verify <file>"
  local scratch="workwell_restore_check"

  echo "restoring $file into $scratch ..."
  restore_into "$file" "$scratch"

  # Row counts, not just "it loaded": an empty restore also loads.
  local report
  report=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$scratch" -tA -F' ' -c "
    SELECT 'users', count(*) FROM users
    UNION ALL SELECT 'daily_features', count(*) FROM daily_features
    UNION ALL SELECT 'consents', count(*) FROM consents
    UNION ALL SELECT 'audit_logs', count(*) FROM audit_logs
    UNION ALL SELECT 'knowledge_chunks', count(*) FROM knowledge_chunks;")

  echo "$report" | while read -r table count; do
    printf '  %-18s %s\n' "$table" "$count"
  done

  local users
  users=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$scratch" -tA -c "SELECT count(*) FROM users;")
  local revision
  revision=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d "$scratch" -tA -c "SELECT version_num FROM alembic_version;")
  echo "  schema revision    $revision"

  psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -q -c "DROP DATABASE \"$scratch\";"

  [ "$users" -gt 0 ] || die "restore produced no users - this backup is not usable"
  echo "restore verified"
}

cmd_restore() {
  local file="${1:-}" target="${2:-}"
  [ -n "$file" ] && [ -n "$target" ] || die "usage: $0 restore <file> <database>"
  [ "$target" != "$DB" ] || die "refusing to overwrite the live database '$DB' - restore into a new name and switch over"

  restore_into "$file" "$target"
  echo "restored into $target"
}

case "${1:-}" in
  dump)    shift; cmd_dump "$@" ;;
  verify)  shift; cmd_verify "$@" ;;
  restore) shift; cmd_restore "$@" ;;
  *) die "usage: $0 {dump|verify <file>|restore <file> <database>}" ;;
esac
