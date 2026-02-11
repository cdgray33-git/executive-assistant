#!/bin/bash
# COMPLETE_PHASE3_DEPLOYMENT.sh - One-shot deployment of everything

set -e

EXEC_DIR="/home/cody/cody-v3/executive-assistant"
cd "$EXEC_DIR"

echo "+------------------------------------------------------------+"
echo "¦     EXECUTIVE ASSISTANT - COMPLETE PHASE 1-3 DEPLOY       ¦"
echo "+------------------------------------------------------------+"

# Create all directories
mkdir -p server/{managers,intelligence,services,security,connectors,llm,utils}
mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence,logs}

# Install dependencies
pip install -q fastapi uvicorn[standard] pydantic python-multipart python-dotenv imapclient email-validator httpx authlib requests python-docx python-pptx Pillow svgwrite caldav icalendar keyring cryptography python-dateutil pytz

# Create __init__ files
touch server/managers/__init__.py
touch server/intelligence/__init__.py
touch server/services/__init__.py
touch server/security/__init__.py

# Test imports
python3 -c "from server.managers.account_manager import AccountManager; from server.security.credential_vault import CredentialVault; print('? All imports successful')"

echo ""
echo "? PHASE 1-3 DEPLOYMENT COMPLETE"
echo ""
echo "Capabilities:"
echo "  ? Email: Yahoo, Gmail, Hotmail, Comcast, Apple"
echo "  ? Calendar management"
echo "  ? Contact management"
echo "  ? Meeting orchestration"
echo "  ? Document generation"
echo "  ? Notes & tasks"
echo "  ? OAuth2 authentication"
echo "  ? Secure credential storage"
echo ""
echo "Next: Run setup_account_interactive.sh to add accounts"