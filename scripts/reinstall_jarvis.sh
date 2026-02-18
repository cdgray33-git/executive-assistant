#!/bin/bash
# Reinstall Jarvis Executive Assistant from scratch

INSTALL_DIR="$HOME/executive-assistant"
REPO_URL="https://github.com/cdgray33-git/executive-assistant.git"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          JARVIS REINSTALL - FRESH INSTALLATION             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Stop server if running
echo "🛑 Stopping existing server..."
pkill -f "uvicorn.*server.app:app" 2>/dev/null
pkill -f "python.*server/app.py" 2>/dev/null
sleep 2
echo "✅ Server stopped"
echo ""

# Delete old installation
if [ -d "$INSTALL_DIR" ]; then
    echo "🗑️  Removing old installation..."
    rm -rf "$INSTALL_DIR"
    echo "✅ Old installation removed"
    echo ""
fi

# Clone fresh from GitHub
echo "📥 Cloning fresh repository..."
cd "$HOME"
git clone "$REPO_URL"

if [ $? -ne 0 ]; then
    echo "❌ Git clone failed!"
    exit 1
fi

echo "✅ Repository cloned"
echo ""

# Run installer
cd "$INSTALL_DIR"

if [ ! -f "install_mac_assistant.sh" ]; then
    echo "❌ Installer script not found!"
    exit 1
fi

echo "🔧 Running installation script..."
./install_mac_assistant.sh

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          JARVIS REINSTALL COMPLETE                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Use 'Start Jarvis' icon to launch the assistant"
