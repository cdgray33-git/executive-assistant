#!/bin/bash
# setup_account_interactive.sh - Interactive account setup

echo "+-------------------------------------------------------+"
echo "¦       EXECUTIVE ASSISTANT - ACCOUNT SETUP             ¦"
echo "+-------------------------------------------------------+"
echo ""

# Function to add Yahoo/Comcast/Apple account
add_password_account() {
    PROVIDER=$1
    
    echo ""
    echo "Adding $PROVIDER account..."
    echo "?????????????????????????????????????????"
    
    read -p "Account ID (e.g., my_yahoo): " ACCOUNT_ID
    read -p "Email address: " EMAIL
    read -sp "App password: " APP_PASSWORD
    echo ""
    
    # Add account via Python
    python3 << EOF
from server.managers.account_manager import AccountManager

account_mgr = AccountManager()
result = account_mgr.add_account_password(
    account_id="$ACCOUNT_ID",
    provider="$PROVIDER",
    email="$EMAIL",
    app_password="$APP_PASSWORD"
)

if result["status"] == "success":
    print("? Account added successfully!")
else:
    print(f"? Error: {result.get('error')}")
EOF
}

# Function to add Gmail/Hotmail account
add_oauth_account() {
    PROVIDER=$1
    
    echo ""
    echo "Adding $PROVIDER account (OAuth2)..."
    echo "?????????????????????????????????????????"
    echo ""
    echo "??  You will need OAuth2 credentials from:"
    if [ "$PROVIDER" == "gmail" ]; then
        echo "   Google Cloud Console: https://console.cloud.google.com/"
    else
        echo "   Azure Portal: https://portal.azure.com/"
    fi
    echo ""
    
    read -p "Account ID (e.g., my_gmail): " ACCOUNT_ID
    read -p "Email address: " EMAIL
    read -p "Client ID: " CLIENT_ID
    read -sp "Client Secret: " CLIENT_SECRET
    echo ""
    
    echo ""
    echo "?? Opening browser for authorization..."
    echo "   Please complete the OAuth2 flow in your browser."
    echo ""
    
    # Add account via Python (will open browser)
    python3 << EOF
from server.managers.account_manager import AccountManager

account_mgr = AccountManager()
result = account_mgr.add_account_oauth(
    account_id="$ACCOUNT_ID",
    provider="$PROVIDER",
    email="$EMAIL",
    client_id="$CLIENT_ID",
    client_secret="$CLIENT_SECRET"
)

if result["status"] == "success":
    print("? Account authorized and added successfully!")
else:
    print(f"? Error: {result.get('error')}")
EOF
}

# Main menu
while true; do
    echo ""
    echo "Select email provider to add:"
    echo "  1) Yahoo"
    echo "  2) Gmail (OAuth2)"
    echo "  3) Hotmail/Outlook (OAuth2)"
    echo "  4) Comcast"
    echo "  5) Apple iCloud"
    echo "  6) List configured accounts"
    echo "  7) Test all accounts"
    echo "  8) Exit"
    echo ""
    read -p "Choice: " CHOICE
    
    case $CHOICE in
        1) add_password_account "yahoo" ;;
        2) add_oauth_account "gmail" ;;
        3) add_oauth_account "hotmail" ;;
        4) add_password_account "comcast" ;;
        5) add_password_account "apple" ;;
        6)
            echo ""
            python3 << 'EOF'
from server.managers.account_manager import AccountManager
account_mgr = AccountManager()
result = account_mgr.list_accounts()
print(f"Configured accounts: {result['count']}")
for acc in result.get('accounts', []):
    print(f"  - {acc['account_id']}: {acc['email']} ({acc['provider']})")
EOF
            ;;
        7)
            echo ""
            echo "Testing all accounts..."
            python3 << 'EOF'
from server.managers.account_manager import AccountManager
account_mgr = AccountManager()
result = account_mgr.test_all_accounts()
print(f"\nResults: {result['successful']}/{result['total']} successful")
for acc in result.get('accounts', []):
    status_icon = "?" if acc['status'] == 'connected' else "?"
    print(f"{status_icon} {acc['email']}: {acc['status']}")
EOF
            ;;
        8)
            echo ""
            echo "Setup complete!"
            exit 0
            ;;
        *)
            echo "Invalid choice"
            ;;
    esac
done