#!/usr/bin/env bash
set -e
mkdir -p "$HOME/ExecutiveAssistant/updates" "$HOME/ExecutiveAssistant/backups" "$HOME/ExecutiveAssistant/logs"
cat > "$HOME/ExecutiveAssistant/config.env" <<CFG
APP_DIR=$HOME/ExecutiveAssistant
API_KEY="change_me_local_api_key_$(date +%s)"
CFG
echo "Created ~/ExecutiveAssistant with config.env"
