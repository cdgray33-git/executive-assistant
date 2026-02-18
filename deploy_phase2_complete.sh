#!/bin/bash
# Phase 2 Complete Deployment Script

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          PHASE 2: MEETING RESPONSE MONITORING              ║"
echo "║          Complete Deployment                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check we're in correct directory
if [ ! -f "server/app.py" ]; then
    echo "❌ Must run from executive-assistant root directory"
    exit 1
fi

echo "📋 Deployment Checklist:"
echo ""

# 1. Verify new files exist
echo "1. Verifying new files..."
FILES=(
    "server/database/migrations/001_meeting_responses.sql"
    "server/managers/meeting_response_parser.py"
    "server/managers/calendar_block_manager.py"
    "server/services/meeting_response_monitor.py"
    "server/assistant_functions_calendar.py"
    "scripts/reinstall_jarvis.sh"
    "scripts/create_reinstall_icon.sh"
    "scripts/run_migration.sh"
    "ui-build/src/MeetingsTab.jsx"
)

MISSING=0
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (MISSING)"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "❌ $MISSING file(s) missing! Cannot proceed."
    exit 1
fi

echo ""
echo "2. Checking dependencies..."
if grep -q "python-dateutil" requirements.txt && \
   grep -q "psycopg2" requirements.txt && \
   grep -q "sqlalchemy" requirements.txt; then
    echo "   ✅ All dependencies present"
else
    echo "   ❌ Missing dependencies in requirements.txt"
    exit 1
fi

echo ""
echo "3. Git status check..."
git status --short

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          READY TO COMMIT AND PUSH                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Review changes above"
echo "  2. Run: git add ."
echo "  3. Run: git commit -m 'Phase 2: Meeting response monitoring + calendar blocking'"
echo "  4. Run: git push origin main && git push gitlab main"
echo "  5. On Mac: git pull && ./install_mac_assistant.sh"
echo "  6. On Mac: Run migration: ./scripts/run_migration.sh"
echo ""
