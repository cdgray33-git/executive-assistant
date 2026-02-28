#!/bin/bash
# Run all database migrations

MIGRATION_DIR="server/database/migrations"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          RUNNING DATABASE MIGRATIONS                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -d "$MIGRATION_DIR" ]; then
    echo "❌ Migration directory not found: $MIGRATION_DIR"
    exit 1
fi

# Check if PostgreSQL is accessible
if ! command -v psql &> /dev/null; then
    echo "❌ psql command not found. Is PostgreSQL installed?"
    exit 1
fi

# Get database credentials from environment or use defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-jarvis_ea}"
DB_USER="${DB_USER:-postgres}"

echo "Database: $DB_NAME"
echo "Host: $DB_HOST:$DB_PORT"
echo "User: $DB_USER"
echo ""

# Run all migrations in order
for MIGRATION_FILE in $(ls -1 $MIGRATION_DIR/*.sql | sort); do
    MIGRATION_NAME=$(basename "$MIGRATION_FILE")
    echo "Running $MIGRATION_NAME..."
    
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ $MIGRATION_NAME completed"
    else
        echo "❌ $MIGRATION_NAME failed!"
        exit 1
    fi
    echo ""
done

echo "✅ All migrations completed successfully!"
