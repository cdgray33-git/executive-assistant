#!/usr/bin/env bash
#
# Executive Assistant - macOS Installation Script
# 
# This script fully installs and deploys the Executive Assistant application on macOS.
# It handles dependency checking, installation, configuration, and service startup.
#
# Usage:
#   ./install_mac_assistant.sh              # Interactive mode
#   FORCE_YES=1 ./install_mac_assistant.sh  # Non-interactive mode (auto-accept)
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# ============================================================================
# CONFIGURATION
# ============================================================================

REPO_URL="${REPO_URL:-https://github.com/cdgray33-git/executive-assistant.git}"
INSTALL_DIR="$HOME/ExecutiveAssistant"
VENV_DIR="$HOME/.virtualenvs/executive-assistant"
REPO_DIR="$HOME/executive-assistant"
LOG_FILE="$INSTALL_DIR/logs/install.log"
MIN_DISK_SPACE_GB=5
FORCE_YES="${FORCE_YES:-0}"

# Server configuration
SERVER_PORT=8001
SERVER_HOST="127.0.0.1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}INFO:${NC} $@"
    log "INFO" "$@"
}

success() {
    echo -e "${GREEN}SUCCESS:${NC} $@"
    log "SUCCESS" "$@"
}

warning() {
    echo -e "${YELLOW}WARNING:${NC} $@"
    log "WARNING" "$@"
}

error() {
    echo -e "${RED}ERROR:${NC} $@" >&2
    log "ERROR" "$@"
}

fatal() {
    error "$@"
    exit 1
}

prompt_yes_no() {
    local prompt="$1"
    if [[ "$FORCE_YES" == "1" ]]; then
        info "Auto-accepting: $prompt"
        return 0
    fi
    
    while true; do
        read -p "$prompt [y/N]: " yn
        case $yn in
            [Yy]* ) return 0;;
            [Nn]* ) return 1;;
            "" ) return 1;;
            * ) echo "Please answer yes or no.";;
        esac
    done
}

# ============================================================================
# SYSTEM CHECKS
# ============================================================================

check_macos() {
    info "Checking operating system..."
    if [[ "$(uname -s)" != "Darwin" ]]; then
        fatal "This script is designed for macOS only. Detected: $(uname -s)"
    fi
    success "Running on macOS ($(sw_vers -productVersion))"
}

check_disk_space() {
    info "Checking disk space..."
    local available_kb=$(df -k "$HOME" | tail -1 | awk '{print $4}')
    local available_gb=$((available_kb / 1024 / 1024))
    
    if [[ $available_gb -lt $MIN_DISK_SPACE_GB ]]; then
        fatal "Insufficient disk space. Need at least ${MIN_DISK_SPACE_GB}GB, have ${available_gb}GB"
    fi
    success "Sufficient disk space available: ${available_gb}GB"
}

check_xcode_cli_tools() {
    info "Checking for Xcode Command Line Tools..."
    if xcode-select -p &>/dev/null; then
        success "Xcode Command Line Tools already installed"
        return 0
    fi
    
    warning "Xcode Command Line Tools not found"
    if prompt_yes_no "Install Xcode Command Line Tools?"; then
        info "Installing Xcode Command Line Tools..."
        xcode-select --install
        info "Please complete the installation dialog, then press Enter to continue..."
        read -r
        
        if xcode-select -p &>/dev/null; then
            success "Xcode Command Line Tools installed successfully"
        else
            fatal "Xcode Command Line Tools installation failed"
        fi
    else
        fatal "Xcode Command Line Tools are required"
    fi
}

check_homebrew() {
    info "Checking for Homebrew..."
    if command -v brew &>/dev/null; then
        success "Homebrew already installed ($(brew --version | head -1))"
        return 0
    fi
    
    warning "Homebrew not found"
    if prompt_yes_no "Install Homebrew?"; then
        info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH for Apple Silicon
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        if command -v brew &>/dev/null; then
            success "Homebrew installed successfully"
        else
            fatal "Homebrew installation failed"
        fi
    else
        fatal "Homebrew is required"
    fi
}

check_python() {
    info "Checking for Python 3..."
    if command -v python3 &>/dev/null; then
        local py_version=$(python3 --version | awk '{print $2}')
        success "Python 3 already installed (version $py_version)"
        return 0
    fi
    
    warning "Python 3 not found"
    if prompt_yes_no "Install Python 3 via Homebrew?"; then
        info "Installing Python 3..."
        brew install python
        
        if command -v python3 &>/dev/null; then
            success "Python 3 installed successfully"
        else
            fatal "Python 3 installation failed"
        fi
    else
        fatal "Python 3 is required"
    fi
}

check_git() {
    info "Checking for git..."
    if command -v git &>/dev/null; then
        success "git already installed ($(git --version))"
        return 0
    fi
    
    warning "git not found"
    if prompt_yes_no "Install git via Homebrew?"; then
        info "Installing git..."
        brew install git
        
        if command -v git &>/dev/null; then
            success "git installed successfully"
        else
            fatal "git installation failed"
        fi
    else
        fatal "git is required"
    fi
}

