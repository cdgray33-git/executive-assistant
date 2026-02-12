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
echo "📦 Step 2/5: Installing Python 3.13 and Ollama..."
brew install python@3.13 ollama git 2>/dev/null || true

echo ""
echo "📦 Step 3/5: Creating Python virtual environment..."
/opt/homebrew/bin/python3.13 -m venv ~/.executive-assistant-env
source ~/.executive-assistant-env/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt
echo "✅ Python packages installed"

echo ""
echo ""
echo "🎨 Step 4/6: Building React UI..."
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

echo "🤖 Step 4/5: Starting Ollama and downloading AI model..."
pkill ollama 2>/dev/null || true
sleep 2
ollama serve > /dev/null 2>&1 &
sleep 5
echo "   Downloading AI model (~4GB, may take 5-10 minutes)..."
ollama pull qwen2.5:7b-instruct

echo ""
echo "📁 Step 5/5: Creating data directories..."
mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence,logs}

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ INSTALLATION COMPLETE! ✅                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "To start:"
echo "  ./start_server.sh"
echo ""
echo "Then open: http://localhost:8000"
echo ""
