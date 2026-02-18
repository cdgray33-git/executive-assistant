#!/bin/bash
# Run database migration for Phase 2

MIGRATION_FILE="server/database/migrations/001_meeting_responses.sql"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          RUNNING DATABASE MIGRATION                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Migration file not found: $MIGRATION_FILE"
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

# Run migration
echo "Running migration..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo ""
    echo "New tables/columns added:"
    echo "  • meetings.response_status"
    echo "  • meetings.attendee_responses"
    echo "  • meetings.message_id"
    echo "  • meetings.last_checked"
    echo "  • meetings.ics_uid"
    echo "  • calendar_blocks (new table)"
else
    echo ""
    echo "❌ Migration failed!"
    exit 1
fi
