# Quick Start Guide - Using Email Features

## Problem: "Method Not Allowed" Error

If you're seeing `{"detail":"Method Not Allowed"}` when trying to access emails, this guide will help you fix it.

## Solution

The issue has been fixed in the latest code. You need to update your installation.

### Step 1: Update Your Installation

```bash
cd ~/executive-assistant
git pull origin copilot/enhance-email-management-automation
~/executive-assistant/scripts/run_server.sh
```

Or restart the launchd service:
```bash
launchctl unload ~/Library/LaunchAgents/com.executiveassistant.server.plist
launchctl load ~/Library/LaunchAgents/com.executiveassistant.server.plist
```

### Step 2: Add Email Account (If Not Done)

The installation script should have prompted you for email credentials. If it didn't, or if you skipped it, add your email account now:

#### Option A: Using the Web Interface

1. Open http://127.0.0.1:8001
2. Look for email account settings
3. Add your email credentials

#### Option B: Using Python

```bash
cd ~/executive-assistant/server
source ~/.virtualenvs/executive-assistant/bin/activate
python3 << 'EOF'
import sys
sys.path.insert(0, '..')
import asyncio
import assistant_functions

async def add_account():
    result = await assistant_functions.add_email_account(
        account_id="my_account",
        imap_host="imap.mail.yahoo.com",  # or your provider
        imap_port=993,
        smtp_host="smtp.mail.yahoo.com",  # or your provider
        smtp_port=465,
        username="your_email@yahoo.com",
        password="your_app_password",
        use_ssl=True
    )
    print(result)

asyncio.run(add_account())
EOF
```

### Step 3: Test the Chat Interface

Now you can use natural language to interact with your emails:

```bash
curl -X POST http://127.0.0.1:8001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"show me my last 3 emails"}'
```

Or use the web interface at http://127.0.0.1:8001

## Supported Email Queries

The chat interface now understands:
- "show me my last 3 emails"
- "what are my last 5 emails"
- "fetch my unread emails"
- "get my recent messages"

## Using Email Functions Directly

You can also call email functions directly via the API:

### Fetch Unread Emails
```bash
curl -X POST http://127.0.0.1:8001/api/function_call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fetch_unread_emails",
    "arguments": {
      "account_id": "my_account",
      "max_messages": 5
    }
  }'
```

### Bulk Delete Old Emails
```bash
curl -X POST http://127.0.0.1:8001/api/email/bulk_cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "my_account",
    "criteria": {
      "older_than_days": 365,
      "folder": "INBOX"
    },
    "dry_run": true
  }'
```

### Categorize Emails
```bash
curl -X POST http://127.0.0.1:8001/api/email/categorize \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "my_account",
    "max_messages": 100,
    "dry_run": true
  }'
```

## Email Account Setup Details

### For Yahoo Mail:
1. Go to Yahoo Account Security settings
2. Generate an "App Password"
3. Use that app password (not your regular password) in the setup

Settings:
- IMAP: `imap.mail.yahoo.com:993`
- SMTP: `smtp.mail.yahoo.com:465`
- SSL: Yes

### For Gmail:
1. Enable 2-factor authentication
2. Generate an "App Password"
3. Use that app password in the setup

Settings:
- IMAP: `imap.gmail.com:993`
- SMTP: `smtp.gmail.com:587`
- SSL: Yes

### For Outlook/Hotmail:
Settings:
- IMAP: `outlook.office365.com:993`
- SMTP: `smtp.office365.com:587`
- SSL: Yes

## Checking Your Configuration

To verify your email accounts are set up:

```bash
cd ~/executive-assistant/server
source ~/.virtualenvs/executive-assistant/bin/activate
python3 << 'EOF'
import sys
sys.path.insert(0, '..')
import asyncio
import assistant_functions

async def check():
    result = await assistant_functions.list_email_accounts()
    print(f"Configured accounts: {result}")

asyncio.run(check())
EOF
```

## Troubleshooting

### Still Getting "Method Not Allowed"?

1. Make sure you pulled the latest code
2. Restart the server
3. Check server logs: `tail -f ~/ExecutiveAssistant/logs/server_stderr.log`

### "No email accounts configured" Message?

Run the account setup steps above.

### IMAP Connection Errors?

- Double-check your email provider settings
- Make sure you're using an app password (not your regular password)
- Verify SSL port numbers (993 for IMAP, 465 for SMTP)
- Check if your email provider requires special app passwords

### Still Having Issues?

Check the logs:
```bash
# Server logs
tail -f ~/ExecutiveAssistant/logs/server_stderr.log

# Launchd logs  
tail -f ~/ExecutiveAssistant/logs/launchd_stderr.log
```

Email accounts are stored in:
```bash
~/executive-assistant/data/email_accounts.json
```

You can manually verify the file exists and has the correct permissions (should be 600).
