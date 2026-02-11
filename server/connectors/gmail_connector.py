"""
Gmail Connector - OAuth2 authentication with Gmail API
Location: server/connectors/gmail_connector.py
"""
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import httpx

from server.security.credential_vault import CredentialVault
from server.security.oauth2_handler import OAuth2Handler

logger = logging.getLogger("gmail_connector")


class GmailConnector:
    """Gmail connector using OAuth2 and Gmail API"""
    
    def __init__(self, account_id: str):
        """
        Initialize Gmail connector
        
        Args:
            account_id: Account identifier for credential lookup
        """
        self.account_id = account_id
        self.vault = CredentialVault()
        self.access_token = None
        self.email_address = None
        self.client = httpx.Client(timeout=30.0)
        
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to Gmail using OAuth2
        
        Returns:
            (success, message)
        """
        try:
            # Get account metadata
            metadata = self.vault.get_account_metadata(self.account_id)
            if not metadata:
                return False, f"Account {self.account_id} not found"
            
            if metadata.get("provider") != "gmail":
                return False, "Account is not a Gmail account"
            
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
                logger.info(f"Connected to Gmail: {profile.get('emailAddress')}")
                return True, f"Connected as {profile.get('emailAddress')}"
            else:
                return False, "Failed to verify Gmail connection"
            
        except Exception as e:
            logger.error(f"Gmail connection error: {e}")
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
            
            oauth_handler = OAuth2Handler("gmail", client_id, client_secret)
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
                "https://gmail.googleapis.com/gmail/v1/users/me/profile",
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
            # List messages
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {
                "maxResults": min(count, 500),  # API limit
                "q": "in:inbox"
            }
            
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"List messages failed: {response.status_code}")
                return []
            
            message_list = response.json().get("messages", [])
            
            # Get full message details
            emails = []
            for msg in message_list[:count]:
                email_data = self._get_message_details(msg["id"])
                if email_data:
                    emails.append(email_data)
            
            # Sort by date
            emails.sort(key=lambda e: e.get("date", ""), reverse=not oldest_first)
            
            return emails
            
        except Exception as e:
            logger.error(f"Preview emails error: {e}")
            return []
    
    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed message information"""
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
            params = {"format": "full"}
            
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                params=params
            )
            
            if response.status_code != 200:
                return None
            
            msg = response.json()
            
            # Parse headers
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            
            # Get body
            body = self._extract_body(msg.get("payload", {}))
            
            return {
                "id": message_id,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "snippet": msg.get("snippet", ""),
                "labels": msg.get("labelIds", [])
            }
            
        except Exception as e:
            logger.error(f"Get message details error: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        try:
            # Check for direct body
            if "body" in payload and payload["body"].get("data"):
                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
            
            # Check parts
            if "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        if part.get("body", {}).get("data"):
                            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                    
                    # Recursive for nested parts
                    if "parts" in part:
                        body = self._extract_body(part)
                        if body:
                            return body
            
            return ""
            
        except Exception as e:
            logger.error(f"Body extraction error: {e}")
            return ""
    
    def delete_emails(self, email_ids: List[str], permanent: bool = False) -> Dict[str, Any]:
        """
        Delete emails
        
        Args:
            email_ids: List of message IDs
            permanent: If True, permanently delete; if False, move to trash
            
        Returns:
            Result dict
        """
        try:
            deleted = []
            errors = []
            
            for msg_id in email_ids:
                try:
                    if permanent:
                        # Permanent delete
                        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                        response = self.client.delete(
                            url,
                            headers={"Authorization": f"Bearer {self.access_token}"}
                        )
                    else:
                        # Move to trash
                        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/trash"
                        response = self.client.post(
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
            # Create MIME message
            message = MIMEMultipart()
            message["From"] = self.email_address
            message["To"] = to
            message["Subject"] = subject
            
            if cc:
                message["Cc"] = ", ".join(cc)
            if bcc:
                message["Bcc"] = ", ".join(bcc)
            
            message.attach(MIMEText(body, "plain"))
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            # Send via Gmail API
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            response = self.client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"raw": raw_message}
            )
            
            if response.status_code == 200:
                msg_data = response.json()
                return {
                    "success": True,
                    "message_id": msg_data.get("id"),
                    "thread_id": msg_data.get("threadId")
                }
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
            # Get profile with message counts
            profile = self._get_profile()
            
            if not profile:
                return {}
            
            return {
                "total_messages": profile.get("messagesTotal", 0),
                "threads_total": profile.get("threadsTotal", 0),
                "history_id": profile.get("historyId", "")
            }
            
        except Exception as e:
            logger.error(f"Get mailbox stats error: {e}")
            return {}
    
    def move_to_folder(self, email_ids: List[str], folder_label: str) -> Dict[str, Any]:
        """
        Move emails to a folder (Gmail label)
        
        Args:
            email_ids: List of message IDs
            folder_label: Label name
            
        Returns:
            Result dict
        """
        try:
            # Get or create label
            label_id = self._get_or_create_label(folder_label)
            if not label_id:
                return {"success": False, "error": "Failed to get/create label"}
            
            moved = []
            errors = []
            
            for msg_id in email_ids:
                try:
                    url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}/modify"
                    response = self.client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        json={
                            "addLabelIds": [label_id],
                            "removeLabelIds": ["INBOX"]
                        }
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
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """Get label ID or create if doesn't exist"""
        try:
            # List existing labels
            url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
            response = self.client.get(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            if response.status_code == 200:
                labels = response.json().get("labels", [])
                for label in labels:
                    if label["name"] == label_name:
                        return label["id"]
            
            # Create label
            response = self.client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show"
                }
            )
            
            if response.status_code == 200:
                return response.json().get("id")
            
            return None
            
        except Exception as e:
            logger.error(f"Get/create label error: {e}")
            return None