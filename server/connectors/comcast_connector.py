"""
Comcast Connector - IMAP/SMTP authentication
Location: server/connectors/comcast_connector.py
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import message_from_bytes
from datetime import datetime

from imapclient import IMAPClient

from server.security.credential_vault import CredentialVault

logger = logging.getLogger("comcast_connector")


class ComcastConnector:
    """Comcast/Xfinity email connector using IMAP/SMTP"""
    
    # Comcast server settings
    IMAP_SERVER = "imap.comcast.net"
    IMAP_PORT = 993
    SMTP_SERVER = "smtp.comcast.net"
    SMTP_PORT = 587
    
    def __init__(self, account_id: str):
        """
        Initialize Comcast connector
        
        Args:
            account_id: Account identifier for credential lookup
        """
        self.account_id = account_id
        self.vault = CredentialVault()
        self.imap = None
        self.email_address = None
        self.app_password = None
        
    def connect(self) -> Tuple[bool, str]:
        """
        Connect to Comcast email using IMAP
        
        Returns:
            (success, message)
        """
        try:
            # Get account metadata
            metadata = self.vault.get_account_metadata(self.account_id)
            if not metadata:
                return False, f"Account {self.account_id} not found"
            
            if metadata.get("provider") != "comcast":
                return False, "Account is not a Comcast account"
            
            self.email_address = metadata.get("email")
            
            # Get app password from vault
            self.app_password = self.vault.get_credentials(self.account_id, "app_password")
            if not self.app_password:
                return False, "No app password found for account"
            
            # Connect to IMAP
            self.imap = IMAPClient(self.IMAP_SERVER, port=self.IMAP_PORT, ssl=True)
            self.imap.login(self.email_address, self.app_password)
            
            logger.info(f"Connected to Comcast: {self.email_address}")
            return True, f"Connected to {self.email_address}"
            
        except Exception as e:
            logger.error(f"Comcast connection error: {e}")
            return False, str(e)
    
    def disconnect(self):
        """Close IMAP connection"""
        try:
            if self.imap:
                self.imap.logout()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
    
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
            self.imap.select_folder('INBOX', readonly=True)
            
            # Search for all messages
            messages = self.imap.search(['ALL'])
            
            if not messages:
                return []
            
            # Sort and limit
            if oldest_first:
                message_ids = sorted(messages)[:count]
            else:
                message_ids = sorted(messages, reverse=True)[:count]
            
            # Fetch email data
            emails = []
            fetch_data = self.imap.fetch(message_ids, ['ENVELOPE', 'BODY.PEEK[]', 'RFC822.SIZE'])
            
            for msg_id, data in fetch_data.items():
                try:
                    envelope = data[b'ENVELOPE']
                    raw_email = data[b'BODY[]']
                    
                    # Parse email
                    msg = message_from_bytes(raw_email)
                    
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    emails.append({
                        "id": str(msg_id),
                        "from": envelope.from_[0].mailbox.decode() + "@" + envelope.from_[0].host.decode() if envelope.from_ else "",
                        "to": envelope.to[0].mailbox.decode() + "@" + envelope.to[0].host.decode() if envelope.to else "",
                        "subject": envelope.subject.decode() if envelope.subject else "",
                        "date": str(envelope.date),
                        "body": body[:1000],  # Limit body preview
                        "snippet": body[:200]
                    })
                    
                except Exception as e:
                    logger.error(f"Error parsing message {msg_id}: {e}")
                    continue
            
            return emails
            
        except Exception as e:
            logger.error(f"Preview emails error: {e}")
            return []
    
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
            self.imap.select_folder('INBOX')
            
            # Convert string IDs to integers
            msg_ids = [int(msg_id) for msg_id in email_ids]
            
            deleted = []
            errors = []
            
            for msg_id in msg_ids:
                try:
                    if permanent:
                        # Mark for deletion and expunge
                        self.imap.delete_messages([msg_id])
                        self.imap.expunge()
                    else:
                        # Move to Trash
                        self.imap.move([msg_id], 'Trash')
                    
                    deleted.append(str(msg_id))
                    
                except Exception as e:
                    errors.append({"id": str(msg_id), "error": str(e)})
            
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
        Send an email via SMTP
        
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
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_address
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP
            smtp = smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT)
            smtp.starttls()
            smtp.login(self.email_address, self.app_password)
            
            # Send
            recipients = [to]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            smtp.send_message(msg, self.email_address, recipients)
            smtp.quit()
            
            logger.info(f"Email sent to {to}")
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_mailbox_stats(self) -> Dict[str, Any]:
        """Get mailbox statistics"""
        try:
            self.imap.select_folder('INBOX', readonly=True)
            
            # Get total messages
            total = len(self.imap.search(['ALL']))
            
            # Get unread messages
            unread = len(self.imap.search(['UNSEEN']))
            
            return {
                "total_messages": total,
                "unread_messages": unread
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
            self.imap.select_folder('INBOX')
            
            # Ensure folder exists
            if not self.imap.folder_exists(folder_name):
                self.imap.create_folder(folder_name)
            
            # Convert string IDs to integers
            msg_ids = [int(msg_id) for msg_id in email_ids]
            
            moved = []
            errors = []
            
            for msg_id in msg_ids:
                try:
                    self.imap.move([msg_id], folder_name)
                    moved.append(str(msg_id))
                except Exception as e:
                    errors.append({"id": str(msg_id), "error": str(e)})
            
            return {
                "success": True,
                "moved_count": len(moved),
                "moved_ids": moved,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Move to folder error: {e}")
            return {"success": False, "error": str(e)}