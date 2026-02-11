"""
Hotmail/Outlook Connector - OAuth2 with Microsoft Graph API
Location: server/connectors/hotmail_connector.py
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import base64

import httpx

from server.security.credential_vault import CredentialVault
from server.security.oauth2_handler import OAuth2Handler

logger = logging.getLogger("hotmail_connector")


class HotmailConnector:
    """Hotmail/Outlook connector using OAuth2 and Microsoft Graph API"""
    
    def __init__(self, account_id: str):
        """
        Initialize Hotmail connector
        
        Args:
            account_id: Account identifier for credential lookup
        """
        self.account_id = account_id
        self.vault = CredentialVault()
        self.access_token = None
        self.email_address = None
        self.client = httpx.Client(timeout=30.0)
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to Hotmail using OAuth2
        
        Returns:
            (success, message)
        """
        try:
            # Get account metadata
            metadata = self.vault.get_account_metadata(self.account_id)
            if not metadata:
                return False, f"Account {self.account_id} not found"
            
            if metadata.get("provider") != "hotmail":
                return False, "Account is not a Hotmail/Outlook account"
            
            self.email_address = metadata.get("email")
            
            # Check if token is expired
            if self.vault.is_token_expired(self.account_id):
                logger.info("Access token expired, refreshing...")
                success = self._refresh_token()
                if not success:
                    return False, "Failed to refresh access token"
            
            # Get access token
            self.access_token = self.vault.get_credentials(self.account_id, "oauth_access_token")
            if not self.access_token:
                return False, "No access token found - please authorize account"
            
            # Test connection
            profile = self._get_profile()
            if profile:
                logger.info(f"Connected to Hotmail: {profile.get('mail')}")
                return True, f"Connected as {profile.get('mail')}"
            else:
                return False, "Failed to verify Hotmail connection"
            
        except Exception as e:
            logger.error(f"Hotmail connection error: {e}")
            return False, str(e)
    
    def disconnect(self):
        """Close connection"""
        self.client.close()
    
    def _refresh_token(self) -> bool:
        """Refresh OAuth2 access token"""
        try:
            refresh_token = self.vault.get_credentials(self.account_id, "oauth_refresh_token")
            if not refresh_token:
                return False
            
            metadata = self.vault.get_account_metadata(self.account_id)
            client_id = metadata.get("additional_data", {}).get("client_id")
            client_secret = metadata.get("additional_data", {}).get("client_secret")
            
            if not client_id or not client_secret:
                logger.error("Missing OAuth2 credentials")
                return False
            
            oauth_handler = OAuth2Handler("hotmail", client_id, client_secret)
            new_tokens = oauth_handler.refresh_access_token(refresh_token)
            
            if new_tokens:
                self.vault.update_oauth_tokens(
                    self.account_id,
                    new_tokens["access_token"],
                    new_tokens["refresh_token"],
                    new_tokens["expires_in"]
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    def _get_profile(self) -> Optional[Dict]:
        """Get user profile to verify connection"""
        try:
            response = self.client.get(
                f"{self.graph_endpoint}/me",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Profile request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Profile request error: {e}")
            return None
    
    def preview_emails(self, count: int = 100, oldest_first: bool = False) -> List[Dict]:
        """
        Preview emails from inbox
        
        Args:
            count: Number of emails to retrieve
            oldest_first: If True, get oldest first; if False, get newest first
            
        Returns:
            List of email dicts
        """
        try:
            order_by = "receivedDateTime asc" if oldest_first else "receivedDateTime desc"
            
            url = f"{self.graph_endpoint}/me/mailFolders/inbox/messages"
            params = {
                "$top": min(count, 999),  # API limit
                "$orderby": order_by,
                "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview,body"
            }
            
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"List messages failed: {response.status_code}")
                return []
            
            messages = response.json().get("value", [])
            
            # Convert to standard format
            emails = []
            for msg in messages:
                emails.append({
                    "id": msg.get("id"),
                    "from": msg.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "to": ", ".join([r.get("emailAddress", {}).get("address", "") 
                                    for r in msg.get("toRecipients", [])]),
                    "subject": msg.get("subject", ""),
                    "date": msg.get("receivedDateTime", ""),
                    "body": msg.get("body", {}).get("content", ""),
                    "snippet": msg.get("bodyPreview", "")
                })
            
            return emails
            
        except Exception as e:
            logger.error(f"Preview emails error: {e}")
            return []
    
    def delete_emails(self, email_ids: List[str], permanent: bool = False) -> Dict[str, Any]:
        """
        Delete emails
        
        Args:
            email_ids: List of message IDs
            permanent: If True, permanently delete; if False, move to deleted items
            
        Returns:
            Result dict
        """
        try:
            deleted = []
            errors = []
            
            for msg_id in email_ids:
                try:
                    url = f"{self.graph_endpoint}/me/messages/{msg_id}"
                    response = self.client.delete(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"}
                    )
                    
                    if response.status_code in [200, 204]:
                        deleted.append(msg_id)
                    else:
                        errors.append({"id": msg_id, "error": f"Status {response.status_code}"})
                        
                except Exception as e:
                    errors.append({"id": msg_id, "error": str(e)})
            
            return {
                "success": True,
                "deleted_count": len(deleted),
                "deleted_ids": deleted,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Delete emails error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_message(self, to: str, subject: str, body: str,
                    cc: Optional[List[str]] = None, bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to: Recipient email
            subject: Email subject  
            body: Email body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            Result dict
        """
        try:
            # Build message
            message = {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {"emailAddress": {"address": to}}
                ]
            }
            
            if cc:
                message["ccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in cc
                ]
            
            if bcc:
                message["bccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in bcc
                ]
            
            # Send via Graph API
            url = f"{self.graph_endpoint}/me/sendMail"
            response = self.client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"message": message}
            )
            
            if response.status_code in [200, 202]:
                return {"success": True}
            else:
                return {
                    "success": False,
                    "error": f"Send failed: {response.status_code}"
                }
            
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_mailbox_stats(self) -> Dict[str, Any]:
        """Get mailbox statistics"""
        try:
            # Get folder info
            url = f"{self.graph_endpoint}/me/mailFolders/inbox"
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code != 200:
                return {}
            
            folder = response.json()
            
            return {
                "total_messages": folder.get("totalItemCount", 0),
                "unread_messages": folder.get("unreadItemCount", 0)
            }
            
        except Exception as e:
            logger.error(f"Get mailbox stats error: {e}")
            return {}
    
    def move_to_folder(self, email_ids: List[str], folder_name: str) -> Dict[str, Any]:
        """
        Move emails to a folder
        
        Args:
            email_ids: List of message IDs
            folder_name: Folder name
            
        Returns:
            Result dict
        """
        try:
            # Get or create folder
            folder_id = self._get_or_create_folder(folder_name)
            if not folder_id:
                return {"success": False, "error": "Failed to get/create folder"}
            
            moved = []
            errors = []
            
            for msg_id in email_ids:
                try:
                    url = f"{self.graph_endpoint}/me/messages/{msg_id}/move"
                    response = self.client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        json={"destinationId": folder_id}
                    )
                    
                    if response.status_code == 200:
                        moved.append(msg_id)
                    else:
                        errors.append({"id": msg_id, "error": f"Status {response.status_code}"})
                        
                except Exception as e:
                    errors.append({"id": msg_id, "error": str(e)})
            
            return {
                "success": True,
                "moved_count": len(moved),
                "moved_ids": moved,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Move to folder error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_or_create_folder(self, folder_name: str) -> Optional[str]:
        """Get folder ID or create if doesn't exist"""
        try:
            # List existing folders
            url = f"{self.graph_endpoint}/me/mailFolders"
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                folders = response.json().get("value", [])
                for folder in folders:
                    if folder["displayName"] == folder_name:
                        return folder["id"]
            
            # Create folder
            response = self.client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"displayName": folder_name}
            )
            
            if response.status_code in [200, 201]:
                return response.json().get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"Get/create folder error: {e}")
            return None