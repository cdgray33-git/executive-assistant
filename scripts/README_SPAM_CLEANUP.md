# Direct Spam Cleanup Script

This script provides a simple, direct way to move spam emails to your Spam folder **without using the LLM**. Perfect for bulk cleanup operations.

## Quick Start

```bash
# Move spam from last 100 emails
cd ~/executive-assistant/scripts
python3 move_spam.py

# Scan and move spam from last 300 emails (bulk cleanup)
python3 move_spam.py --max 300

# Preview what would be moved (dry run)
python3 move_spam.py --max 150 --dry-run
```

## Features

- **No LLM required** - Direct IMAP operations
- **Bulk operations** - Handle 100-300+ emails at once
- **Safe by default** - Preview mode available with --dry-run
- **Smart spam detection** - Uses multiple heuristics:
  - X-Spam-Score headers
  - X-Spam-Status headers
  - Common spam keywords
  - Suspicious patterns
- **Automatic folder creation** - Creates Spam folder if needed
- **Move, not delete** - Spam goes to Spam folder for review

## Usage

```bash
python3 move_spam.py [options]
```

### Options

- `--max NUM` - Maximum number of emails to scan (default: 100)
  - For bulk cleanup, use 150-300
  - Example: `--max 300`

- `--dry-run` - Preview what would be moved without actually moving
  - Safe way to test before running
  - Example: `--dry-run`

- `--account ID` - Email account ID (default: first account)
  - Example: `--account primary`

## Examples

### Basic Cleanup (100 emails)
```bash
python3 move_spam.py
```

### Bulk Cleanup (300 emails)
```bash
python3 move_spam.py --max 300
```

### Preview Mode (see what would be moved)
```bash
python3 move_spam.py --max 150 --dry-run
```

### Use Specific Account
```bash
python3 move_spam.py --account work --max 200
```

## Output Example

```
============================================================
SPAM MOVER - Direct Email Cleanup
============================================================
Account: primary
Scanning: Last 300 emails
Mode: LIVE (will move emails)
============================================================

✓ Moved 23 spam email(s) to Spam folder

Spam emails found: 23
Successfully moved: 23

Sample of spam emails:
------------------------------------------------------------
1. From: "Temu"
   Subject: Dinosaur toy - Now Priced at 1 CENT!

2. From: lottery@example.com
   Subject: You've won $1,000,000!

============================================================
Spam emails have been moved to the 'Spam' folder.
Check your email client to verify.
============================================================
```

## Troubleshooting

### No email accounts configured
```
ERROR: No email accounts configured.
```
**Solution:** Configure an email account through the web UI first.

### Account not found
```
ERROR: Account 'work' not found.
Available accounts: primary
```
**Solution:** Use the correct account ID or omit --account to use the default.

### Connection errors
If you get IMAP connection errors, check:
1. Email credentials are correct
2. IMAP is enabled in your email settings
3. App-specific password is being used (for Gmail, Yahoo, etc.)

## How It Works

1. **Connects to IMAP** - Uses your configured email account
2. **Scans recent emails** - Checks the last N emails in INBOX
3. **Detects spam** - Uses multiple detection methods
4. **Creates Spam folder** - If it doesn't exist
5. **Moves emails** - Copies to Spam folder, removes from INBOX
6. **Reports results** - Shows what was moved

## Location

The script is located at:
```
~/executive-assistant/scripts/move_spam.py
```

## Logs

All operations are logged to:
```
~/ExecutiveAssistant/logs/assistant.log
```

View logs with:
```bash
tail -f ~/ExecutiveAssistant/logs/assistant.log
```

## Integration with Main App

You can also use this functionality through the web interface:
- Natural language: "move spam to spam folder"
- Or use the direct API: `/api/function_call` with function `move_spam_to_folder`

## Safety Features

- **Preview mode** - Test with --dry-run first
- **Move, not delete** - Emails go to Spam folder, not permanently deleted
- **Logging** - All operations logged for audit trail
- **Error handling** - Graceful failure with helpful error messages

## Performance

- **Fast** - Processes ~100 emails in 5-10 seconds
- **Efficient** - Uses IMAP UID commands for reliability
- **Scalable** - Can handle 300+ emails in a single run

## Recommendations

1. **Start with preview**: `python3 move_spam.py --max 50 --dry-run`
2. **Test small batch**: `python3 move_spam.py --max 50`
3. **Scale up**: `python3 move_spam.py --max 300`
4. **Regular cleanup**: Run weekly with `--max 150`
