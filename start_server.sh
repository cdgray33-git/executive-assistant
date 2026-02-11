#!/bin/bash
cd "$(dirname "$0")"
echo "🚀 Starting Executive Assistant..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 3
fi
python3 -m uvicorn server.app:app --host 127.0.0.1 --port 8000
