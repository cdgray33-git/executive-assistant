"""
OAuth2 Handler - OAuth2 flow for Gmail and Hotmail
Location: server/security/oauth2_handler.py
"""
import logging
import webbrowser
import http.server
import socketserver
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from threading import Thread
import time

from authlib.integrations.requests_client import OAuth2Session
import requests

logger = logging.getLogger("oauth2_handler")

# OAuth2 configurations
GMAIL_CONFIG = {
    "client_id": None,  # Set during account setup
    "client_secret": None,
    "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "scopes": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify"
    ],
    "redirect_uri": "http://localhost:8888/oauth2callback"
}

HOTMAIL_CONFIG = {
    "client_id": None,  # Set during account setup
    "client_secret": None,
    "auth_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "token_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "scopes": [
        "https://outlook.office.com/Mail.Read",
        "https://outlook.office.com/Mail.Send",
        "offline_access"
    ],
    "redirect_uri": "http://localhost:8888/oauth2callback"
}


class OAuth2CallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler to capture OAuth2 callback"""
    
    auth_code = None
    auth_error = None
    
    def do_GET(self):
        """Handle OAuth2 callback"""
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        
        if 'code' in query:
            OAuth2CallbackHandler.auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html><body>
            <h1>Authorization Successful!</h1>
            <p>You can close this window and return to the application.</p>
            </body></html>
            """)
        elif 'error' in query:
            OAuth2CallbackHandler.auth_error = query['error'][0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
            <html><body>
            <h1>Authorization Failed</h1>
            <p>Error: {query['error'][0]}</p>
            </body></html>
            """.encode())
        
        # Suppress log messages
        def log_message(self, format, *args):
            pass


class OAuth2Handler:
    """Handles OAuth2 authentication flow"""
    
    def __init__(self, provider: str, client_id: str, client_secret: str):
        """
        Initialize OAuth2 handler
        
        Args:
            provider: 'gmail' or 'hotmail'
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.provider = provider.lower()
        
        if self.provider == "gmail":
            self.config = GMAIL_CONFIG.copy()
        elif self.provider == "hotmail":
            self.config = HOTMAIL_CONFIG.copy()
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        self.config["client_id"] = client_id
        self.config["client_secret"] = client_secret
        
        self.session = None
    
    def start_authorization_flow(self) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Start OAuth2 authorization flow
        
        Returns:
            (success, tokens_dict, error_message)
        """
        try:
            # Create OAuth2 session
            self.session = OAuth2Session(
                client_id=self.config["client_id"],
                client_secret=self.config["client_secret"],
                scope=self.config["scopes"],
                redirect_uri=self.config["redirect_uri"]
            )
            
            # Generate authorization URL
            authorization_url, state = self.session.create_authorization_url(
                self.config["auth_uri"]
            )
            
            logger.info(f"Starting OAuth2 flow for {self.provider}")
            
            # Start local callback server
            OAuth2CallbackHandler.auth_code = None
            OAuth2CallbackHandler.auth_error = None
            
            server = socketserver.TCPServer(("localhost", 8888), OAuth2CallbackHandler)
            server_thread = Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Open browser for authorization
            logger.info("Opening browser for authorization...")
            webbrowser.open(authorization_url)
            
            # Wait for callback (timeout 5 minutes)
            timeout = 300
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if OAuth2CallbackHandler.auth_code:
                    # Success - exchange code for tokens
                    server.shutdown()
                    
                    tokens = self._exchange_code_for_tokens(OAuth2CallbackHandler.auth_code)
                    if tokens:
                        return True, tokens, None
                    else:
                        return False, None, "Failed to exchange authorization code for tokens"
                
                elif OAuth2CallbackHandler.auth_error:
                    server.shutdown()
                    return False, None, f"Authorization error: {OAuth2CallbackHandler.auth_error}"
                
                time.sleep(0.5)
            
            # Timeout
            server.shutdown()
            return False, None, "Authorization timeout - user did not complete flow"
            
        except Exception as e:
            logger.error(f"OAuth2 flow error: {e}")
            return False, None, str(e)
    
    def _exchange_code_for_tokens(self, code: str) -> Optional[Dict]:
        """Exchange authorization code for access/refresh tokens"""
        try:
            token_response = self.session.fetch_token(
                self.config["token_uri"],
                code=code
            )
            
            return {
                "access_token": token_response.get("access_token"),
                "refresh_token": token_response.get("refresh_token"),
                "expires_in": token_response.get("expires_in", 3600),
                "token_type": token_response.get("token_type", "Bearer")
            }
            
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens dict or None
        """
        try:
            data = {
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            response = requests.post(self.config["token_uri"], data=data)
            response.raise_for_status()
            
            token_data = response.json()
            
            return {
                "access_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token", refresh_token),  # May not return new refresh token
                "expires_in": token_data.get("expires_in", 3600),
                "token_type": token_data.get("token_type", "Bearer")
            }
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke an access or refresh token"""
        try:
            if self.provider == "gmail":
                revoke_url = "https://oauth2.googleapis.com/revoke"
            elif self.provider == "hotmail":
                # Microsoft doesn't have a standard revoke endpoint
                logger.warning("Hotmail token revocation not supported")
                return True
            else:
                return False
            
            response = requests.post(revoke_url, data={"token": token})
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False