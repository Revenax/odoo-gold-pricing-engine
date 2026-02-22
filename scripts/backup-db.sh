#!/usr/bin/env bash
# Backup PostgreSQL database with pg_dump.
#
# Usage:
#   ./scripts/backup-db.sh DATABASE_NAME [OUTPUT_FILE]
#   ./scripts/backup-db.sh mydb
#   ./scripts/backup-db.sh mydb /path/to/backup-$(date +%Y%m%d).sql
#
# On Ubuntu, if you get "role \"$(whoami)\" does not exist", the script will
# run pg_dump as system user postgres (via sudo). Otherwise set PGUSER/PGPASSWORD.
# Optional: PGHOST, PGPORT, PGUSER, PGPASSWORD (or .pgpass) for connection.

set -euo pipefail

DB_NAME="${1:?Usage: $0 DATABASE_NAME [OUTPUT_FILE]}"
OUTPUT="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_OUTPUT="$PROJECT_ROOT/backups/${DB_NAME}-$(date +%Y%m%d-%H%M%S).sql"

if [ -z "$OUTPUT" ]; then
  mkdir -p "$PROJECT_ROOT/backups"
  OUTPUT="$DEFAULT_OUTPUT"
fi

echo "Backing up database: $DB_NAME -> $OUTPUT"

_run_dump() {
  pg_dump --no-owner --no-acl "$DB_NAME" -f "$1"
}

if [ -n "${PGUSER:-}" ] || [ -n "${PGPASSWORD:-}" ] || [ -n "${PGHOST:-}" ]; then
  _run_dump "$OUTPUT"
else
  TMP_OUT="$(mktemp)"
  trap 'sudo rm -f "$TMP_OUT"' EXIT
  if sudo -u postgres pg_dump --no-owner --no-acl "$DB_NAME" -f "$TMP_OUT"; then
    sudo cp "$TMP_OUT" "$OUTPUT" && sudo chown "$(whoami):$(id -gn)" "$OUTPUT"
    sudo rm -f "$TMP_OUT"
    trap - EXIT
  else
    echo "Backup failed. On Ubuntu, PostgreSQL often allows only the postgres role. Try: sudo -u postgres $0 $DB_NAME"
    exit 1
  fi
fi

echo "Done. Size: $(du -h "$OUTPUT" | cut -f1)"
