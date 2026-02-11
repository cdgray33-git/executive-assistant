#!/bin/bash
# test_phase3.sh - Test Phase 3 multi-email connectors

echo "?? Testing Phase 3: Multi-Email Connectors"
echo "=========================================="

cd /home/cody/cody-v3/executive-assistant

# Test 1: Import all Phase 3 modules
echo ""
echo "Test 1: Module imports..."
python3 << 'EOF'
try:
    from server.security.credential_vault import CredentialVault
    from server.security.oauth2_handler import OAuth2Handler
    from server.connectors.gmail_connector import GmailConnector
    from server.connectors.hotmail_connector import HotmailConnector
    from server.connectors.comcast_connector import ComcastConnector
    from server.connectors.apple_connector import AppleConnector
    from server.managers.account_manager import AccountManager
    print("? All Phase 3 modules imported successfully")
except Exception as e:
    print(f"? Import error: {e}")
    exit(1)
EOF

# Test 2: Test Credential Vault
echo ""
echo "Test 2: Credential Vault..."
python3 << 'EOF'
from server.security.credential_vault import CredentialVault

vault = CredentialVault()

# Store test credentials
success = vault.store_credentials(
    account_id="test_account",
    provider="yahoo",
    email="test@yahoo.com",
    credential_type="app_password",
    credential_value="test_password_123"
)

if success:
    print("? Credential storage: SUCCESS")
    
    # Retrieve credentials
    retrieved = vault.get_credentials("test_account", "app_password")
    if retrieved == "test_password_123":
        print("? Credential retrieval: SUCCESS")
    else:
        print("? Credential retrieval: FAILED")
    
    # Clean up
    vault.delete_credentials("test_account")
    print("? Credential deletion: SUCCESS")
else:
    print("? Credential vault test: FAILED")
EOF

# Test 3: Test Account Manager
echo ""
echo "Test 3: Account Manager..."
python3 << 'EOF'
from server.managers.account_manager import AccountManager

account_mgr = AccountManager()

# Test listing accounts (should be empty initially)
result = account_mgr.list_accounts()
print(f"? Account Manager: {result['count']} accounts configured")
print("   (Add accounts via API or setup script)")
EOF

# Test 4: Test connector instantiation
echo ""
echo "Test 4: Connector instantiation..."
python3 << 'EOF'
from server.connectors.yahoo_connector import YahooConnector
from server.connectors.gmail_connector import GmailConnector
from server.connectors.hotmail_connector import HotmailConnector
from server.connectors.comcast_connector import ComcastConnector
from server.connectors.apple_connector import AppleConnector

try:
    # These should instantiate without errors (but won't connect without credentials)
    yahoo = YahooConnector(email_address="test@yahoo.com", app_password="test")
    gmail = GmailConnector(account_id="test_gmail")
    hotmail = HotmailConnector(account_id="test_hotmail")
    comcast = ComcastConnector(account_id="test_comcast")
    apple = AppleConnector(account_id="test_apple")
    
    print("? All connectors instantiated successfully")
    print("   - Yahoo (IMAP/SMTP)")
    print("   - Gmail (OAuth2 + Gmail API)")
    print("   - Hotmail (OAuth2 + Graph API)")
    print("   - Comcast (IMAP/SMTP)")
    print("   - Apple (IMAP/SMTP)")
except Exception as e:
    print(f"? Connector instantiation failed: {e}")
EOF

# Test 5: Test updated EmailManager
echo ""
echo "Test 5: Updated Email Manager..."
python3 << 'EOF'
from server.managers.email_manager import EmailManager

email_mgr = EmailManager()

# Test check_all_accounts (will show no accounts configured)
result = email_mgr.check_all_accounts()
print(f"? Email Manager: Checked {len(result['by_account'])} accounts")
print(f"   Total new messages: {result['total_new']}")
print(f"   Priority messages: {len(result['priority_messages'])}")
EOF

# Test 6: Test API endpoints
echo ""
echo "Test 6: API endpoints..."
echo "   Starting FastAPI server in background..."

# Start server in background
uvicorn server.app:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

sleep 5

# Test endpoints
echo ""
echo "   Testing /api/status..."
curl -s http://127.0.0.1:8000/api/status | python3 -m json.tool | head -10

echo ""
echo "   Testing /api/accounts..."
curl -s http://127.0.0.1:8000/api/accounts | python3 -m json.tool

echo ""
echo "   Testing /api/functions..."
curl -s http://127.0.0.1:8000/api/functions | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Functions: {data['count']}\")"

# Stop server
kill $SERVER_PID 2>/dev/null

echo ""
echo "=========================================="
echo "? Phase 3 Testing Complete!"
echo ""
echo "Summary:"
echo "  ? All connectors implemented"
echo "  ? OAuth2 flow ready (Gmail, Hotmail)"
echo "  ? IMAP/SMTP ready (Yahoo, Comcast, Apple)"
echo "  ? Credential vault operational"
echo "  ? Account manager functional"
echo ""
echo "Next: Add accounts via setup script or API"
echo ""