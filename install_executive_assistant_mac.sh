#!/usr/bin/env bash
set -euo pipefail

# install_executive_assistant_mac.sh
# All-in-one, non-Docker installer for Executive Assistant (macOS).
# Installs Homebrew (if needed), Ollama, Python venv, pulls models,
# creates a FastAPI + function backend, a browser UI, email credential prompt,
# configures a per-user launchd agent to run the server, and opens the browser.
#
# Usage:
#   1) Save this file as install_executive_assistant_mac.sh in ~/Downloads
#   2) In Terminal:
#      cd ~/Downloads
#      chmod +x install_executive_assistant_mac.sh
#      ./install_executive_assistant_mac.sh
#
# Optional environment variables:
#   FORCE_YES=yes        # accept prompts automatically (use carefully)
#   SKIP_MODEL_PULL=yes  # skip automatic ollama model pulls
#   YAHOO_EMAIL, YAHOO_APP_PASSWORD, YAHOO_IMAP_SERVER, YAHOO_IMAP_PORT, YAHOO_SMTP_SERVER, YAHOO_SMTP_PORT

# ------------ Configuration -------------
: "${REPO_ARCHIVE_URL:=https://github.com/cdgray33-git/executive-assistant/archive/refs/heads/copilot/enhance-email-management-automation.zip}"
REPO_DIR="$HOME/executive-assistant"
VENV_DIR="$HOME/.virtualenvs/executive-assistant"
LOG_DIR="$HOME/ExecutiveAssistant/logs"
DATA_DIR="$REPO_DIR/data"
SERVER_DIR="$REPO_DIR/server"
STATIC_DIR="$SERVER_DIR/static"
RUN_SH="$REPO_DIR/scripts/run_server.sh"
LAUNCH_PLIST_USER="$HOME/Library/LaunchAgents/com.executiveassistant.server.plist"
CONFIG_FILE="$REPO_DIR/config.env"
PORT=8001
OLLAMA_HTTP="http://127.0.0.1:11434"

# Models
MODEL_3B="${MODEL_3B:-llama3.2:3b}"  # Correct default model name for Llama 3.2 3B
MODEL_7B="${MODEL_7B:-mistral:7b}"  # Correct default model name for Mistral 7B

# Flags
FORCE_YES="${FORCE_YES:-no}"
SKIP_MODEL_PULL="${SKIP_MODEL_PULL:-no}"

# Retry settings for brew installs
RETRY_WAIT_SECONDS=3
MAX_RETRIES=3

# ------------ Helpers -------------
log()  { printf "\n[INFO] %s\n" "$*"; }
err()  { printf "\n[ERROR] %s\n" "$*" >&2; }
die()  { err "$*"; exit 1; }
check_cmd() { command -v "$1" >/dev/null 2>&1; }
available_disk_gb() { df -Pk "$HOME" | awk 'NR==2 {print int($4/1024/1024)}' 2>/dev/null || echo 0; }

confirm() {
  if [[ "$FORCE_YES" == "yes" ]]; then
    return 0
  fi
  read -r -p "$1 [y/N]: " a
  case "$a" in [yY]|[yY][eE][sS]) return 0 ;; *) return 1 ;; esac
}

try() { if ! "$@"; then return 1; fi; return 0; }

wait_for_http() {
  local url="$1"; local tries=0 max=${2:-120}
  until curl -fsS "$url" >/dev/null 2>&1; do
    sleep 1; tries=$((tries+1))
    if (( tries >= max )); then return 1; fi
  done
  return 0
}

ensure_dirs() {
  mkdir -p "$DATA_DIR/notes" "$DATA_DIR/calendar" "$DATA_DIR/contacts" \
           "$DATA_DIR/outputs/presentations" "$DATA_DIR/outputs/documents" "$DATA_DIR/outputs/pdfs" \
           "$LOG_DIR" "$SERVER_DIR" "$STATIC_DIR" "$REPO_DIR/scripts"
  log "Ensured data, output, server, static and log directories exist"
}

# ----------------- Begin -----------------
log "Executive Assistant - All-in-one installer (non-Docker)"

# 0) Basic pre-checks
if ! command -v curl >/dev/null 2>&1; then
  die "curl is required but not found. Install curl and re-run."
fi

log "Checking network access to GitHub..."
if ! curl -fsS --head https://raw.githubusercontent.com/ >/dev/null 2>&1; then
  die "No network access to GitHub RAW endpoints. Ensure the Mac is online."
fi

# Initial disk check
FREE_GB=$(available_disk_gb || echo 0)
log "Free disk space (GB): $FREE_GB"
if (( FREE_GB < 10 )); then
  err "Low free disk space (<10GB). Models and packages may fail to install."
  if ! confirm "Proceed anyway?"; then die "Aborted due to low disk space."; fi
fi

