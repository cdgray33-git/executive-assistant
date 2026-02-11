"""
Credential Vault - Secure credential storage using macOS Keychain
Location: server/security/credential_vault.py
"""
import logging
import keyring
import json
from typing import Dict, Any, Optional
from pathlib import Path
import os
from cryptography.fernet import Fernet

logger = logging.getLogger("credential_vault")

# Service name for keychain
KEYCHAIN_SERVICE = "ExecutiveAssistant"

# Local metadata storage
DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
ACCOUNTS_METADATA = DATA_DIR / "config" / "accounts.json"


class CredentialVault:
    """Secure credential storage using macOS Keychain"""
    
    def __init__(self):
        self.accounts_metadata = self._load_accounts_metadata()
        
    def _load_accounts_metadata(self) -> Dict:
        """Load account metadata (NOT credentials)"""
        try:
            if ACCOUNTS_METADATA.exists():
                with open(ACCOUNTS_METADATA, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading accounts metadata: {e}")
            return {}
    
    def _save_accounts_metadata(self):
        """Save account metadata"""
        try:
            ACCOUNTS_METADATA.parent.mkdir(parents=True, exist_ok=True)
            with open(ACCOUNTS_METADATA, 'w') as f:
                json.dump(self.accounts_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving accounts metadata: {e}")
    
    def store_credentials(self, account_id: str, provider: str, email: str,
                         credential_type: str, credential_value: str,
                         additional_data: Optional[Dict] = None) -> bool:
        """
        Store credentials securely in Keychain
        
        Args:
            account_id: Unique account identifier
            provider: Email provider (yahoo, gmail, hotmail, etc.)
            email: Email address
            credential_type: Type (app_password, oauth_token, refresh_token)
            credential_value: The actual credential
            additional_data: Optional additional encrypted data
            
        Returns:
            Success boolean
        """
        try:
            # Store credential in Keychain
            keychain_key = f"{account_id}_{credential_type}"
            keyring.set_password(KEYCHAIN_SERVICE, keychain_key, credential_value)
            
            # Store metadata (NOT credentials)
            if account_id not in self.accounts_metadata:
                self.accounts_metadata[account_id] = {
                    "provider": provider,
                    "email": email,
                    "credential_types": [],
                    "created_at": None,
                    "updated_at": None
                }
            
            if credential_type not in self.accounts_metadata[account_id]["credential_types"]:
                self.accounts_metadata[account_id]["credential_types"].append(credential_type)
            
            # Store additional data if provided
            if additional_data:
                self.accounts_metadata[account_id]["additional_data"] = additional_data
            
            self.accounts_metadata[account_id]["updated_at"] = None  # Will be set by caller
            
            self._save_accounts_metadata()
            
            logger.info(f"Stored {credential_type} for {account_id} in Keychain")
            return True
            
        except Exception as e:
            logger.error(f"Error storing credentials: {e}")
            return False
    
    def get_credentials(self, account_id: str, credential_type: str) -> Optional[str]:
        """
        Retrieve credentials from Keychain
        
        Args:
            account_id: Account identifier
            credential_type: Type of credential to retrieve
            
        Returns:
            Credential value or None
        """
        try:
            keychain_key = f"{account_id}_{credential_type}"
            credential = keyring.get_password(KEYCHAIN_SERVICE, keychain_key)
            
            if credential:
                logger.info(f"Retrieved {credential_type} for {account_id}")
            else:
                logger.warning(f"No {credential_type} found for {account_id}")
            
            return credential
            
        except Exception as e:
            logger.error(f"Error retrieving credentials: {e}")
            return None
    
    def delete_credentials(self, account_id: str) -> bool:
        """
        Delete all credentials for an account
        
        Args:
            account_id: Account identifier
            
        Returns:
            Success boolean
        """
        try:
            if account_id not in self.accounts_metadata:
                logger.warning(f"Account {account_id} not found")
                return False
            
            # Delete all credential types
            credential_types = self.accounts_metadata[account_id].get("credential_types", [])
            for cred_type in credential_types:
                keychain_key = f"{account_id}_{cred_type}"
                try:
                    keyring.delete_password(KEYCHAIN_SERVICE, keychain_key)
                except Exception as e:
                    logger.warning(f"Could not delete {cred_type}: {e}")
            
            # Remove metadata
            del self.accounts_metadata[account_id]
            self._save_accounts_metadata()
            
            logger.info(f"Deleted credentials for {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting credentials: {e}")
            return False
    
    def list_accounts(self) -> Dict:
        """List all accounts (metadata only, no credentials)"""
        return self.accounts_metadata
    
    def get_account_metadata(self, account_id: str) -> Optional[Dict]:
        """Get metadata for a specific account"""
        return self.accounts_metadata.get(account_id)
    
    def update_oauth_tokens(self, account_id: str, access_token: str, 
                           refresh_token: str, expires_in: int) -> bool:
        """
        Update OAuth tokens for an account
        
        Args:
            account_id: Account identifier
            access_token: New access token
            refresh_token: New refresh token
            expires_in: Token expiry in seconds
            
        Returns:
            Success boolean
        """
        try:
            from datetime import datetime, timedelta
            
            # Store tokens in Keychain
            self.store_credentials(account_id, "", "", "oauth_access_token", access_token)
            self.store_credentials(account_id, "", "", "oauth_refresh_token", refresh_token)
            
            # Update expiry in metadata
            if account_id in self.accounts_metadata:
                expiry = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
                self.accounts_metadata[account_id]["token_expiry"] = expiry
                self._save_accounts_metadata()
            
            logger.info(f"Updated OAuth tokens for {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating OAuth tokens: {e}")
            return False
    
    def is_token_expired(self, account_id: str) -> bool:
        """Check if OAuth token is expired"""
        try:
            from datetime import datetime
            
            if account_id not in self.accounts_metadata:
                return True
            
            expiry_str = self.accounts_metadata[account_id].get("token_expiry")
            if not expiry_str:
                return True
            
            expiry = datetime.fromisoformat(expiry_str)
            return datetime.now() >= expiry
            
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True