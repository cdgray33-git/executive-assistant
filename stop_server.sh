#!/bin/bash
# Stop Executive Assistant gracefully

echo "🛑 Stopping Executive Assistant..."

# Stop server
pkill -f "uvicorn.*server.app:app"
sleep 1

# Stop Ollama (optional - you decide)
# pkill -f ollama

echo "✅ Server stopped"
