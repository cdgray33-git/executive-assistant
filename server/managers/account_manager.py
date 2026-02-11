"""
Account Manager - Multi-account orchestration and management
Location: server/managers/account_manager.py
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os

from server.security.credential_vault import CredentialVault
from server.security.oauth2_handler import OAuth2Handler
from server.connectors.yahoo_connector import YahooConnector
from server.connectors.gmail_connector import GmailConnector
from server.connectors.hotmail_connector import HotmailConnector
from server.connectors.comcast_connector import ComcastConnector
from server.connectors.apple_connector import AppleConnector

logger = logging.getLogger("account_manager")


class AccountManager:
    """Manages multiple email accounts and their connectors"""
    
    def __init__(self):
        self.vault = CredentialVault()
        self.active_connectors = {}  # Cache of active connections
        
    def add_account_oauth(self, account_id: str, provider: str, email: str,
                         client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Add an OAuth2-based account (Gmail, Hotmail)
        
        Args:
            account_id: Unique account identifier
            provider: 'gmail' or 'hotmail'
            email: Email address
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            
        Returns:
            Result dict
        """
        try:
            if provider not in ['gmail', 'hotmail']:
                return {
                    "status": "error",
                    "error": f"OAuth2 not supported for {provider}"
                }
            
            logger.info(f"Starting OAuth2 flow for {email} ({provider})")
            
            # Start OAuth2 flow
            oauth_handler = OAuth2Handler(provider, client_id, client_secret)
            success, tokens, error = oauth_handler.start_authorization_flow()
            
            if not success:
                return {
                    "status": "error",
                    "error": f"OAuth2 authorization failed: {error}"
                }
            
            # Store credentials in vault
            self.vault.store_credentials(
                account_id=account_id,
                provider=provider,
                email=email,
                credential_type="oauth_access_token",
                credential_value=tokens["access_token"],
                additional_data={
                    "client_id": client_id,
                    "client_secret": client_secret
                }
            )
            
            self.vault.store_credentials(
                account_id=account_id,
                provider=provider,
                email=email,
                credential_type="oauth_refresh_token",
                credential_value=tokens["refresh_token"]
            )
            
            # Update expiry
            self.vault.update_oauth_tokens(
                account_id,
                tokens["access_token"],
                tokens["refresh_token"],
                tokens["expires_in"]
            )
            
            logger.info(f"Account {account_id} added successfully")
            
            return {
                "status": "success",
                "account_id": account_id,
                "email": email,
                "provider": provider,
                "message": "Account authorized and credentials stored securely"
            }
            
        except Exception as e:
            logger.error(f"Error adding OAuth account: {e}")
            return {"status": "error", "error": str(e)}
    
    def add_account_password(self, account_id: str, provider: str, 
                           email: str, app_password: str) -> Dict[str, Any]:
        """
        Add a password-based account (Yahoo, Comcast, Apple)
        
        Args:
            account_id: Unique account identifier
            provider: 'yahoo', 'comcast', or 'apple'
            email: Email address
            app_password: App-specific password
            
        Returns:
            Result dict
        """
        try:
            if provider not in ['yahoo', 'comcast', 'apple']:
                return {
                    "status": "error",
                    "error": f"Password auth not supported for {provider}"
                }
            
            # Store credentials in vault
            self.vault.store_credentials(
                account_id=account_id,
                provider=provider,
                email=email,
                credential_type="app_password",
                credential_value=app_password
            )
            
            # Test connection
            connector = self._get_connector(account_id)
            success, message = connector.connect()
            connector.disconnect()
            
            if not success:
                # Remove credentials if connection failed
                self.vault.delete_credentials(account_id)
                return {
                    "status": "error",
                    "error": f"Connection test failed: {message}"
                }
            
            logger.info(f"Account {account_id} added successfully")
            
            return {
                "status": "success",
                "account_id": account_id,
                "email": email,
                "provider": provider,
                "message": "Account added and verified"
            }
            
        except Exception as e:
            logger.error(f"Error adding password account: {e}")
            return {"status": "error", "error": str(e)}
    
    def remove_account(self, account_id: str) -> Dict[str, Any]:
        """
        Remove an account
        
        Args:
            account_id: Account identifier
            
        Returns:
            Result dict
        """
        try:
            # Close active connection if exists
            if account_id in self.active_connectors:
                self.active_connectors[account_id].disconnect()
                del self.active_connectors[account_id]
            
            # Delete credentials
            success = self.vault.delete_credentials(account_id)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Account {account_id} removed"
                }
            else:
                return {
                    "status": "error",
                    "error": "Failed to remove account"
                }
                
        except Exception as e:
            logger.error(f"Error removing account: {e}")
            return {"status": "error", "error": str(e)}
    
    def list_accounts(self) -> Dict[str, Any]:
        """
        List all configured accounts
        
        Returns:
            Dict with account list
        """
        try:
            accounts = self.vault.list_accounts()
            
            account_list = []
            for account_id, metadata in accounts.items():
                account_list.append({
                    "account_id": account_id,
                    "email": metadata.get("email"),
                    "provider": metadata.get("provider"),
                    "credential_types": metadata.get("credential_types", [])
                })
            
            return {
                "status": "success",
                "accounts": account_list,
                "count": len(account_list)
            }
            
        except Exception as e:
            logger.error(f"Error listing accounts: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_connector(self, account_id: str):
        """
        Get appropriate connector for account
        
        Args:
            account_id: Account identifier
            
        Returns:
            Connector instance
        """
        metadata = self.vault.get_account_metadata(account_id)
        if not metadata:
            raise ValueError(f"Account {account_id} not found")
        
        provider = metadata.get("provider")
        
        if provider == "yahoo":
            email = metadata.get("email")
            app_password = self.vault.get_credentials(account_id, "app_password")
            return YahooConnector(email_address=email, app_password=app_password)
        elif provider == "gmail":
            return GmailConnector(account_id=account_id)
        elif provider == "hotmail":
            return HotmailConnector(account_id=account_id)
        elif provider == "comcast":
            return ComcastConnector(account_id=account_id)
        elif provider == "apple":
            return AppleConnector(account_id=account_id)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def get_connector(self, account_id: str, cache: bool = True):
        """
        Get connector with optional caching
        
        Args:
            account_id: Account identifier
            cache: If True, reuse cached connection
            
        Returns:
            Connector instance
        """
        if cache and account_id in self.active_connectors:
            return self.active_connectors[account_id]
        
        connector = self._get_connector(account_id)
        
        if cache:
            self.active_connectors[account_id] = connector
        
        return connector
    
    def test_all_accounts(self) -> Dict[str, Any]:
        """
        Test connectivity for all accounts
        
        Returns:
            Test results
        """
        results = {
            "status": "success",
            "accounts": [],
            "total": 0,
            "successful": 0,
            "failed": 0
        }
        
        accounts = self.vault.list_accounts()
        results["total"] = len(accounts)
        
        for account_id, metadata in accounts.items():
            try:
                connector = self._get_connector(account_id)
                success, message = connector.connect()
                
                if success:
                    results["successful"] += 1
                    # Get stats
                    stats = connector.get_mailbox_stats()
                    connector.disconnect()
                    
                    results["accounts"].append({
                        "account_id": account_id,
                        "email": metadata.get("email"),
                        "provider": metadata.get("provider"),
                        "status": "connected",
                        "stats": stats
                    })
                else:
                    results["failed"] += 1
                    results["accounts"].append({
                        "account_id": account_id,
                        "email": metadata.get("email"),
                        "provider": metadata.get("provider"),
                        "status": "failed",
                        "error": message
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["accounts"].append({
                    "account_id": account_id,
                    "email": metadata.get("email"),
                    "provider": metadata.get("provider"),
                    "status": "error",
                    "error": str(e)
                })
        
        return results