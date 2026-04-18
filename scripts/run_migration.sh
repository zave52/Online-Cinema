#!/bin/sh

set -eu

ALEMBIC_CONFIG="/opt/alembic/alembic.ini"
MIGRATIONS_DIR="/opt/app/database/migrations/versions"

echo "Checking for changes before generating a migration..."

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Migrations folder does not exist. Creating it..."
  mkdir -p "$MIGRATIONS_DIR"
fi

list_migration_files() {
  for file in "$MIGRATIONS_DIR"/*.py; do
    [ -e "$file" ] || continue
    basename "$file"
  done | sort
}

export PGPASSWORD="$POSTGRES_PASSWORD"

NEEDS_BOOTSTRAP=0

if command -v psql >/dev/null 2>&1; then
  if ! psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt" 2>/dev/null | grep -q "alembic_version"; then
    NEEDS_BOOTSTRAP=1
  fi
else
  echo "psql not found. Falling back to Alembic check."
  if ! alembic -c "$ALEMBIC_CONFIG" current >/dev/null 2>&1; then
    NEEDS_BOOTSTRAP=1
  fi
fi

if [ "$NEEDS_BOOTSTRAP" -eq 1 ]; then
  echo "Alembic version table not found. Applying all migrations..."

  if [ -z "$(ls -A "$MIGRATIONS_DIR")" ]; then
    echo "No migration files found. Generating initial migration..."
    alembic -c "$ALEMBIC_CONFIG" revision --autogenerate -m "initial migration"
  fi

  echo "Applying all migrations..."
  alembic -c "$ALEMBIC_CONFIG" upgrade head
#
#  echo "Running database saver script..."
#  python -m database.populate
#  echo "Database saver script completed."

  exit 0
fi

echo "Ensuring database is at latest migration before autogenerate check..."
if ! alembic -c "$ALEMBIC_CONFIG" upgrade head; then
  echo "Failed to upgrade database to head. Exiting."
  exit 1
fi

BEFORE_TMP=$(mktemp)
AFTER_TMP=$(mktemp)
trap 'rm -f "$BEFORE_TMP" "$AFTER_TMP"' EXIT

list_migration_files > "$BEFORE_TMP"

if ! alembic -c "$ALEMBIC_CONFIG" revision --autogenerate -m "temp_migration"; then
  echo "Error generating migration. Exiting."
  exit 1
fi

list_migration_files > "$AFTER_TMP"
LAST_MIGRATION=$(comm -13 "$BEFORE_TMP" "$AFTER_TMP" | tail -n 1)

if [ -z "$LAST_MIGRATION" ]; then
  echo "Could not detect generated migration file. Exiting."
  exit 1
fi

LAST_MIGRATION="$MIGRATIONS_DIR/$LAST_MIGRATION"

echo "Generated migration content:"
cat "$LAST_MIGRATION"

if grep -qE '^[[:space:]]*pass[[:space:]]*$' "$LAST_MIGRATION"; then
  echo "No changes detected. Deleting temporary migration."
  rm "$LAST_MIGRATION"
else
  echo "Changes detected. Applying migration."
  alembic -c "$ALEMBIC_CONFIG" upgrade head
fi

#echo "Running database saver script..."
#python -m database.populate
#echo "Database saver script completed."
