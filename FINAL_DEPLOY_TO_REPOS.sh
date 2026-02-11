#!/bin/bash
# FINAL_DEPLOY_TO_REPOS.sh - Creates missing files and pushes to GitLab + GitHub

set -e  # Exit on any error

cd /home/cody/cody-v3/executive-assistant

echo "+------------------------------------------------------------+"
echo "¦          FINAL DEPLOYMENT - CREATING FILES & PUSHING       ¦"
echo "+------------------------------------------------------------+"
echo ""

# ============================================================
# STEP 1: Create start_server.sh
# ============================================================
echo "?? Step 1/5: Creating start_server.sh..."

cat > start_server.sh << 'STARTEOF'
#!/bin/bash
# Start Executive Assistant server

cd "$(dirname "$0")"

echo "+------------------------------------------------------------+"
echo "¦          EXECUTIVE ASSISTANT - STARTING SERVER             ¦"
echo "+------------------------------------------------------------+"
echo ""

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "?? Starting Ollama service..."
    ollama serve &
    sleep 3
fi

echo "? Ollama is running"
echo ""
echo "?? Starting FastAPI server..."
echo "   Access at: http://localhost:8000"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Start server
python3 -m uvicorn server.app:app --host 127.0.0.1 --port 8000
STARTEOF

chmod +x start_server.sh
echo "? start_server.sh created"

# ============================================================
# STEP 2: Create complete README.md
# ============================================================
echo ""
echo "?? Step 2/5: Creating README.md..."

cat > README.md << 'READMEEOF'
# ?? Executive Assistant - Your Personal AI Email & Productivity Assistant

> **Built with ?? for Family and Friends** - A production-ready AI assistant that manages your email, calendar, contacts, and creates documents for you.

---

## ?? What Does It Do?

Your Executive Assistant is like having a personal secretary on your Mac that:

- ? **Cleans Your Email** - Automatically finds and removes spam (saved me from losing 11GB of emails!)
- ? **Manages Multiple Email Accounts** - Yahoo, Gmail, Hotmail, Comcast, iCloud all in one place
- ? **Schedules Meetings** - Just say "Schedule meeting with John next Thursday at 2pm" and it's done
- ? **Drafts Emails for You** - AI writes emails in YOUR writing style
- ? **Organizes Contacts** - Never lose a phone number or email again
- ? **Creates Documents** - Makes PowerPoint presentations, memos, and drawings
- ? **Learns Your Priorities** - Gets smarter over time about what's important to you
- ? **Works Offline** - AI runs on YOUR Mac, not in the cloud

---

## ??? Requirements

- **Mac with Apple Silicon** (M1, M2, M3, or M4 chip)
- **macOS Monterey (12.0) or newer**
- **6GB free disk space** (for AI model and app)
- **Internet connection** (for initial setup and email access)

---

## ?? Quick Start (3 Steps)

### Step 1: Install Prerequisites

Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)

```bash
# Install Homebrew (Mac's package manager)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required tools
brew install python@3.11 ollama git