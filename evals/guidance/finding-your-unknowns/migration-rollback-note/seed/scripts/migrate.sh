#!/usr/bin/env bash
# Apply every migration in name order to the database named by $DB_PATH.
set -euo pipefail
for f in db/migrations/*.sql; do
  sqlite3 "${DB_PATH:?set DB_PATH}" < "$f"
done