# 1) Download & install repository into $REPO_DIR (fresh copy)
log "Downloading repository archive and installing to $REPO_DIR..."
TMP_ZIP="/tmp/ea_main.zip"
TMP_EXTRACT="/tmp/ea_extract_$$"
rm -f "$TMP_ZIP" || true
rm -rf "$TMP_EXTRACT" || true
mkdir -p "$TMP_EXTRACT"
curl -fsSL -o "$TMP_ZIP" "$REPO_ARCHIVE_URL" || die "Failed to download repo archive."
# Extract to dedicated temp directory
unzip -oq "$TMP_ZIP" -d "$TMP_EXTRACT" || die "Failed to unzip repo archive."
# Find the extracted directory (GitHub creates executive-assistant-BRANCHNAME)
# Wait a moment for filesystem to sync
sleep 1
EXTRACTED_DIR=$(find "$TMP_EXTRACT" -maxdepth 1 -type d ! -path "$TMP_EXTRACT" 2>/dev/null | head -n1)
if [[ -z "$EXTRACTED_DIR" || ! -d "$EXTRACTED_DIR" ]]; then
  # Debug: list what was actually extracted
  log "Contents of extraction directory:"
  ls -la "$TMP_EXTRACT" 2>/dev/null || true
  log "Attempting to list subdirectories:"
  find "$TMP_EXTRACT" -maxdepth 2 -type d 2>/dev/null || true
  die "Unexpected archive layout after unzip. Could not find extracted directory."
fi
rm -rf "$REPO_DIR" || true
mv "$EXTRACTED_DIR" "$REPO_DIR" || die "Failed to move repo to $REPO_DIR"
rm -f "$TMP_ZIP"
rm -rf "$TMP_EXTRACT"
log "Repo installed to $REPO_DIR"

# Ensure directories (early)
ensure_dirs

# 2) Install Homebrew (if missing), Ollama, Python
log "Ensuring Homebrew, ollama, python3 are installed..."

# Re-check free disk space before heavy installs
FREE_GB=$(available_disk_gb || echo 0)
log "Re-checked free disk space before package installs: ${FREE_GB} GB"
if (( FREE_GB < 10 )); then
  err "Low free disk space (<10GB) before package installs. Please free space or set FORCE_YES to continue."
  if ! confirm "Proceed anyway?"; then die "Aborted due to low disk space before package installs."; fi
fi

# 2.a) Ensure Xcode Command Line Tools (best-effort)
ensure_xcode_clt() {
  if xcode-select -p >/dev/null 2>&1 && [[ -d "$(xcode-select -p)" ]]; then
    log "Xcode Command Line Tools detected at: $(xcode-select -p)"
    return 0
  fi

  log "Xcode Command Line Tools not found. Attempting to trigger install..."
  sudo rm -rf /Library/Developer/CommandLineTools >/dev/null 2>&1 || true
  # Non-blocking attempt to launch the installer UI (may require user approval)
  if ! sudo xcode-select --install >/dev/null 2>&1; then
    log "xcode-select --install returned non-zero; manual install may be required."
  else
    log "xcode-select --install invoked."
  fi

  # Wait up to 600s for tools to appear
  local tries=0 max_wait=600
  while ! xcode-select -p >/dev/null 2>&1; do
    sleep 5; tries=$((tries+5))
    if (( tries >= max_wait )); then
      err "Timed out waiting for Command Line Tools to install. If Homebrew fails, run 'sudo xcode-select --install' and re-run this script."
      return 1
    fi
  done

  log "Xcode Command Line Tools installed at: $(xcode-select -p)"
  return 0
}

# Attempt CLT but do not fatal immediately if unavailable; provide guidance later.
if ! ensure_xcode_clt; then
  err "Proceeding despite Command Line Tools issue; Homebrew may require manual intervention if install fails."
fi

# 2.b) Ensure Homebrew is installed and available in PATH
ensure_homebrew() {
  if check_cmd brew; then
    log "Homebrew already installed: $(brew --version 2>/dev/null | head -n1 || true)"
    return 0
  fi

  log "Homebrew not found — installing Homebrew (non-interactive where possible)..."
  if ! /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null; then
    err "Homebrew installer failed."
    return 1
  fi

  # Configure shell for common prefixes
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)" || true
    if ! grep -Fq 'homebrew/bin/brew shellenv' "${HOME}/.zprofile" 2>/dev/null; then
      printf '\n# Homebrew\neval "$(/opt/homebrew/bin/brew shellenv)"\n' >> "${HOME}/.zprofile" || true
    fi
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)" || true
    if ! grep -Fq 'homebrew/bin/brew shellenv' "${HOME}/.zprofile" 2>/dev/null; then
      printf '\n# Homebrew\neval "$(/usr/local/bin/brew shellenv)"\n' >> "${HOME}/.zprofile" || true
    fi
  fi

  if ! check_cmd brew; then
    err "Homebrew not available in PATH after install. You may need to open a new terminal or source your shell profile."
    return 1
  fi

  log "Homebrew installed successfully: $(brew --version 2>/dev/null | head -n1 || true)"
  return 0
}

if ! ensure_homebrew; then
  die "Homebrew installation failed. Please install Homebrew manually and re-run this installer."
fi

# 2.c) Use Homebrew to install ollama and python (idempotent, with retries)
log "Updating Homebrew and installing required packages (ollama, python)..."
brew update >/dev/null 2>&1 || log "brew update reported warnings; continuing..."

