# Native macOS Installation Checklist (Homebrew Ollama, Homebrew Python, per-user launchd)

This checklist installs and configures the Executive Assistant server natively on an Apple Silicon Mac (M1/M2/M3).
It expects you want Ollama native (Homebrew), one 3B model and one 7B model available, and a per-user launchd agent.

Run these commands in Terminal. Read each section before running.

1) Install Homebrew (if you don't have it)
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   # Follow any post-install instructions to add brew to your PATH (usually eval "$(/opt/homebrew/bin/brew shellenv)")

2) Install Ollama (native)
   brew install ollama

   # Start Ollama daemon (if needed)
   ollama serve --watch &

   # Verify Ollama HTTP API
   curl -fsS http://127.0.0.1:11434/api/health || echo "Ollama health check failed"

   # List models available in Ollama
   ollama list

   # Pull recommended small/quantized models (choose appropriate model names)
   # Example (replace <model-name>):
   # ollama pull <3B-model-name>
   # ollama pull <7B-model-name>
   #
   # Note: consult `ollama models` or the Ollama catalog for exact model names suitable for CPU/MPS.

3) Install Homebrew Python and create a venv
   brew install python
   python3 -m venv $HOME/.virtualenvs/executive-assistant
   $HOME/.virtualenvs/executive-assistant/bin/pip install --upgrade pip
   $HOME/.virtualenvs/executive-assistant/bin/pip install -r /path/to/your/repo/server/requirements.txt

4) Store the API key in macOS Keychain (recommended)
   # Option A: Use the Python keyring module
   $HOME/.virtualenvs/executive-assistant/bin/python - <<PY
   import keyring
   keyring.set_password("ExecutiveAssistant", "api_key", "replace_with_a_strong_key_here")
   print("Stored API key in macOS Keychain")
   PY

   # Option B: fallback: create ~/ExecutiveAssistant/config.env with API_KEY=...
   mkdir -p "$HOME/ExecutiveAssistant"
   cat > "$HOME/ExecutiveAssistant/config.env" <<CFG
   API_KEY="replace_with_a_strong_key_here"
   CFG

   # Or set environment variable (session only):
   export API_KEY="replace_with_a_strong_key_here"

5) Prepare logs and directories
   mkdir -p "$HOME/ExecutiveAssistant/logs"

6) Copy run_server.sh and make executable
   # from repo root
   chmod +x scripts/run_server.sh

7) Install per-user launchd agent
   mkdir -p ~/Library/LaunchAgents
   cp launchd/com.executiveassistant.server.plist ~/Library/LaunchAgents/

   # Load the agent
   launchctl unload ~/Library/LaunchAgents/com.executiveassistant.server.plist 2>/dev/null || true
   launchctl load ~/Library/LaunchAgents/com.executiveassistant.server.plist

   # Check status
   launchctl list | grep -i executiveassistant || true

   # Logs:
   tail -f "$HOME/ExecutiveAssistant/logs/launchd_stdout.log"

8) Test the server
   curl -fsS http://127.0.0.1:8001/health
   # If you set an API key, include header X-API-Key: <your_key> when calling /api/models or /api/function_call

9) Ollama model memory guidance (3B vs 7B)
   - 3B models: generally safe on Apple Silicon with ~16GB, fast enough for interactive use.
   - 7B models: may run but require quantized ggml/4-bit variants or MPS-optimized kernels. Expect slower responses and higher memory usage.
   - Recommendation: test with the 3B first. If you need the 7B, use a quantized variant and monitor memory. If performance is poor, offload heavy model inference to a remote GPU host.

