#!/usr/bin/env bash
# Executive Assistant - Production Installation for Mac M1/M2/M3/M4
# Uses Python 3.13 (3.14 has package compatibility issues)

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       EXECUTIVE ASSISTANT - MAC INSTALLATION               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only"
    exit 1
fi

echo "📦 Step 1/5: Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ -f /opt/homebrew/bin/brew ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi
echo "✅ Homebrew installed"

echo ""
echo "📦 Step 2/8: Installing Python 3.13 and Ollama..."
brew install python@3.13 ollama git postgresql@17 2>/dev/null || true

echo ""

echo ""
echo "🗄️  Step 3/8: Setting up PostgreSQL + pgvector..."
# Start PostgreSQL service
brew services start postgresql@17
sleep 3

# Install pgvector extension
rm -rf /tmp/pgvector
echo "   Downloading pgvector..."
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git /tmp/pgvector

cd /tmp/pgvector
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
make clean 2>/dev/null || true
make
make install
cd ~/executive-assistant

# Create database and user
echo "   Creating database..."
psql postgres -c "CREATE USER jarvis WITH PASSWORD 'jarvis_secure_2026';" 2>/dev/null || echo "   User already exists"
psql postgres -c "CREATE DATABASE jarvis_ea OWNER jarvis;" 2>/dev/null || echo "   Database already exists"
psql jarvis_ea -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Deploy schema
echo "   Deploying schema..."
psql -U jarvis -d jarvis_ea -f server/database/schema.sql

# Run database migrations
echo "   Running migrations..."
if [ -f "scripts/run_migration.sh" ]; then
    export DB_PASSWORD="jarvis_secure_2026"
    export DB_USER="jarvis"
    ./scripts/run_migration.sh 2>/dev/null || echo "   ⚠️  Migration encountered issues (may be normal on fresh install)"
fi

echo "✅ PostgreSQL + pgvector configured"
echo "📦 Step 4/8: Creating Python virtual environment..."
/opt/homebrew/bin/python3.13 -m venv ~/.executive-assistant-env
source ~/.executive-assistant-env/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt
echo "✅ Python packages installed"

echo ""
echo ""
echo "🎨 Step 5/8: Building React UI..."
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    brew install node
fi
echo "✅ Node.js installed"

cd ui-build
echo "   Installing UI dependencies..."
npm install --silent
echo "   Building production UI..."
npm run build
echo "   Deploying to server..."
rm -rf ../ui/dist/*
mkdir -p ../ui/dist
cp -r dist/* ../ui/dist/
cd ..
echo "✅ UI built and deployed"

echo "🤖 Step 6/8: Starting Ollama and downloading AI model..."
pkill ollama 2>/dev/null || true
sleep 2
ollama serve > /dev/null 2>&1 &
sleep 5
echo "   Downloading AI model (~4GB, may take 5-10 minutes)..."
ollama pull qwen2.5:7b-instruct

echo ""
echo "📁 Step 7/8: Creating data directories..."
mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence,logs}

echo ""

echo ""
echo "🖥️  Step 8/8: Creating desktop launcher..."
APP_NAME="Executive Assistant"
APP_DIR="$HOME/Desktop/$APP_NAME.app"

mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create launcher script
cat > "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHEOF'
#!/bin/bash
cd ~/executive-assistant
source ~/.executive-assistant-env/bin/activate

# Ensure PostgreSQL is running
brew services start postgresql@17 2>/dev/null

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

# Start server
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000 &
sleep 3

# Open browser
open http://localhost:8000

# Keep app running
wait
LAUNCHEOF

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# Create Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleName</key>
    <string>Executive Assistant</string>
    <key>CFBundleDisplayName</key>
    <string>Executive Assistant</string>
    <key>CFBundleIdentifier</key>
    <string>com.executiveassistant</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
PLISTEOF

echo "✅ Desktop launcher created at: $APP_DIR"

# Create Stop Server icon
STOP_APP_NAME="Stop Executive Assistant"
STOP_APP_DIR="$HOME/Desktop/$STOP_APP_NAME.app"

mkdir -p "$STOP_APP_DIR/Contents/MacOS"
mkdir -p "$STOP_APP_DIR/Contents/Resources"

cat > "$STOP_APP_DIR/Contents/MacOS/launcher" << 'STOPEOF'
#!/bin/bash

osascript -e 'display notification "Stopping Executive Assistant..." with title "Executive Assistant"'

# Stop server
pkill -f "uvicorn.*server.app:app"
sleep 1

# Stop Ollama (optional)
pkill -f ollama

osascript -e 'display notification "Server stopped successfully" with title "Executive Assistant"'
STOPEOF

chmod +x "$STOP_APP_DIR/Contents/MacOS/launcher"

cat > "$STOP_APP_DIR/Contents/Info.plist" << 'STOPPLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleName</key>
    <string>Stop Executive Assistant</string>
    <key>CFBundleDisplayName</key>
    <string>Stop Executive Assistant</string>
    <key>CFBundleIdentifier</key>
    <string>com.executiveassistant.stop</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
</dict>
</plist>
STOPPLIST

echo "✅ Stop icon created at: $STOP_APP_DIR"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ INSTALLATION COMPLETE! ✅                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "To start:"
echo "  ./start_server.sh"
echo ""
echo "Then open: http://localhost:8000"

echo "To start, either:"
echo "   1. Double-click 'Executive Assistant' on Desktop"
echo "   2. Run: ./start_server.sh"
echo ""
echo "🗄️  Database: jarvis_ea (PostgreSQL 17 + pgvector)"
echo "🤖 AI Model: qwen2.5:7b-instruct"
echo ""
