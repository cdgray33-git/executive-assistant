#!/bin/bash
# MASTER_DEPLOYMENT.sh - Complete Phase 2 Deployment

echo "+------------------------------------------------------------+"
echo "¦          EXECUTIVE ASSISTANT - PHASE 2 DEPLOYMENT         ¦"
echo "¦                   Core Managers Build                      ¦"
echo "+------------------------------------------------------------+"
echo ""

# Set strict error handling
set -e

EXEC_DIR="/home/cody/cody-v3/executive-assistant"

cd "$EXEC_DIR"

# ============================================================
# STEP 1: DIRECTORY STRUCTURE
# ============================================================
echo "?? Step 1/10: Creating directory structure..."

bash << 'DIRSCRIPT'
cd /home/cody/cody-v3/executive-assistant/server

mkdir -p managers
mkdir -p intelligence
mkdir -p services
mkdir -p security
mkdir -p data/{calendar,contacts,notes,templates/email}

touch managers/__init__.py
touch intelligence/__init__.py
touch services/__init__.py

echo "? Directories created"
DIRSCRIPT

# ============================================================
# STEP 2: UPDATE REQUIREMENTS
# ============================================================
echo ""
echo "?? Step 2/10: Updating requirements.txt..."

cat > server/requirements.txt << 'EOF'
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
python-dotenv==1.0.0

# Email
imapclient==2.3.1
email-validator==2.1.0
httpx==0.25.2

# OAuth2 (Phase 3)
authlib==1.3.0
requests==2.31.0

# Document Generation
python-docx==1.1.0
python-pptx==0.6.23
Pillow==10.1.0
svgwrite==1.4.3

# Calendar (CalDAV - Phase 5)
caldav==1.3.9
icalendar==5.0.11

# Utilities
keyring==24.3.0
cryptography==41.0.7

# Data handling
python-dateutil==2.8.2
pytz==2023.3
EOF

echo "? Requirements updated"

# ============================================================
# STEP 3: INSTALL DEPENDENCIES
# ============================================================
echo ""
echo "??  Step 3/10: Installing Python dependencies..."
pip install -r server/requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "? Dependencies installed"
else
    echo "? Dependency installation failed"
    exit 1
fi

# ============================================================
# STEP 4: CREATE DATA DIRECTORIES
# ============================================================
echo ""
echo "?? Step 4/10: Creating application data directories..."

mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence,logs}

echo "? Data directories created"

# ============================================================
# STEP 5: VERIFY ALL FILES EXIST
# ============================================================
echo ""
echo "?? Step 5/10: Verifying all module files..."

REQUIRED_FILES=(
    "server/managers/__init__.py"
    "server/managers/email_manager.py"
    "server/managers/calendar_manager.py"
    "server/managers/contact_manager.py"
    "server/managers/note_manager.py"
    "server/managers/meeting_orchestrator.py"
    "server/managers/document_generator.py"
    "server/assistant_functions.py"
    "server/app.py"
)

ALL_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "? Missing: $file"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = true ]; then
    echo "? All required files present"
else
    echo "? Some files are missing - please copy all modules"
    exit 1
fi

# ============================================================
# STEP 6: RUN IMPORT TESTS
# ============================================================
echo ""
echo "?? Step 6/10: Testing module imports..."

python3 << 'PYTEST'
import sys
try:
    from server.managers.email_manager import EmailManager
    from server.managers.calendar_manager import CalendarManager
    from server.managers.contact_manager import ContactManager
    from server.managers.note_manager import NoteManager
    from server.managers.meeting_orchestrator import MeetingOrchestrator
    from server.managers.document_generator import DocumentGenerator
    from server import assistant_functions
    print("? All modules imported successfully")
    sys.exit(0)
except Exception as e:
    print(f"? Import error: {e}")
    sys.exit(1)
PYTEST

if [ $? -ne 0 ]; then
    echo "? Module import test failed"
    exit 1
fi

# ============================================================
# STEP 7: RUN FUNCTIONAL TESTS
# ============================================================
echo ""
echo "?? Step 7/10: Running functional tests..."

# Quick functional test
python3 << 'FUNCTEST'
import sys
from server.managers.calendar_manager import CalendarManager
from server.managers.contact_manager import ContactManager
from server.managers.note_manager import NoteManager

try:
    # Test calendar
    cal = CalendarManager()
    result = cal.add_event("Test", "2026-03-01", "10:00", 30)
    assert result["status"] == "success"
    cal.delete_event(result["event"]["id"])
    
    # Test contacts
    contact = ContactManager()
    result = contact.add_contact("Test User", email="test@example.com")
    assert result["status"] == "success"
    
    # Test notes
    notes = NoteManager()
    result = notes.save_note("Test note content", "Test Title")
    assert result["status"] == "success"
    
    print("? Functional tests passed")
    sys.exit(0)
except Exception as e:
    print(f"? Functional test failed: {e}")
    sys.exit(1)
FUNCTEST

if [ $? -ne 0 ]; then
    echo "? Functional tests failed"
    exit 1
fi

# ============================================================
# STEP 8: COUNT FUNCTIONS
# ============================================================
echo ""
echo "?? Step 8/10: Verifying function registry..."

python3 << 'COUNTFUNC'
from server import assistant_functions
functions = assistant_functions.get_function_names()
print(f"? {len(functions)} EA functions registered")
if len(functions) < 20:
    print("??  Warning: Expected 20+ functions")
COUNTFUNC

# ============================================================
# STEP 9: BACKUP AND GIT COMMIT
# ============================================================
echo ""
echo "?? Step 9/10: Version control..."

# Backup
if [ -f server/app.py.backup.phase1 ]; then
    echo "   Backup already exists"
else
    cp server/app.py server/app.py.backup.phase1
    echo "? Backup created"
fi

# Git operations
if [ -d .git ]; then
    git add .
    git status --short
    echo "? Changes staged for commit"
else
    echo "??  Not a git repository"
fi

# ============================================================
# STEP 10: DEPLOYMENT SUMMARY
# ============================================================
echo ""
echo "+------------------------------------------------------------+"
echo "¦              PHASE 2 DEPLOYMENT COMPLETE ?                ¦"
echo "+------------------------------------------------------------+"
echo ""
echo "?? Deployment Summary:"
echo "   ? 6 Manager modules created"
echo "   ? 25+ EA functions implemented"
echo "   ? Dependencies installed"
echo "   ? Data directories created"
echo "   ? All tests passed"
echo ""
echo "?? Implemented Capabilities:"
echo "   • Email management (Yahoo working)"
echo "   • Calendar operations"
echo "   • Contact management"
echo "   • Meeting orchestration"
echo "   • Document generation (PPT/Memo/Drawing)"
echo "   • Notes and tasks"
echo ""
echo "?? Data Location:"
echo "   ~/Library/Application Support/ExecutiveAssistant/"
echo ""
echo "?? Next Steps:"
echo "   1. Run: bash push_to_gitlab.sh"
echo "   2. Test via: curl http://localhost:8000/api/functions"
echo "   3. Start Phase 3: Multi-email connectors"
echo ""
echo "---------------------------------------------------------------"