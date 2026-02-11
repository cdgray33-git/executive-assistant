"""
Security module initialization
"""
from server.security.credential_vault import CredentialVault
from server.security.oauth2_handler import OAuth2Handler

# Import require_api_key from security.py (parent level)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from security import require_api_key

__all__ = [
    'CredentialVault',
    'OAuth2Handler',
    'require_api_key'
]
