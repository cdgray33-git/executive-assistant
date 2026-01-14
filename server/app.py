"""
FastAPI application adapted for native macOS Ollama usage.

- Binds to localhost only
- Uses server/security.require_api_key to protect function endpoints
- Provides lightweight status & health endpoints for launchd checks
"""
import os
import logging
from typing import Optional, Any, Dict

from fastapi import FastAPI, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware

# local helpers
from server.security import require_api_key
from server.llm.ollama_adapter import OllamaAdapter

logger = logging.getLogger("executive_assistant")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Executive Assistant API (native mac)")

# Restrict CORS to the local UI
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://127.0.0.1:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama adapter instance
ollama = OllamaAdapter()

def verify_key(x_api_key: Optional[str] = Header(None)):
    """
    FastAPI dependency that verifies X-API-Key header using server.security.require_api_key.
    """
    require_api_key(x_api_key)


@app.get("/health")
async def health():
    """Service health endpoint suitable for launchd or supervisor checks."""
    healthy = ollama.ping()
    return {"status": "healthy" if healthy else "degraded", "ollama": healthy}


@app.get("/api/status")
async def api_status():
    return {"status": "ok", "host": "local", "user": os.environ.get("USER", "unknown")}


@app.get("/api/models", dependencies=[Depends(verify_key)])
async def api_models():
    """List models available to the local Ollama runtime. Requires API key if configured."""
    models = ollama.list_models()
    return {"models": models}


@app.post("/api/function_call", dependencies=[Depends(verify_key)])
async def function_call(payload: Dict[str, Any]):
    """
    Minimal function-call endpoint.
    The real project may route this to server/assistant_functions or a more elaborate router.
    This implementation validates the presence of a function name and echoes arguments.
    """
    try:
        name = payload.get("name") or payload.get("function_name")
        args = payload.get("arguments", {})
        if not name:
            return {"status": "error", "error": "function name required"}
        # For now, echo back the call; integrate with your existing router as needed.
        logger.info("Function call: %s %s", name, args)
        return {"status": "success", "function": name, "arguments": args}
    except Exception as e:
        logger.exception("function_call error")
        return {"status": "error", "error": str(e)}
