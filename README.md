# Executive Assistant

A native macOS application providing AI-powered executive assistance with email management, document generation, and task automation using local Ollama models.

## Quick Start (macOS)

### Automated Installation

The easiest way to install Executive Assistant on macOS is to use the automated installation script:

```bash
# Clone the repository
git clone https://github.com/cdgray33-git/executive-assistant.git
cd executive-assistant

# Run the installer (interactive mode)
./install_mac_assistant.sh

# Or run in non-interactive mode (auto-accept all prompts)
FORCE_YES=1 ./install_mac_assistant.sh
```

The installation script will:
- ✓ Check and install required dependencies (Xcode CLI, Homebrew, Python 3, git)
- ✓ Verify sufficient disk space (minimum 5GB)
- ✓ Set up directories for logs, updates, and backups
- ✓ Create Python virtual environment and install dependencies
- ✓ Install and start Ollama service
- ✓ Configure email settings (optional)
- ✓ Generate API key for secure access
- ✓ Start the FastAPI server
- ✓ Verify the installation with health checks

### After Installation

Once installed, the server will be running at:
- **Health Check:** http://127.0.0.1:8001/health
- **API Status:** http://127.0.0.1:8001/api/status

Configuration files are stored in `~/ExecutiveAssistant/`:
- `config.env` - API key and environment settings
- `logs/` - Application logs
- `updates/` - Update packages
- `backups/` - Backup files

### Manual Installation

For more control or troubleshooting, see [docs/INSTALL_MAC_NATIVE.md](docs/INSTALL_MAC_NATIVE.md) for step-by-step manual installation instructions.

## Features

- **Local AI Processing:** Uses Ollama for private, on-device AI inference
- **Email Management:** Supports Gmail, Yahoo, Hotmail, Apple Mail, and IMAP
- **Secure API:** API key authentication for all endpoints
- **Document Generation:** PowerPoint and other document automation
- **Update Management:** Built-in update and backup system

## Requirements

- macOS (tested on Apple Silicon M1/M2/M3)
- 5GB+ free disk space
- Internet connection for initial setup

## Usage

### Starting the Server

The server starts automatically after installation. To manually start:

```bash
~/executive-assistant/scripts/run_server.sh
```

### Stopping the Server

```bash
kill $(cat ~/ExecutiveAssistant/server.pid)
```

### Viewing Logs

```bash
tail -f ~/ExecutiveAssistant/logs/server.log
```

## API Documentation

All protected endpoints require an API key header:

```bash
X-API-Key: your_api_key_here
```

Find your API key in `~/ExecutiveAssistant/config.env`.

### Available Endpoints

- `GET /health` - Health check (no auth required)
- `GET /api/status` - API status (no auth required)
- `GET /api/models` - List available Ollama models (requires auth)
- `POST /api/function_call` - Execute assistant functions (requires auth)

## Development

### Project Structure

```
executive-assistant/
├── server/           # FastAPI backend
│   ├── app.py       # Main application
│   ├── security.py  # Authentication
│   ├── llm/         # Ollama adapter
│   └── connectors/  # Email connectors
├── scripts/         # Helper scripts
├── ui/              # Frontend (placeholder)
└── docs/            # Documentation
```

## Troubleshooting

### Server won't start

Check the logs:
```bash
cat ~/ExecutiveAssistant/logs/server.log
cat ~/ExecutiveAssistant/logs/install.log
```

### Ollama not responding

Restart Ollama service:
```bash
killall ollama
ollama serve > ~/ExecutiveAssistant/logs/ollama.log 2>&1 &
```

### Permission denied

Ensure the script is executable:
```bash
chmod +x install_mac_assistant.sh
```

## License

See repository for license information.

## Support

For issues and questions, please file an issue on GitHub.
