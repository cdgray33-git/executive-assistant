#!/bin/bash
# deploy_phase3.sh - Complete Phase 3 deployment

echo "?? Deploying Phase 3: Multi-Email Connectors"
echo "============================================="

cd /home/cody/cody-v3/executive-assistant

# Step 1: Verify all files exist
echo ""
echo "Step 1/5: Verifying Phase 3 files..."

REQUIRED_FILES=(
    "server/security/credential_vault.py"
    "server/security/oauth2_handler.py"
    "server/security/__init__.py"
    "server/connectors/gmail_connector.py"
    "server/connectors/hotmail_connector.py"
    "server/connectors/comcast_connector.py"
    "server/connectors/apple_connector.py"
    "server/managers/account_manager.py"
)

ALL_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "? Missing: $file"
        ALL_EXIST=false
    fi
done

if [ "$ALL_EXIST" = false ]; then
    echo "? Some files are missing"
    exit 1
fi

echo "? All Phase 3 files present"

# Step 2: Install dependencies
echo ""
echo "Step 2/5: Installing dependencies..."
pip install -r server/requirements.txt --quiet

if [ $? -eq 0 ]; then
    echo "? Dependencies installed"
else
    echo "? Dependency installation failed"
    exit 1
fi

# Step 3: Run tests
echo ""
echo "Step 3/5: Running tests..."
bash test_phase3.sh

if [ $? -ne 0 ]; then
    echo "? Tests failed"
    exit 1
fi

# Step 4: Backup
echo ""
echo "Step 4/5: Creating backup..."
cp server/app.py server/app.py.backup.phase2
echo "? Backup created"

# Step 5: Git commit
echo ""
echo "Step 5/5: Committing to version control..."
if [ -d .git ]; then
    git add .
    git commit -m "Phase 3 Complete: Multi-Email Connectors

Implemented:
- OAuth2 Handler (Gmail, Hotmail authorization flow)
- Credential Vault (macOS Keychain integration)
- Gmail Connector (Gmail API with OAuth2)
- Hotmail Connector (Microsoft Graph API with OAuth2)
- Comcast Connector (IMAP/SMTP)
- Apple iCloud Connector (IMAP/SMTP)
- Account Manager (multi-account orchestration)
- Updated Email Manager (supports all providers)
- Account management API endpoints

Security:
- Secure credential storage in macOS Keychain
- OAuth2 token management with refresh
- Encrypted storage for sensitive data

Ready for Phase 4: Intelligence Layer (AI learning engines)
"
    echo "? Changes committed"
else
    echo "??  Not a git repository"
fi

echo ""
echo "============================================="
echo "? Phase 3 Deployment Complete!"
echo ""
echo "?? Summary:"
echo "   • 5 email connectors implemented"
echo "   • OAuth2 flow operational"
echo "   • Secure credential storage"
echo "   • Multi-account management"
echo ""
echo "?? Next Steps:"
echo "   1. Run: bash setup_account_interactive.sh"
echo "   2. Add your email accounts"
echo "   3. Test: curl http://localhost:8000/api/accounts/test"
echo "   4. Ready for Phase 4: Intelligence Layer"
echo ""
echo "============================================="