#!/bin/sh

ALEMBIC_CONFIG="/usr/src/alembic/alembic.ini"
MIGRATIONS_DIR="/usr/src/fastapi/database/migrations/versions"

echo "Checking for changes before generating a migration..."

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "Migrations folder does not exist. Creating it..."
  mkdir -p "$MIGRATIONS_DIR"
fi

export PGPASSWORD="$POSTGRES_PASSWORD"

if ! psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt" | grep -q "alembic_version"; then
  echo "Alembic version table not found. Applying all migrations..."

  if [ -z "$(ls -A "$MIGRATIONS_DIR")" ]; then
    echo "No migration files found. Generating initial migration..."
    alembic -c $ALEMBIC_CONFIG revision --autogenerate -m "initial migration"
  fi

  echo "Applying all migrations..."
  alembic -c $ALEMBIC_CONFIG upgrade head
#
#  echo "Running database saver script..."
#  python -m database.populate
#  echo "Database saver script completed."

  exit 0
fi

if ! alembic -c $ALEMBIC_CONFIG revision --autogenerate -m "temp_migration"; then
  echo "Error generating migration. Exiting."
  exit 1
fi

LAST_MIGRATION=$(find "$MIGRATIONS_DIR" -type f -printf '%T+ %p\n' | sort | tail -n 1 | awk '{print $2}' )

echo "Generated migration content:"
cat "$LAST_MIGRATION"

if grep -qE '^\s*pass\s*$' "$LAST_MIGRATION"; then
  echo "No changes detected. Deleting temporary migration."
  rm "$LAST_MIGRATION"
else
  echo "Changes detected. Applying migration."
  alembic -c $ALEMBIC_CONFIG upgrade head
fi

#echo "Running database saver script..."
#python -m database.populate
#echo "Database saver script completed."
