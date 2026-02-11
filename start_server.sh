#!/bin/bash
# Start Executive Assistant

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          EXECUTIVE ASSISTANT - STARTING                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Activate virtual environment
source ~/.executive-assistant-env/bin/activate

# Start Ollama
if ! pgrep -x "ollama" > /dev/null; then
    echo "🤖 Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
fi

echo "✅ Ollama running"
echo ""
echo "🚀 Starting server at http://localhost:8000"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Run server
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