install_with_brew() {
  local pkg=$1
  local i=0
  while (( i < MAX_RETRIES )); do
    if brew list --formula | grep -q "^${pkg}\$" 2>/dev/null || brew list --cask | grep -q "^${pkg}\$" 2>/dev/null; then
      log "${pkg} already installed (brew reports)."
      return 0
    fi
    if brew install "${pkg}" >/dev/null 2>&1; then
      log "Installed ${pkg}."
      return 0
    else
      i=$((i+1))
      log "Attempt ${i}/${MAX_RETRIES} to install ${pkg} failed; retrying in ${RETRY_WAIT_SECONDS}s..."
      sleep "${RETRY_WAIT_SECONDS}"
    fi
  done
  err "Failed to install ${pkg} via Homebrew after ${MAX_RETRIES} attempts."
  return 1
}

if ! install_with_brew python; then die "Failed to install python via Homebrew."; fi
if ! install_with_brew ollama; then die "Failed to install ollama via Homebrew."; fi

# Verify availability
if ! check_cmd python3; then
  err "python3 not found after brew install. Attempting to use 'python'..."
  if check_cmd python; then
    log "python exists; python --version: $(python --version 2>&1 || true)"
  else
    die "python3 is not available. Please install Python3 and re-run."
  fi
fi

if ! check_cmd ollama; then
  die "ollama not available after brew install. Please re-run after fixing Homebrew/network connectivity."
fi

log "Homebrew, ollama, python OK"

# 3) Start Ollama daemon (background)
log "Starting Ollama daemon (background)... logs -> $LOG_DIR/ollama_*.log"
mkdir -p "$LOG_DIR"
if ! pgrep -f "ollama serve" >/dev/null 2>&1; then
  nohup ollama serve --watch >"$LOG_DIR/ollama_stdout.log" 2>"$LOG_DIR/ollama_stderr.log" &
  sleep 2
fi
if wait_for_http "$OLLAMA_HTTP/api/tags" 60; then
  log "Ollama HTTP API responding"
else
  log "Ollama did not respond within timeout. Model pulls may still work later. Check $LOG_DIR/ollama_stderr.log"
fi

# 4) Prepare server app files (FastAPI + static UI + assistant functions)
log "Creating server app (FastAPI) and browser UI..."

# Ensure server static directory exists before writing files
mkdir -p "$STATIC_DIR" || die "Failed to create $STATIC_DIR before writing UI"

# server: requirements (only update if needed - add new dependencies)
if [[ ! -f "$SERVER_DIR/requirements.txt" ]] || ! grep -q "python-pptx" "$SERVER_DIR/requirements.txt"; then
  log "Updating requirements.txt with latest dependencies..."
  cat > "$SERVER_DIR/requirements.txt" <<'REQ'
fastapi
uvicorn[standard]
httpx
python-dateutil
pydantic
keyring
python-pptx
python-docx
reportlab
REQ
fi

# server: app.py - Use repository version if available, otherwise create basic version
if [[ ! -f "$SERVER_DIR/app.py" ]]; then
  log "Creating app.py from template..."
  cat > "$SERVER_DIR/app.py" <<'PY'
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import subprocess, shlex, json, os, logging, asyncio, sys
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exec_assist_server")

APP_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.abspath(os.path.join(APP_DIR, "..", "data"))

app = FastAPI(title="Executive Assistant")

# Serve the static UI
static_dir = os.path.join(APP_DIR, "static")
if not os.path.isdir(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Health
@app.get("/health")
async def health():
    return {"status":"healthy"}

# List local ollama models using CLI
@app.get("/api/models")
async def models():
    try:
        out = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=False)
        return JSONResponse({"raw": out.stdout, "err": out.stderr})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Simple chat endpoint: calls ollama CLI (best-effort)
@app.post("/api/chat")
async def chat(req: Request):
    data = await req.json()
    prompt = data.get("prompt", "")
    model = data.get("model", os.environ.get("DEFAULT_OLLAMA_MODEL", "llama-2-3b-chat"))
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing prompt")
    try:
        cmd = ["ollama", "run", model, "--prompt", prompt]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
        text = proc.stdout.strip() or proc.stderr.strip()
        return {"model": model, "response": text}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Model generation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Function-calling endpoint: forward to assistant functions module
@app.post("/api/function_call")
async def function_call(req: Request):
    data = await req.json()
    name = data.get("name") or data.get("function_name")
    args = data.get("arguments", {})
    if not name:
        raise HTTPException(status_code=400, detail="Missing function name")
    try:
        import importlib
        af = importlib.import_module("assistant_functions")
        if not hasattr(af, "execute_function"):
            raise Exception("assistant_functions.execute_function not found")
        func = getattr(af, "execute_function")
        if asyncio.iscoroutinefunction(func):
            res = await func(name, args)
        else:
            res = await asyncio.get_event_loop().run_in_executor(None, lambda: func(name, args))
        return {"status":"success", "result": res}
    except Exception as e:
        logger.exception("function_call error")
        return {"status":"error", "error": str(e)}

