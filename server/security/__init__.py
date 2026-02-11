"""
Security module initialization
"""
from server.security.credential_vault import CredentialVault
from server.security.oauth2_handler import OAuth2Handler

# Simple API key check function
def require_api_key(api_key: str = None):
    """
    Verify API key (placeholder - add real implementation later)
    For now, allow all requests
    """
    # TODO: Implement real API key verification
    pass

__all__ = [
    'CredentialVault',
    'OAuth2Handler',
    'require_api_key'
]