check_ollama() {
    info "Checking for Ollama..."
    if command -v ollama &>/dev/null; then
        success "Ollama already installed"
        return 0
    fi
    
    warning "Ollama not found"
    if prompt_yes_no "Install Ollama via Homebrew?"; then
        info "Installing Ollama..."
        brew install ollama
        
        if command -v ollama &>/dev/null; then
            success "Ollama installed successfully"
        else
            fatal "Ollama installation failed"
        fi
    else
        warning "Ollama not installed - some features may not work"
    fi
}

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

setup_directories() {
    info "Setting up directories..."
    mkdir -p "$INSTALL_DIR"/{logs,updates,backups,static}
    mkdir -p "$(dirname "$VENV_DIR")"
    success "Directories created"
}

setup_repository() {
    info "Setting up repository..."
    
    # Check if we're already in the repo
    if [[ -d "$PWD/.git" ]] && git rev-parse --git-dir &>/dev/null; then
        REPO_DIR="$PWD"
        info "Using existing repository at: $REPO_DIR"
    elif [[ -d "$REPO_DIR/.git" ]]; then
        info "Repository already exists at: $REPO_DIR"
        if prompt_yes_no "Update existing repository?"; then
            cd "$REPO_DIR"
            git pull origin main || git pull origin master || warning "Could not pull latest changes"
        fi
    else
        info "Cloning repository from $REPO_URL..."
        git clone "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
    fi
    
    success "Repository ready at: $REPO_DIR"
}

setup_python_env() {
    info "Setting up Python virtual environment..."
    
    if [[ -d "$VENV_DIR" ]]; then
        info "Virtual environment already exists at: $VENV_DIR"
        if ! prompt_yes_no "Recreate virtual environment?"; then
            info "Using existing virtual environment"
            return 0
        fi
        rm -rf "$VENV_DIR"
    fi
    
    info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    
    info "Upgrading pip..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    
    info "Installing Python dependencies..."
    if [[ -f "$REPO_DIR/server/requirements.txt" ]]; then
        "$VENV_DIR/bin/pip" install -r "$REPO_DIR/server/requirements.txt"
    else
        fatal "requirements.txt not found at $REPO_DIR/server/requirements.txt"
    fi
    
    success "Python environment setup complete"
}

setup_api_key() {
    info "Setting up API key..."
    
    local api_key
    if [[ -f "$INSTALL_DIR/config.env" ]] && grep -q "API_KEY=" "$INSTALL_DIR/config.env"; then
        info "API key already configured in config.env"
        if ! prompt_yes_no "Generate new API key?"; then
            return 0
        fi
    fi
    
    # Generate a secure random API key
    api_key="ea_$(openssl rand -hex 32)"
    
    cat > "$INSTALL_DIR/config.env" <<CFG
# Executive Assistant Configuration
APP_DIR=$INSTALL_DIR
API_KEY="$api_key"
ALLOWED_ORIGIN="http://127.0.0.1:8000"
CFG
    
    success "API key generated and saved to $INSTALL_DIR/config.env"
    info "Your API key: $api_key"
}

start_ollama_service() {
    info "Starting Ollama service..."
    
    if ! command -v ollama &>/dev/null; then
        warning "Ollama not installed, skipping service start"
        return 0
    fi
    
    # Check if Ollama is already running
    if curl -fsS http://127.0.0.1:11434/api/health &>/dev/null; then
        success "Ollama service already running"
        return 0
    fi
    
    info "Starting Ollama in background..."
    nohup ollama serve > "$INSTALL_DIR/logs/ollama.log" 2>&1 &
    local ollama_pid=$!
    
    # Wait for service to be ready
    local attempts=0
    local max_attempts=30
    while [[ $attempts -lt $max_attempts ]]; do
        if curl -fsS http://127.0.0.1:11434/api/health &>/dev/null; then
            success "Ollama service started (PID: $ollama_pid)"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    warning "Ollama service did not become ready within 30 seconds"
}

setup_email_config() {
    info "Setting up email configuration..."
    
    if [[ "$FORCE_YES" == "1" ]]; then
        info "Skipping email configuration (FORCE_YES mode)"
        return 0
    fi
    
    if ! prompt_yes_no "Configure email settings now?"; then
        info "Skipping email configuration"
        return 0
    fi
    
    local email_provider
    echo ""
    echo "Select email provider:"
    echo "  1) Gmail"
    echo "  2) Yahoo"
    echo "  3) Hotmail/Outlook"
    echo "  4) Apple/iCloud"
    echo "  5) Comcast"
    echo "  6) Generic IMAP"
    echo "  7) Skip"
    echo ""
    read -p "Enter choice [1-7]: " email_provider
    
    case $email_provider in
        1) echo "EMAIL_PROVIDER=gmail" >> "$INSTALL_DIR/config.env" ;;
        2) echo "EMAIL_PROVIDER=yahoo" >> "$INSTALL_DIR/config.env" ;;
        3) echo "EMAIL_PROVIDER=hotmail" >> "$INSTALL_DIR/config.env" ;;
        4) echo "EMAIL_PROVIDER=apple" >> "$INSTALL_DIR/config.env" ;;
        5) echo "EMAIL_PROVIDER=comcast" >> "$INSTALL_DIR/config.env" ;;
        6) echo "EMAIL_PROVIDER=imap" >> "$INSTALL_DIR/config.env" ;;
        7) info "Skipping email configuration" ; return 0 ;;
        *) warning "Invalid choice, skipping email configuration" ; return 0 ;;
    esac
    
    success "Email provider configured"
}