# List available functions
@app.get("/api/functions")
async def list_functions():
    try:
        import assistant_functions
        return {"functions": assistant_functions.get_function_info()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
PY
else
  log "Using existing app.py from repository (includes latest features)"
fi

# server: assistant_functions.py - Use repository version if available
if [[ ! -f "$SERVER_DIR/assistant_functions.py" ]]; then
  log "Creating assistant_functions.py from template..."
  cat > "$SERVER_DIR/assistant_functions.py" <<'PY'
"""
assistant_functions.py
Provides functions: notes, calendar, contacts, email (IMAP/SMTP), search, summarize.
Stored data lives under ../data relative to this file.
"""
import os, json, random, logging, email, imaplib, smtplib, asyncio
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.header import decode_header

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("assistant_functions")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
NOTES_DIR = os.path.join(ROOT, "notes")
CALENDAR_FILE = os.path.join(ROOT, "calendar", "events.json")
CONTACTS_FILE = os.path.join(ROOT, "contacts", "contacts.json")
EMAIL_ACCOUNTS_FILE = os.path.join(ROOT, "email_accounts.json")

os.makedirs(NOTES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
os.makedirs(os.path.dirname(CONTACTS_FILE), exist_ok=True)

# Initialize files if missing
if not os.path.exists(CALENDAR_FILE):
    with open(CALENDAR_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(CONTACTS_FILE):
    with open(CONTACTS_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(EMAIL_ACCOUNTS_FILE):
    with open(EMAIL_ACCOUNTS_FILE, "w") as f:
        json.dump({}, f)

# Function registry metadata
FUNCTION_REGISTRY = {
    "test_connection": {"description":"Test connection", "parameters":["query"]},
    "take_notes": {"description":"Save a note", "parameters":["content","title"]},
    "get_notes": {"description":"Get a note or list", "parameters":["title"]},
    "add_calendar_event": {"description":"Add event", "parameters":["title","date","time","description"]},
    "get_calendar": {"description":"Get calendar events", "parameters":["days"]},
    "add_contact": {"description":"Add contact", "parameters":["name","email","phone","notes"]},
    "search_contacts": {"description":"Search contacts", "parameters":["query"]},
    "fetch_unread_emails": {"description":"Fetch unread emails", "parameters":["account_id","max_messages"]},
    "mark_email_read": {"description":"Mark email read", "parameters":["account_id","uid"]},
    "send_email": {"description":"Send an email", "parameters":["account_id","to","subject","body"]},
    "summarize_text": {"description":"Summarize text", "parameters":["text"]}
}

def _load_email_accounts():
    try:
        with open(EMAIL_ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_email_accounts(accounts):
    with open(EMAIL_ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    os.chmod(EMAIL_ACCOUNTS_FILE, 0o600)

def _decode_header(h):
    parts = decode_header(h)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out += text.decode(enc or "utf-8", errors="replace")
            except Exception:
                out += text.decode("utf-8", errors="replace")
        else:
            out += text
    return out

# Basic functions
async def test_connection(query="test", **kwargs):
    return {"message": f"Assistant reachable. Query: {query}", "timestamp": datetime.now().isoformat(), "functions": list(FUNCTION_REGISTRY.keys())}

async def take_notes(content, title=None, **kwargs):
    if not title:
        title = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title).strip().replace(' ','_') + ".txt"
    path = os.path.join(NOTES_DIR, filename)
    with open(path, "w") as f:
        f.write(content)
    return {"message":"note saved", "filename": filename, "timestamp": datetime.now().isoformat()}

async def get_notes(title=None, **kwargs):
    if title:
        filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title).strip().replace(' ','_') + ".txt"
        path = os.path.join(NOTES_DIR, filename)
        try:
            with open(path) as f:
                return {"title": title, "content": f.read(), "timestamp": datetime.now().isoformat()}
        except FileNotFoundError:
            return {"error": "not found", "available": await list_notes()}
    return await list_notes()

async def list_notes(**kwargs):
    notes=[]
    for fn in os.listdir(NOTES_DIR):
        if fn.endswith(".txt"):
            notes.append({"title":fn.replace('_',' ').replace('.txt',''), "filename":fn})
    return {"notes":notes, "count":len(notes)}

# Calendar
async def add_calendar_event(title, date, time=None, description=None, **kwargs):
    with open(CALENDAR_FILE) as f:
        events = json.load(f)
    event={"id": str(random.randint(10000,99999)), "title":title, "date":date, "time":time, "description":description, "created_at": datetime.now().isoformat()}
    events.append(event)
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)
    return {"message":"event added", "event":event}

async def get_calendar(days=7, **kwargs):
    with open(CALENDAR_FILE) as f:
        all_events = json.load(f)
    today = datetime.now().date()
    end = today + timedelta(days=int(days))
    events=[]
    for ev in all_events:
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            if today <= d <= end:
                events.append(ev)
        except Exception:
            pass
    return {"events": events, "count": len(events)}

# Contacts
async def add_contact(name, email=None, phone=None, notes=None, **kwargs):
    with open(CONTACTS_FILE) as f:
        contacts = json.load(f)
    contact={"id": str(random.randint(10000,99999)), "name":name, "email":email, "phone":phone, "notes":notes, "created_at": datetime.now().isoformat()}
    contacts.append(contact)
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)
    return {"message":"contact added", "contact":contact}

async def search_contacts(query, **kwargs):
    with open(CONTACTS_FILE) as f:
        contacts = json.load(f)
    q = query.lower()
    matches = [c for c in contacts if q in (c.get("name","")+c.get("email","")+c.get("phone","")+c.get("notes","")).lower()]
    return {"contacts":matches, "count":len(matches)}

# Web search (simulated)
async def search_web(query, **kwargs):
    return {"message": f"Simulated results for {query}", "results":[{"title":"Example","url":"https://example.com"}]}

# Summarize (simple)
async def summarize_text(text, **kwargs):
    words = text.split()
    summary = " ".join(words[:min(30, max(1,len(words)//3))]) + "..."
    return {"summary": summary, "original_length": len(words)}

# Email helpers (IMAP/SMTP) - synchronous work run in thread via asyncio
def _read_accounts():
    try:
        with open(EMAIL_ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_accounts(accounts):
    with open(EMAIL_ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    os.chmod(EMAIL_ACCOUNTS_FILE, 0o600)

async def add_email_account(account_id, imap_host, imap_port, smtp_host, smtp_port, username, password, use_ssl=True, **kwargs):
    def _sync():
        accounts = _read_accounts()
        accounts[account_id] = {"imap_host": imap_host, "imap_port": int(imap_port), "smtp_host": smtp_host, "smtp_port": int(smtp_port), "username": username, "password": password, "use_ssl": bool(use_ssl)}
        _save_accounts(accounts)
        return {"message": f"Saved account {account_id}"}
    return await asyncio.to_thread(_sync)

async def list_email_accounts(**kwargs):
    accounts = _read_accounts()
    return {"accounts": list(accounts.keys()), "count": len(accounts)}

async def fetch_unread_emails(account_id, max_messages=10, **kwargs):
    def _sync():
        accounts = _read_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found", "available": list(accounts.keys())}
        host = acct["imap_host"]; port = int(acct.get("imap_port",993)); use_ssl = acct.get("use_ssl", True)
        username = acct["username"]; password = acct["password"]
        try:
            if use_ssl:
                M = imaplib.IMAP4_SSL(host, port)
            else:
                M = imaplib.IMAP4(host, port)
            M.login(username, password)
            M.select("INBOX")
            typ, data = M.search(None, "UNSEEN")
            uids = data[0].split() if data and data[0] else []
            uids = uids[-int(max_messages):]
            results=[]
            for uid in reversed(uids):
                typ, msg_data = M.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = _decode_header(msg.get("Subject",""))
                frm = _decode_header(msg.get("From",""))
                date = msg.get("Date","")
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        disp = str(part.get("Content-Disposition"))
                        if ctype == "text/plain" and "attachment" not in disp:
                            try:
                                body = part.get_payload(decode=True).decode(errors="replace")
                            except Exception:
                                body = str(part.get_payload())
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="replace")
                    except Exception:
                        body = str(msg.get_payload())
                preview = " ".join(body.strip().splitlines())[:400] + ("..." if len(body)>400 else "")
                results.append({"uid": uid.decode() if isinstance(uid, bytes) else str(uid), "from": frm, "subject": subject, "date": date, "preview": preview})
            M.logout()
            return {"messages": results, "count": len(results)}
        except imaplib.IMAP4.error as e:
            return {"error": f"IMAP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    return await asyncio.to_thread(_sync)

async def mark_email_read(account_id, uid, **kwargs):
    def _sync():
        accounts = _read_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        host = acct["imap_host"]; port = int(acct.get("imap_port",993)); use_ssl = acct.get("use_ssl", True)
        username = acct["username"]; password = acct["password"]
        try:
            if use_ssl:
                M = imaplib.IMAP4_SSL(host, port)
            else:
                M = imaplib.IMAP4(host, port)
            M.login(username, password)
            M.select("INBOX")
            M.store(uid, '+FLAGS', '\\Seen')
            M.logout()
            return {"message": f"Marked {uid} as read"}
        except Exception as e:
            return {"error": str(e)}
    return await asyncio.to_thread(_sync)

async def send_email(account_id, to, subject, body, **kwargs):
    def _sync():
        accounts = _read_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        smtp_host = acct["smtp_host"]; smtp_port = int(acct["smtp_port"])
        username = acct["username"]; password = acct["password"]; use_ssl = acct.get("use_ssl", True)
        try:
            msg = EmailMessage()
            msg["From"] = username; msg["To"] = to; msg["Subject"] = subject
            msg.set_content(body)
            if smtp_port == 465 or use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30); server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            return {"message":"Email sent"}
        except Exception as e:
            return {"error": str(e)}
    return await asyncio.to_thread(_sync)

# Router: execute function by name
async def execute_function(function_name, arguments):
    mapping = {
        "test_connection": test_connection,
        "take_notes": take_notes,
        "get_notes": get_notes,
        "list_notes": list_notes,
        "add_calendar_event": add_calendar_event,
        "get_calendar": get_calendar,
        "add_contact": add_contact,
        "search_contacts": search_contacts,
        "fetch_unread_emails": fetch_unread_emails,
        "mark_email_read": mark_email_read,
        "send_email": send_email,
        "summarize_text": summarize_text
    }
    fn = mapping.get(function_name)
    if not fn:
        return {"error": f"Function '{function_name}' not found", "available": list(mapping.keys())}
    return await fn(**arguments)

def get_function_names():
    return list(FUNCTION_REGISTRY.keys())

def get_function_info():
    return FUNCTION_REGISTRY
PY
else
  log "Using existing assistant_functions.py from repository (includes latest email management features)"
fi

# server: static UI (simple chat + function calls + voice via browser dictation)
cat > "$STATIC_DIR/index.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Executive Assistant</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial; margin: 0; padding: 0; background:#f7f7f8; }
    header { background:#0b5cff; color:white; padding:16px; }
    #app { max-width:900px; margin:20px auto; padding:16px; background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.08); }
    #messages { height:400px; overflow:auto; border:1px solid #eee; padding:12px; }
    .msg { margin:8px 0; }
    .user { color:#0b5cff; font-weight:600; }
    .assistant { color:#222; }
    textarea { width:100%; height:80px; }
    button { padding:8px 12px; margin-top:8px; }
  </style>
</head>
<body>
<header><h1>Executive Assistant</h1></header>
<div id="app">
  <div id="info">Open the microphone (macOS dictation or browser mic) to speak. Use the box below to type requests.</div>
  <div id="messages"></div>
  <textarea id="prompt" placeholder="Ask: 'Read my unread email' or 'Summarize unread messages'"></textarea>
  <div>
    <button id="send">Send</button>
    <button id="fetchMail">Fetch unread mail</button>
    <select id="accountSelect"></select>
  </div>
  <div id="status"></div>
</div>

<script>
async function api(path, opts={}) {
  const r = await fetch(path, Object.assign({headers: {'Content-Type':'application/json'}}, opts));
  return r.json();
}
function appendwho(who, text){ const d=document.createElement('div'); d.className='msg '+who; d.innerHTML='<b>'+who+':</b> '+text; document.getElementById('messages').appendChild(d); document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight; }

async function listAccounts(){
  try{
    const res = await api('/api/function_call', {method:'POST', body: JSON.stringify({name:'list_email_accounts', arguments:{}})});
    const accounts = (res.result && res.result.accounts) || [];
    const sel=document.getElementById('accountSelect'); sel.innerHTML=''; accounts.forEach(a=>{ const o=document.createElement('option'); o.value=a; o.textContent=a; sel.appendChild(o);});
  }catch(e){console.log(e)}
}

document.getElementById('send').onclick = async ()=>{
  const p = document.getElementById('prompt').value.trim(); if(!p) return;
  appendwho('user', p);
  document.getElementById('prompt').value='';
  document.getElementById('status').textContent='Thinking...';
  try{
    const resp = await api('/api/chat',{method:'POST', body: JSON.stringify({prompt:p})});
    appendwho('assistant', resp.response || JSON.stringify(resp));
  }catch(e){ appendwho('assistant','Error: '+e); }
  document.getElementById('status').textContent='';
};

document.getElementById('fetchMail').onclick = async ()=>{
  const acct = document.getElementById('accountSelect').value;
  appendwho('user', 'Fetch unread mail for '+acct);
  document.getElementById('status').textContent='Fetching mail...';
  try{
    const resp = await api('/api/function_call', {method:'POST', body: JSON.stringify({name:'fetch_unread_emails', arguments:{account_id:acct, max_messages:5}})});
    const res = resp.result || resp;
    if(res.error){ appendwho('assistant','Error: '+res.error); }
    else if(res.messages && res.messages.length){
      res.messages.forEach(m=> appendwho('assistant', '<b>'+m.subject+'</b> from '+m.from+' — '+m.preview));
    } else { appendwho('assistant', 'No unread messages'); }
  }catch(e){ appendwho('assistant','Error: '+e); }
  document.getElementById('status').textContent='';
};

window.addEventListener('load', ()=>{ listAccounts(); setInterval(listAccounts, 15000); });
</script>
</body>
</html>
HTML

# 5) scripts/run_server.sh - starts uvicorn using venv
mkdir -p "$REPO_DIR/scripts"
cat > "$RUN_SH" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$HOME/.virtualenvs/executive-assistant"
export PATH="$VENV_DIR/bin:$PATH"
# Load config if present
if [[ -f "$REPO_ROOT/config.env" ]]; then
  set -o allexport
  # shellcheck disable=SC1090
  source "$REPO_ROOT/config.env"
  set +o allexport
fi
cd "$REPO_ROOT/server"
exec uvicorn app:app --host 127.0.0.1 --port 8001 --log-level info
SH
chmod +x "$RUN_SH"

# 6) Write config.env default model
cat > "$CONFIG_FILE" <<EOF
DEFAULT_OLLAMA_MODEL="$MODEL_3B"
EOF

# 7) Python venv + dependencies
log "Creating Python virtualenv and installing server requirements..."
mkdir -p "$(dirname "$VENV_DIR")"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$SERVER_DIR/requirements.txt" >/dev/null

# 8) Email credential prompt & save (interactive or env-driven)
log "Email account setup: credentials are stored locally only at $DATA_DIR/email_accounts.json (mode 600)"
EMAIL_FILE="$DATA_DIR/email_accounts.json"
touch "$EMAIL_FILE"
chmod 600 "$EMAIL_FILE"

_save_email_account() {
  local acct_id="$1" imap_host="$2" imap_port="$3" smtp_host="$4" smtp_port="$5" username="$6" password="$7" use_ssl="$8"
  # use_ssl passed as 'true' or 'false' (lowercase strings)
  python3 - <<PY
import json, os
p = os.path.expanduser("$EMAIL_FILE")
accounts = {}
if os.path.exists(p):
    try:
        with open(p,'r') as f:
            accounts = json.load(f)
    except Exception:
        accounts = {}
# use_ssl passed as a string; convert to bool in Python
use_ssl_str = '${use_ssl}'
use_ssl_bool = str(use_ssl_str).lower() in ('true','1','yes','y')
accounts["${acct_id}"] = {
    "imap_host": "${imap_host}",
    "imap_port": int(${imap_port}),
    "smtp_host": "${smtp_host}",
    "smtp_port": int(${smtp_port}),
    "username": "${username}",
    "password": "${password}",
    "use_ssl": use_ssl_bool
}
with open(p,'w') as f:
    json.dump(accounts, f, indent=2)
os.chmod(p, 0o600)
print("Saved account ${acct_id} -> "+p)
PY
}

# Auto-add environment-provided Yahoo credentials if present
if [[ -n "${YAHOO_EMAIL:-}" && -n "${YAHOO_APP_PASSWORD:-}" ]]; then
  acct_id="yahoo_${USER}"
  _save_email_account "$acct_id" "${YAHOO_IMAP_SERVER:-imap.mail.yahoo.com}" "${YAHOO_IMAP_PORT:-993}" "${YAHOO_SMTP_SERVER:-smtp.mail.yahoo.com}" "${YAHOO_SMTP_PORT:-465}" "${YAHOO_EMAIL}" "${YAHOO_APP_PASSWORD}" "true"
fi

# Check if stdin is a terminal (interactive)
if [[ -t 0 ]] && [[ "$FORCE_YES" != "yes" ]]; then
  if confirm "Would you like to add an email account now so the assistant can fetch mail? (recommended)"; then
    while true; do
      read -r -p "Enter a short account id (e.g. mom_yahoo): " acct_id
      read -r -p "IMAP host (default: imap.mail.yahoo.com): " imap_host; imap_host="${imap_host:-imap.mail.yahoo.com}"
      read -r -p "IMAP port (default: 993): " imap_port; imap_port="${imap_port:-993}"
      read -r -p "SMTP host (default: smtp.mail.yahoo.com): " smtp_host; smtp_host="${smtp_host:-smtp.mail.yahoo.com}"
      read -r -p "SMTP port (default: 465): " smtp_port; smtp_port="${smtp_port:-465}"
      read -r -p "Username (email address): " username
      echo -n "Paste the app password (input hidden): "
      read -r -s password; echo
      read -r -p "Use SSL for IMAP/SMTP? (Y/n): " use_ssl_ans
      if [[ "${use_ssl_ans}" =~ ^(N|n) ]]; then use_ssl="false"; else use_ssl="true"; fi
      echo "Saving: ${acct_id} -> ${username} @ ${imap_host}:${imap_port} (use_ssl=${use_ssl})"
      if confirm "Proceed and save this account?"; then
        _save_email_account "$acct_id" "$imap_host" "$imap_port" "$smtp_host" "$smtp_port" "$username" "$password" "$use_ssl"
        if ! confirm "Add another account?"; then break; fi
      else
        echo "Not saved; try again."
      fi
    done
  else
    log "Skipping interactive email account creation."
  fi
else
  if [[ "$FORCE_YES" == "yes" ]]; then
    log "FORCE_YES set; skipping interactive prompts."
  else
    log "Non-interactive mode detected (stdin not a terminal)."
    log "To configure email accounts, see: ${REPO_DIR}/EMAIL_QUICKSTART.md"
    log "Or run this installer again locally: cd ~/executive-assistant && ./install_executive_assistant_mac.sh"
  fi
fi

# 9) Pull Ollama models (best-effort)
if [[ "$SKIP_MODEL_PULL" != "yes" ]]; then
  # Re-check free space before pulling models
  FREE_GB=$(available_disk_gb || echo 0)
  log "Free disk space before model pulls: ${FREE_GB} GB"
  if (( FREE_GB < 10 )); then
    err "Insufficient disk space for model pulls. Skipping model downloads. Free up disk space or pull models manually."
  else
    # Corrected model names
    MODEL_3B="llama3.2:3b"
    MODEL_7B="mistral:7b"
    
    log "Attempting to pull Ollama models. Default 3B: $MODEL_3B; optional 7B: $MODEL_7B"
    
    # Debugging command to verify ollama environment first
    log "Checking Ollama version and CLI status..."
    if ! ollama --version; then
      err "Ollama CLI unavailable. Ensure Ollama is properly installed and accessible."
      log "You can manually pull models later with: ollama pull $MODEL_3B"
    else
      log "Ollama CLI OK: $(ollama --version 2>&1 | head -1)"
      
      # Pull the 3B model (required for AI NLP features)
      log "Pulling Llama 3.2 3B model ($MODEL_3B) - this may take several minutes..."
      
      # Try up to 2 times in case of network issues
      pull_success=false
      for attempt in 1 2; do
        log "Pull attempt $attempt/2..."
        if ollama pull "$MODEL_3B" 2>&1 | tee "$LOG_DIR/model_pull_${attempt}.log"; then
          log "✓ Successfully pulled Llama 3.2 3B model: $MODEL_3B"
          pull_success=true
          break
        else
          err "✗ Pull attempt $attempt failed for $MODEL_3B"
          if [ $attempt -eq 1 ]; then
            log "Retrying in 5 seconds..."
            sleep 5
          fi
        fi
      done
      
      if [ "$pull_success" = "false" ]; then
        err "✗ Failed to pull Llama 3.2 3B model after 2 attempts: $MODEL_3B"
        err "Check logs: $LOG_DIR/model_pull_*.log"
        err "You can manually pull it later with: ollama pull $MODEL_3B"
      fi
      
      # Optional: Pull the 7B model if user confirms and has space
      if (( FREE_GB >= 20 )) && confirm "Pull optional Mistral 7B model (requires ~4GB, better quality)? "; then
        log "Pulling Mistral 7B model ($MODEL_7B)..."
        if ollama pull "$MODEL_7B" 2>&1 | tee -a "$LOG_DIR/model_pull.log"; then
          log "✓ Successfully pulled Mistral 7B model: $MODEL_7B"
        else
          err "✗ Failed to pull Mistral 7B model: $MODEL_7B"
          log "This is optional - the 3B model should work fine."
        fi
      else
        log "Skipping optional 7B model pull."
      fi
      
      # Verify models were pulled successfully
      log "Verifying installed models..."
      sleep 2  # Give Ollama time to register the new models
      
      if ollama list 2>&1 | tee "$LOG_DIR/ollama_list.log"; then
        log "Current models:"
        ollama list
        
        if ollama list | grep -qi "llama3.2"; then
          log "✓ Confirmed: $MODEL_3B is installed and ready"
        else
          err "✗ Warning: $MODEL_3B not found in ollama list"
          err "Attempting one more pull..."
          if ollama pull "$MODEL_3B"; then
            log "✓ Retry successful - model now available"
          else
            err "✗ Retry failed - The server will attempt to auto-pull it on first use."
          fi
        fi
      else
        err "Could not verify models with 'ollama list' - check Ollama is running"
        err "Run: pgrep -f 'ollama serve' to check if Ollama daemon is running"
      fi
      
      log "Model installation logs saved to: $LOG_DIR/model_pull.log"
      log "To check models anytime: ollama list"
    fi
  fi
else
  log "SKIP_MODEL_PULL=yes - skipping model downloads as requested."
  log "Note: You'll need to manually pull a model for AI features:"
  log "  ollama pull llama3.2:3b"
fi

# 10) Install launchd plist so server runs at login (per-user)
log "Installing per-user launchd agent to start server at login..."
mkdir -p ~/Library/LaunchAgents
cat > "$LAUNCH_PLIST_USER" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>com.executiveassistant.server</string>
    <key>ProgramArguments</key>
    <array>
      <string>$RUN_SH</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>StandardOutPath</key><string>$LOG_DIR/launchd_stdout.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/launchd_stderr.log</string>
    <key>WorkingDirectory</key><string>$REPO_DIR</string>
  </dict>
</plist>
PLIST

# Load the launchd agent (unload first for idempotence)
launchctl unload "$LAUNCH_PLIST_USER" 2>/dev/null || true
if launchctl load "$LAUNCH_PLIST_USER" 2>/dev/null; then
  log "Loaded launchd agent: $LAUNCH_PLIST_USER"
else
  err "Failed to load launchd agent (you can load it manually with: launchctl load $LAUNCH_PLIST_USER)"
fi

# 11) Start server now (run_server.sh is started by launchd; start immediately for this session)
log "Starting server now (foreground via run_server.sh launched by launchd or start it manually)..."
if wait_for_http "http://127.0.0.1:${PORT}/health" 10; then
  log "Server is responding at http://127.0.0.1:${PORT}/health"
else
  log "Server not yet responding. Starting run_server.sh in background for immediate use..."
  nohup "$RUN_SH" >"$LOG_DIR/server_stdout.log" 2>"$LOG_DIR/server_stderr.log" &
  sleep 2
  if wait_for_http "http://127.0.0.1:${PORT}/health" 10; then
    log "Server is now responding."
  else
    err "Server did not start successfully. Check logs: $LOG_DIR/server_stderr.log"
  fi
fi

# 12) Open browser to UI
log "Opening browser to the Assistant UI: http://127.0.0.1:${PORT}/"
open "http://127.0.0.1:${PORT}/" || true

log "INSTALL COMPLETE"
log " - Repo: $REPO_DIR"
log " - Data dir: $DATA_DIR"
log " - Email accounts file: $EMAIL_FILE"
log " - Models pulled (if not skipped): $MODEL_3B , $MODEL_7B"
log " - Log directory: $LOG_DIR"
log ""
log "📋 TROUBLESHOOTING COMMANDS:"
log "  Check server logs:    tail -50 $LOG_DIR/server_stderr.log"
log "  Check Ollama logs:    tail -50 $LOG_DIR/ollama_stderr.log"
log "  Check model pull:     tail -50 $LOG_DIR/model_pull.log"
log "  List installed models: ollama list"
log "  Check if server up:    curl http://127.0.0.1:8001/health"
log "  Check Ollama health:   curl http://127.0.0.1:11434/api/tags"
log ""
log "🔧 IF AI FEATURES DON'T WORK:"
log "  1. Check if Ollama is running: pgrep -f 'ollama serve'"
log "  2. Start Ollama if needed: ollama serve"
log "  3. Pull model if missing: ollama pull llama3.2:3b"
log "  4. Restart server: launchctl unload $LAUNCH_PLIST_USER && launchctl load $LAUNCH_PLIST_USER"
log ""
log "For detailed help, see: $REPO_DIR/INSTALLATION_GUIDE.md"
log "If anything fails, copy the exact Terminal output or $LOG_DIR/* for troubleshooting."
exit 0