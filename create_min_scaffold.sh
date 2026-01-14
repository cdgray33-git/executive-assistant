
mkdir -p "
R
O
O
T
D
I
R
/
s
e
r
v
e
r
/
l
l
m
"
"
ROOT_DIR/server/connectors" "
R
O
O
T
D
I
R
/
s
e
r
v
e
r
/
u
t
i
l
s
"
"
ROOT_DIR/ui/src" "$ROOT_DIR/docs"

.gitattributes
cat > "$ROOT_DIR/.gitattributes" <<'GATTR'

text=auto *.sh text eol=lf *.py text eol=lf .js text eol=lf .json text eol=lf ui/ text eol=lf server/ text eol=lf GATTR
.gitignore
cat > "$ROOT_DIR/.gitignore" <<'GIGNO' venv/ node_modules/ .DS_Store config.env data/ updates/ backups/ logs/ exports/ *.pkg *.tar.gz .vscode/ GIGNO

README
cat > "$ROOT_DIR/README.md" <<'RMD'

Executive Assistant (minimal scaffold)
This repo contains placeholder files for the Executive Assistant project. Run install_mac_assistant.sh on macOS after cloning. RMD

Minimal server files
cat > "$ROOT_DIR/server/requirements.txt" <<'REQ' fastapi uvicorn[standard] requests REQ

cat > "$ROOT_DIR/server/app.py" <<'PY' from fastapi import FastAPI app = FastAPI() @app.get("/api/status") async def status(): return {"status":"ok"} PY

cat > "$ROOT_DIR/server/llm/ollama_adapter.py" <<'OAD' import subprocess, os OLLAMA_CLI = os.environ.get("OLLAMA_BIN", "ollama") class OllamaAdapter: def ping(self): try: subprocess.run([OLLAMA_CLI, "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True) return True except Exception: return False OAD

cat > "$ROOT_DIR/server/connectors/imap_connector.py" <<'IMAP'

placeholder
def preview_messages(*a, **k): return [] def execute_move_to_trash(*a, **k): return {"moved_count":0} IMAP

Minimal update manager and utils
cat > "$ROOT_DIR/server/update_manager.py" <<'UM' from pathlib import Path APP_DIR = Path.home() / "ExecutiveAssistant" def list_available_updates(): up = APP_DIR / "updates" if not up.exists(): return [] return [p.name for p in up.glob("*.tar.gz")] def list_backups(): b = APP_DIR / "backups" if not b.exists(): return [] return [p.name for p in b.iterdir() if p.is_dir()] UM

cat > "$ROOT_DIR/server/security.py" <<'SEC' import os def require_api_key(x_api_key: str): expected = os.environ.get("API_KEY") if not expected: cfg = os.path.expanduser("~/ExecutiveAssistant/config.env") if os.path.exists(cfg): with open(cfg) as f: for line in f: if line.startswith("API_KEY"): _, v = line.split("=",1); expected = v.strip().strip('"') if not expected or x_api_key != expected: raise PermissionError("Invalid API key") SEC

cat > "$ROOT_DIR/server/utils/pptx_generator.py" <<'PPTX' from pptx import Presentation def generate_pptx(out_path, slides_text): prs = Presentation(); prs.save(out_path) PPTX

Minimal UI
cat > "$ROOT_DIR/ui/index.html" <<'UHTML'

<!doctype html><html><head><meta charset="utf-8"/><title>Executive Assistant</title></head> <body><div id="root"></div><script type="module" src="./src/App.js"></script></body></html> UHTML
cat > "$ROOT_DIR/ui/src/App.js" <<'UJS' import React from "react"; import { createRoot } from "react-dom/client"; function App(){ return <div style={{padding:20}}>Executive Assistant (UI placeholder)</div>; } createRoot(document.getElementById("root")).render(<App />); UJS

Installer placeholders
cat > "$ROOT_DIR/install_mac_assistant.sh" <<'INST' #!/usr/bin/env bash set -e mkdir -p "
H
O
M
E
/
E
x
e
c
u
t
i
v
e
A
s
s
i
s
t
a
n
t
/
u
p
d
a
t
e
s
"
"
HOME/ExecutiveAssistant/backups" "$HOME/ExecutiveAssistant/logs" cat > "$HOME/ExecutiveAssistant/config.env" <<CFG APP_DIR=$HOME/ExecutiveAssistant API_KEY="change_me_local_api_key_$(date +%s)" CFG echo "Created ~/ExecutiveAssistant with config.env" INST

cat > "$ROOT_DIR/build_pkg.sh" <<'BPKG' #!/usr/bin/env bash echo "build_pkg.sh placeholder" BPKG

cat > "$ROOT_DIR/sign_and_notarize.sh" <<'SIGN' #!/usr/bin/env bash echo "sign_and_notarize.sh placeholder" SIGN

chmod +x "
R
O
O
T
D
I
R
/
i
n
s
t
a
l
l
m
a
c
a
s
s
i
s
t
a
n
t
.
s
h
"
"
ROOT_DIR/build_pkg.sh" "
R
O
O
T
D
I
R
/
s
i
g
n
a
n
d
n
o
t
a
r
i
z
e
.
s
h
"
"
ROOT_DIR/create_min_scaffold.sh" || true echo "Minimal scaffold created." SCRIPT
exit
