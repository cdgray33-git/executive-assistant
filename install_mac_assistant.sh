#!/usr/bin/env bash
# Complete one-shot installation for Mac

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       EXECUTIVE ASSISTANT - MAC INSTALLATION               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Mac
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only"
    exit 1
fi

# Check for Homebrew
echo "📦 Step 1/5: Checking for Homebrew..."
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo "✅ Homebrew installed"

# Install dependencies
echo ""
echo "📦 Step 2/5: Installing Python and Ollama..."
brew install python@3.11 ollama git

# Install Python packages
echo ""
echo "📦 Step 3/5: Installing Python packages..."
pip3 install -r server/requirements.txt

# Start Ollama
echo ""
echo "🤖 Step 4/5: Starting Ollama and downloading AI model..."
brew services start ollama
sleep 3

# Download AI model
echo "   (This downloads ~4GB, may take several minutes...)"
ollama pull qwen2.5:7b-instruct

# Create data directories
echo ""
echo "📁 Step 5/5: Creating data directories..."
mkdir -p ~/Library/Application\ Support/ExecutiveAssistant/data/{calendar,contacts,notes,documents,templates,config,intelligence,logs}

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✅ INSTALLATION COMPLETE! ✅                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Add your email accounts: ./setup_accounts.sh"
echo "  2. Start the assistant: ./start_server.sh"
echo "  3. Open browser to: http://localhost:8000"
echo ""
