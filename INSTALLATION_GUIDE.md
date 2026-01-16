# Executive Assistant - Installation Guide

## Quick Installation on macOS

### Option 1: Automated One-Line Install (Recommended)

The easiest way to install on your MacBook:

1. Open **Terminal** (Applications → Utilities → Terminal)

2. Copy and paste this command:
```bash
curl -fsSL https://raw.githubusercontent.com/cdgray33-git/executive-assistant/copilot/enhance-email-management-automation/install_executive_assistant_mac.sh | bash
```

3. Follow the prompts. The installer will:
   - Install Homebrew (if needed)
   - Install Ollama and Python
   - Download and set up the Executive Assistant
   - Pull AI models (llama3.2:3b and mistral:7b)
   - Configure email accounts (optional)
   - Start the server automatically
   - Open the web interface in your browser

### Option 2: Manual Download and Install

If you prefer to review the script first:

1. Download the installer:
```bash
cd ~/Downloads
curl -fsSL -o install_executive_assistant_mac.sh https://raw.githubusercontent.com/cdgray33-git/executive-assistant/copilot/enhance-email-management-automation/install_executive_assistant_mac.sh
```

2. Make it executable:
```bash
chmod +x install_executive_assistant_mac.sh
```

3. Run the installer:
```bash
./install_executive_assistant_mac.sh
```

## System Requirements

- **macOS**: 10.15 (Catalina) or later
- **Disk Space**: At least 10GB free
- **RAM**: 8GB minimum, 16GB recommended
- **Internet**: Required for initial installation and AI model downloads

## What Gets Installed

- **Location**: `~/executive-assistant/`
- **Data Directory**: `~/executive-assistant/data/`
- **Logs**: `~/ExecutiveAssistant/logs/`
- **Server Port**: http://127.0.0.1:8001
- **Auto-start**: Configured to run at login via launchd

## After Installation

### Access the Assistant

Once installed, open your web browser and go to:
```
http://127.0.0.1:8001
```

### Using Email Management Features

1. Add an email account from the web interface
2. Use these features:
   - **Fetch unread emails**: See your latest messages
   - **Bulk cleanup**: Delete old emails by criteria
   - **Auto-categorize**: Sort emails into folders
   - **Spam filter**: Detect and remove spam

### Using Document Generation Features

Via the web interface or API:

**Generate PowerPoint Presentations:**
```python
POST /api/generate_presentation
{
  "title": "My Presentation",
  "slides": [
    {"type": "title", "title": "Main Title", "subtitle": "Subtitle"},
    {"type": "bullets", "title": "Key Points", "bullets": ["Point 1", "Point 2"]}
  ]
}
```

**Create Briefings:**
```python
POST /api/create_briefing
{
  "title": "Strategic Plan",
  "summary": "Executive summary...",
  "key_points": ["Point 1", "Point 2"],
  "action_items": ["Action 1", "Action 2"],
  "format": "docx"
}
```

**Generate Documents (Letters, Memos):**
```python
POST /api/write_document
{
  "doc_type": "memo",
  "title": "Company Update",
  "content": "Memo content...",
  "format": "docx"
}
```

## Sharing with Family

### Method 1: Share Installation Script (Recommended)

Send your family members this installation guide and the one-line install command. Each person installs their own copy on their Mac.

**Pros:**
- Each person has their own private instance
- No shared credentials or data
- Easy to update and maintain
- Secure (runs locally on each Mac)

### Method 2: Package as Installer (.pkg)

For advanced users - you can create a macOS package:

1. After successful installation, create a package:
```bash
cd ~/executive-assistant
./build_pkg.sh
```

2. This creates a `.pkg` file you can share
3. Recipients double-click to install

**Note:** Recipients still need to:
- Have macOS and sufficient disk space
- Allow the app in System Preferences → Security & Privacy
- Configure their own email accounts

### Method 3: Remote Access (Not Recommended for Families)

You could set up remote access to your Mac, but this is:
- **Less secure** (shared access to your computer)
- **More complex** to configure (requires port forwarding, VPN, etc.)
- **Not recommended** for family use

## Email Configuration

During or after installation, you can add email accounts:

### For Yahoo Mail:
1. Create an app password in Yahoo Mail settings
2. Add account with these settings:
   - IMAP: `imap.mail.yahoo.com:993`
   - SMTP: `smtp.mail.yahoo.com:465`
   - Username: your Yahoo email
   - Password: your app password (not your regular password)

### For Gmail:
1. Enable "Less secure app access" or create an app password
2. Add account with:
   - IMAP: `imap.gmail.com:993`
   - SMTP: `smtp.gmail.com:587`

### For Other Providers:
Check your email provider's IMAP/SMTP settings documentation.

## Generated Files Location

All generated documents are saved to:
- **PowerPoint**: `~/executive-assistant/data/outputs/presentations/`
- **Word Documents**: `~/executive-assistant/data/outputs/documents/`
- **PDFs**: `~/executive-assistant/data/outputs/pdfs/`

## Troubleshooting

### Server Won't Start
```bash
# Check logs
tail -f ~/ExecutiveAssistant/logs/server_stderr.log

# Restart manually
~/executive-assistant/scripts/run_server.sh
```

### Port Already in Use
If port 8001 is taken, edit the config:
```bash
nano ~/executive-assistant/config.env
# Change PORT=8001 to PORT=8002 (or another port)
```

### Ollama Not Running
```bash
# Check if Ollama is running
curl http://127.0.0.1:11434/api/health

# Start Ollama manually
ollama serve --watch &
```

### Permission Denied
```bash
# Fix permissions
chmod +x ~/executive-assistant/scripts/run_server.sh
```

## Uninstalling

To completely remove the Executive Assistant:

```bash
# Stop the service
launchctl unload ~/Library/LaunchAgents/com.executiveassistant.server.plist

# Remove files
rm -rf ~/executive-assistant
rm -rf ~/.virtualenvs/executive-assistant
rm -rf ~/ExecutiveAssistant
rm ~/Library/LaunchAgents/com.executiveassistant.server.plist

# Optional: Remove Ollama and models (if not used elsewhere)
brew uninstall ollama
```

## Getting Help

- Check logs: `~/ExecutiveAssistant/logs/`
- Review installation output for errors
- Ensure you have sufficient disk space and RAM
- Verify network connectivity during installation

## Security Notes

- All data is stored locally on your Mac
- Email credentials are stored in `~/executive-assistant/data/email_accounts.json` (permissions: 600)
- The server only listens on localhost (127.0.0.1) - not accessible from other computers
- No data is sent to external servers except for AI model downloads during installation

## Updates

To update to the latest version:
```bash
cd ~/executive-assistant
git pull origin main
~/executive-assistant/scripts/run_server.sh
```

Or re-run the installation script (it will update existing installation).
