#!/usr/bin/env bash
# create_scaffold.sh
# Creates the Executive Assistant repo scaffold files and directories.
# Run this in the root of your local cloned repo folder (or where you want the project created).
#
# Usage (Git Bash / macOS / WSL):
#   1) Save this file: create_scaffold.sh
#   2) Make executable: chmod +x create_scaffold.sh
#   3) Run: ./create_scaffold.sh
#
set -e
ROOT_DIR="$(pwd)"
echo "Creating scaffold in: $ROOT_DIR"

# Directories
mkdir -p "$ROOT_DIR/server/llm"
mkdir -p "$ROOT_DIR/server/connectors"
mkdir -p "$ROOT_DIR/server/utils"
mkdir -p "$ROOT_DIR/ui/src"
mkdir -p "$ROOT_DIR/docs"

# .gitattributes
cat > "$ROOT_DIR/.gitattributes" <<'EOF'
# Ensure consistent line endings (LF) across platforms
* text=auto

# Force LF for shell scripts and python/js files
*.sh text eol=lf
*.py text eol=lf
*.js text eol=lf
*.json text eol=lf
ui/* text eol=lf
server/* text eol=lf
EOF

# .gitignore
cat > "$ROOT_DIR/.gitignore" <<'EOF'
# Python
venv/
*.pyc
__pycache__/

# Node
node_modules/
.dist/
.cache/

# macOS
.DS_Store

# Local app data & secrets (do NOT commit)
config.env
data/
updates/
backups/
logs/
exports/

# Package artifacts
*.pkg
*.tar.gz

# Editor files
*.swp
*.swo
.idea/
.vscode/
EOF

# README.md
cat > "$ROOT_DIR/README.md" <<'EOF'
# Executive Assistant (Ollama-based) - repo scaffold

Overview
--------
This repository contains a per-user Executive Assistant scaffold for macOS (M1/M2/M3) that uses Ollama (native) for local LLM inference, a FastAPI orchestrator, and a lightweight browser UI.

Structure
---------
- install_mac_assistant.sh - per-user installer script
- build_pkg.sh - helper to create unsigned .pkg installer
- sign_and_notarize.sh - template for signing & notarizing (requires Apple Developer account)
- server/ - backend FastAPI app and connectors
- ui/ - React UI skeleton

Important
---------
- Do NOT commit config.env, credentials, or tokens. Those files are ignored by .gitignore.
- Each user will run the installer on their Mac to set up Ollama, Python venv, and the per-user service.
- Updates are manual. Admins create tar.gz archives and place them into ~/ExecutiveAssistant/updates on the user's machine, then apply via Admin UI.

Quick install on a Mac (after cloning)
1. Open Terminal on the Mac:
