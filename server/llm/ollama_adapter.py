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
HTTP_TIMEOUT = float(os.environ.get("OLLAMA_HTTP_TIMEOUT", "120.0"))


class OllamaAdapter:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or OLLAMA_HTTP
        self.client = httpx.Client(base_url=self.base_url, timeout=HTTP_TIMEOUT)

    def ping(self) -> bool:
        """Check Ollama HTTP health endpoint. Fallback to CLI list."""
        try:
            # Try HTTP health
            r = self.client.get("/api/health")
            if r.status_code == 200:
                logger.info("? Ollama HTTP API is available")
                return True
        except Exception as e:
            logger.debug("Ollama HTTP health check failed: %s", e)

        # Fallback to CLI
        return self._ping_cli()

    def list_models(self) -> List[Dict[str, Any]]:
        """Return list of available models (HTTP if possible, else CLI parsing)."""
        try:
            r = self.client.get("/api/tags")
            if r.status_code == 200:
                return r.json().get('models', [])
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

    def generate(self, model: str, prompt: str, **kwargs) -> str:
        """
        Generate text using Ollama. Returns the generated text as a string.
        Tries HTTP /api/generate first, then falls back to CLI.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False  # Important: disable streaming for simple response
        }
        payload.update(kwargs)
        
        # Try HTTP endpoint
        try:
            print(f"?? Attempting HTTP POST to {self.base_url}/api/generate")
            print(f"?? Payload: model={model}, prompt_length={len(prompt)} chars, timeout={HTTP_TIMEOUT}s")
            
            r = self.client.post("/api/generate", json=payload, timeout=120.0)
            
            print(f"?? HTTP Response Status: {r.status_code}")
            print(f"?? HTTP Response Body (first 500 chars): {r.text[:500]}")
            
            if r.status_code == 200:
                response_data = r.json()
                result = response_data.get('response', '')
                print(f"? HTTP Success! Got {len(result)} chars")
                return result
            else:
                print(f"? HTTP failed with status {r.status_code}")
                
        except httpx.TimeoutException as e:
            print(f"?? HTTP request timed out after {HTTP_TIMEOUT}s: {e}")
            logger.error(f"Ollama HTTP timeout: {e}")
        except httpx.ConnectError as e:
            print(f"?? Connection error - is Ollama running at {self.base_url}? {e}")
            logger.error(f"Ollama HTTP connection error: {e}")
        except Exception as e:
            print(f"? HTTP request exception: {type(e).__name__}: {e}")
            logger.debug("Ollama HTTP generate failed: %s", e)

        # CLI fallback: use `ollama run <model> '<prompt>'`
        print(f"?? Falling back to CLI: {OLLAMA_CLI}")
        try:
            cmd = [OLLAMA_CLI, "run", model, prompt]
            print(f"?? Running command: {' '.join(cmd[:3])}... (prompt truncated)")
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=120)
            text = out.decode("utf-8", errors="ignore").strip()
            print(f"? CLI Success! Got {len(text)} chars")
            return text
        except FileNotFoundError as e:
            error_msg = f"ERROR: Ollama CLI not found at '{OLLAMA_CLI}'. Install Ollama or set OLLAMA_BIN environment variable."
            print(f"? {error_msg}")
            logger.error(error_msg)
            return error_msg
        except subprocess.TimeoutExpired as e:
            error_msg = f"ERROR: CLI command timed out after 120s"
            print(f"?? {error_msg}")
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            print(f"? CLI failed: {error_msg}")
            logger.error("Ollama CLI generate failed: %s", e)
            return error_msg
