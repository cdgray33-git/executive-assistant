#!/usr/bin/env bash
# Wrapper to start the uvicorn FastAPI server using a Homebrew Python venv.
# This script is referenced by the launchd plist.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$HOME/.virtualenvs/executive-assistant"
PYTHON_BIN="$VENV_DIR/bin/python"
UVICORN_CMD="$VENV_DIR/bin/uvicorn"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Virtualenv not found at $VENV_DIR"
  echo "Create it with: python3 -m venv $VENV_DIR && $VENV_DIR/bin/pip install -r $REPO_DIR/server/requirements.txt"
  exit 1
fi

cd "$REPO_DIR"

export PYTHONPATH="$REPO_DIR:$PYTHONPATH"
exec "$UVICORN_CMD" server.app:app --host 127.0.0.1 --port 8001 --workers 1