start_server() {
    info "Starting FastAPI server..."
    
    # Make run_server.sh executable
    if [[ -f "$REPO_DIR/scripts/run_server.sh" ]]; then
        chmod +x "$REPO_DIR/scripts/run_server.sh"
    fi
    
    # Set environment
    export PYTHONPATH="$REPO_DIR:${PYTHONPATH:-}"
    
    # Source config if available
    if [[ -f "$INSTALL_DIR/config.env" ]]; then
        set +u  # Allow undefined variables temporarily
        source "$INSTALL_DIR/config.env"
        set -u
    fi
    
    info "Starting server on $SERVER_HOST:$SERVER_PORT..."
    nohup "$VENV_DIR/bin/uvicorn" server.app:app \
        --host "$SERVER_HOST" \
        --port "$SERVER_PORT" \
        --workers 1 \
        > "$INSTALL_DIR/logs/server.log" 2>&1 &
    
    local server_pid=$!
    echo "$server_pid" > "$INSTALL_DIR/server.pid"
    
    # Wait for server to be ready
    local attempts=0
    local max_attempts=30
    while [[ $attempts -lt $max_attempts ]]; do
        if curl -fsS "http://$SERVER_HOST:$SERVER_PORT/health" &>/dev/null; then
            success "FastAPI server started (PID: $server_pid)"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    
    warning "Server did not become ready within 30 seconds"
    warning "Check logs at: $INSTALL_DIR/logs/server.log"
}

verify_installation() {
    info "Verifying installation..."
    
    local all_ok=true
    
    # Check server health
    if curl -fsS "http://$SERVER_HOST:$SERVER_PORT/health" &>/dev/null; then
        success "✓ Server is responding"
    else
        error "✗ Server is not responding"
        all_ok=false
    fi
    
    # Check API status
    if curl -fsS "http://$SERVER_HOST:$SERVER_PORT/api/status" &>/dev/null; then
        success "✓ API endpoints are accessible"
    else
        error "✗ API endpoints are not accessible"
        all_ok=false
    fi
    
    # Check Ollama (optional)
    if command -v ollama &>/dev/null; then
        if curl -fsS http://127.0.0.1:11434/api/health &>/dev/null; then
            success "✓ Ollama service is running"
        else
            warning "⚠ Ollama service is not responding"
        fi
    fi
    
    if [[ "$all_ok" == "true" ]]; then
        success "Installation verification passed"
        return 0
    else
        warning "Installation verification had some issues"
        return 1
    fi
}

# ============================================================================
# MAIN INSTALLATION FLOW
# ============================================================================

main() {
    echo ""
    echo "===================================================================="
    echo "  Executive Assistant - macOS Installation"
    echo "===================================================================="
    echo ""
    
    # Create initial log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # System checks
    check_macos
    check_disk_space
    
    # Dependency checks and installation
    check_xcode_cli_tools
    check_homebrew
    check_python
    check_git
    check_ollama
    
    # Setup
    setup_directories
    setup_repository
    setup_python_env
    setup_api_key
    
    # Services
    start_ollama_service
    setup_email_config
    start_server
    
    # Verification
    echo ""
    verify_installation
    
    # Final output
    echo ""
    echo "===================================================================="
    echo "  Installation Complete!"
    echo "===================================================================="
    echo ""
    echo "Server URL:      http://$SERVER_HOST:$SERVER_PORT"
    echo "Health Check:    http://$SERVER_HOST:$SERVER_PORT/health"
    echo "API Status:      http://$SERVER_HOST:$SERVER_PORT/api/status"
    echo ""
    echo "Configuration:   $INSTALL_DIR/config.env"
    echo "Logs:            $INSTALL_DIR/logs/"
    echo "Repository:      $REPO_DIR"
    echo ""
    
    if [[ -f "$INSTALL_DIR/config.env" ]]; then
        echo "To use the API, include this header in your requests:"
        local api_key=$(grep "API_KEY=" "$INSTALL_DIR/config.env" | cut -d'"' -f2)
        echo "  X-API-Key: $api_key"
        echo ""
    fi
    
    echo "Server logs:     tail -f $INSTALL_DIR/logs/server.log"
    echo "Stop server:     kill \$(cat $INSTALL_DIR/server.pid)"
    echo ""
}

# Run main installation
main "$@"
