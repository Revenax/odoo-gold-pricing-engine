#!/usr/bin/env bash
# Backup PostgreSQL database with pg_dump.
#
# Usage:
#   ./scripts/backup-db.sh DATABASE_NAME [OUTPUT_FILE]
#   ./scripts/backup-db.sh mydb
#   ./scripts/backup-db.sh mydb /path/to/backup-$(date +%Y%m%d).sql
#
# Optional: set PGHOST, PGPORT, PGUSER, PGPASSWORD (or use .pgpass) for connection.

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
pg_dump --no-owner --no-acl "$DB_NAME" -f "$OUTPUT"
echo "Done. Size: $(du -h "$OUTPUT" | cut -f1)"
