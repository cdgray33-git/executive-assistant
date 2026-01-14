"""
Security helpers: API key retrieval using environment variable, macOS Keychain via keyring,
and a config.env fallback in ~/ExecutiveAssistant/config.env.

Provide require_api_key(x_api_key) which raises fastapi.HTTPException(401) on mismatch.
"""
import os
from typing import Optional

try:
    import keyring
except Exception:
    keyring = None  # keyring is optional at import time; requirements.txt will include it

from fastapi import HTTPException

SERVICE_NAME = "ExecutiveAssistant"
KEYCHAIN_USERNAME = "api_key"  # service/account used with keyring.get_password


def _get_from_env() -> Optional[str]:
    v = os.environ.get("API_KEY")
    if v:
        return v.strip()
    return None


def _get_from_keyring() -> Optional[str]:
    if keyring is None:
        return None
    try:
        val = keyring.get_password(SERVICE_NAME, KEYCHAIN_USERNAME)
        return val
    except Exception:
        return None


def _get_from_config() -> Optional[str]:
    cfg = os.path.expanduser("~/ExecutiveAssistant/config.env")
    if not os.path.exists(cfg):
        return None
    try:
        with open(cfg, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "API_KEY":
                    return v.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def get_expected_api_key() -> Optional[str]:
    """Return expected API key from env, keychain, or config (first found)."""
    for getter in (_get_from_env, _get_from_keyring, _get_from_config):
        try:
            val = getter()
            if val:
                return val
        except Exception:
            continue
    return None


def require_api_key(x_api_key: Optional[str]):
    """
    Raises HTTPException(401) if a key is expected and mismatched.
    If no key is configured (no env, no keychain, no config) the function allows requests
    (useful in early test/dev). In production, set an API key in Keychain or env.
    """
    expected = get_expected_api_key()
    if not expected:
        # No key configured — allow but caller should log/monitor this state
        return
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key header (X-API-Key)")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")
