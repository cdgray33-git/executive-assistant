"""
Ollama HTTP adapter (native Ollama on macOS) with CLI fallback.

This adapter prefers the HTTP API at http://127.0.0.1:11434 (Ollama native on mac).
If the HTTP API is unavailable it will attempt to fall back to the ollama CLI if
OLLAMA_BIN is available in PATH or set via environment.
"""
from typing import Optional, Dict, Any, List
import os
import subprocess
import json
import logging

import httpx

logger = logging.getLogger("ollama_adapter")
OLLAMA_HTTP = os.environ.get("OLLAMA_HTTP", "http://127.0.0.1:11434")
OLLAMA_CLI = os.environ.get("OLLAMA_BIN", "ollama")
HTTP_TIMEOUT = float(os.environ.get("OLLAMA_HTTP_TIMEOUT", "30.0"))


class OllamaAdapter:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or OLLAMA_HTTP
        self._client = None

    def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of async client"""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=HTTP_TIMEOUT)
        return self._client

    async def ping(self) -> bool:
        """Check Ollama HTTP API endpoint. Fallback to CLI list."""
        try:
            # Try HTTP /api/tags endpoint (Ollama's standard endpoint)
            client = self._get_client()
            r = await client.get("/api/tags")
            if r.status_code == 200:
                return True
        except Exception as e:
            logger.debug("Ollama HTTP API check failed: %s", e)

        # Fallback to CLI
        return self._ping_cli()

    async def list_models(self) -> List[Dict[str, Any]]:
        """Return list of available models (HTTP if possible, else CLI parsing)."""
        try:
            client = self._get_client()
            r = await client.get("/api/tags")
            if r.status_code == 200:
                return r.json().get("models", [])
        except Exception as e:
            logger.debug("Ollama HTTP list models failed: %s", e)

        # CLI fallback
        return self._list_models_cli()

    def _ping_cli(self) -> bool:
        try:
            subprocess.run([OLLAMA_CLI, "list"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def _list_models_cli(self) -> List[Dict[str, Any]]:
        try:
            out = subprocess.check_output([OLLAMA_CLI, "list"], stderr=subprocess.DEVNULL)
            text = out.decode("utf-8", errors="ignore")
            # CLI output is text; return as simple list of names
            models = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                # crude parse: lines often like "model-name (size, ...)"
                models.append({"raw": line})
            return models
        except Exception as e:
            logger.debug("Ollama CLI list failed: %s", e)
            return []

    async def generate(self, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Simple generation helper that tries HTTP /api/generate (Ollama) first,
        then falls back to the CLI if needed.
        """
        payload = {"model": model, "prompt": prompt}
        payload.update(kwargs)
        # Try HTTP endpoint (Ollama's HTTP API)
        try:
            client = self._get_client()
            r = await client.post("/api/generate", json=payload)
            if r.status_code in (200, 201):
                # Ollama returns streaming responses by default, collect all chunks
                response_text = ""
                for line in r.text.strip().split('\n'):
                    if line:
                        try:
                            chunk = json.loads(line)
                            response_text += chunk.get("response", "")
                            if chunk.get("done", False):
                                return {"response": response_text}
                        except json.JSONDecodeError:
                            continue
                return {"response": response_text}
        except Exception as e:
            logger.debug("Ollama HTTP generate failed: %s", e)

        # CLI fallback: use `ollama run <model> --prompt '<prompt>'` (simple)
        try:
            cmd = [OLLAMA_CLI, "run", model, prompt]
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=60)
            text = out.decode("utf-8", errors="ignore")
            return {"response": text}
        except Exception as e:
            logger.debug("Ollama CLI generate failed: %s", e)
            return {"error": "generate_failed", "detail": str(e)}
    
    async def close(self):
        """Close the async client if it exists"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
