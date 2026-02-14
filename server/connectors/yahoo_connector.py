"""
Yahoo IMAP Connector - Real Implementation
Connects to Yahoo Mail, previews emails, and deletes spam
"""
import imaplib
import email
from email.header import decode_header
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger("yahoo_connector")

class YahooConnector:
    """Real Yahoo IMAP connector for spam cleanup"""
    
    def __init__(self, email_address: str, app_password: str):
        self.email = email_address
        self.password = app_password
        self.imap = None
        
    def connect(self) -> Tuple[bool, str]:
        """Connect to Yahoo IMAP"""
        try:
            self.imap = imaplib.IMAP4_SSL("imap.mail.yahoo.com", 993)
            self.imap.login(self.email, self.password)
            logger.info(f"✅ Connected to Yahoo for {self.email}")
            return True, "Connected successfully"
        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP login failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Connection error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def disconnect(self):
        """Safely close connection"""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
    
    def get_mailbox_stats(self) -> Dict:
        """Get inbox statistics"""
        if not self.imap:
            return {"error": "Not connected"}
        
        try:
            status, data = self.imap.select("INBOX")
            if status != "OK":
                return {"error": f"Failed to select INBOX: {data}"}
            
            total_messages = int(data[0].decode())
            
            # Count unread
            status, unread = self.imap.search(None, "UNSEEN")
            unread_count = len(unread[0].split()) if unread[0] else 0
            
            return {
                "total_messages": total_messages,
                "unread_count": unread_count,
                "status": "connected"
            }
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}
    
    def preview_emails(self, count: int = 100, folder: str = "INBOX", 
                       oldest_first: bool = True) -> List[Dict]:
        """
        Preview emails for categorization
        Returns: [{id, from, subject, date, size_kb}]
        """
        if not self.imap:
            return []
        
        try:
            status, data = self.imap.select(folder)
            if status != "OK":
                logger.error(f"Failed to select {folder}")
                return []
            
            # Search all messages
            status, msg_ids = self.imap.search(None, "ALL")
            if status != "OK" or not msg_ids[0]:
                return []
            
            all_ids = msg_ids[0].split()
            
            # Get oldest or newest
            if oldest_first:
                target_ids = all_ids[:count]
            else:
                target_ids = all_ids[-count:]
            
            emails = []
            for msg_id in target_ids:
                try:
                    # Fetch headers + size
                    status, data = self.imap.fetch(
                        msg_id, 
                        "(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
                    )
                    
                    if status != "OK":
                        continue
                    
                    # Parse size
                    size_bytes = 0
                    for item in data:
                        if isinstance(item, bytes):
                            continue
                        item_str = item.decode() if isinstance(item, bytes) else str(item)
                        if "RFC822.SIZE" in item_str:
                            match = re.search(r'RFC822.SIZE (\d+)', item_str)
                            if match:
                                size_bytes = int(match.group(1))
                    
                    # Parse headers
                    for item in data:
                        if isinstance(item, tuple):
                            header_data = item[1]
                            msg = email.message_from_bytes(header_data)
                            
                            emails.append({
                                "id": msg_id.decode(),
                                "from": self._decode_header(msg.get("From", "")),
                                "subject": self._decode_header(msg.get("Subject", "")),
                                "date": msg.get("Date", ""),
                                "size_kb": round(size_bytes / 1024, 2)
                            })
                            break
                
                except Exception as e:
                    logger.error(f"Error parsing email {msg_id}: {e}")
                    continue
            
            return emails
        
        except Exception as e:
            logger.error(f"Error previewing emails: {e}")
            return []
    
    def _decode_header(self, header: str) -> str:
        """Decode email header to readable text"""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(encoding or "utf-8", errors="ignore")
            else:
                result += str(part)
        
        return result
    

    def delete_emails(self, email_ids: List[str], permanent: bool = False) -> Dict:
        """
        Delete emails by ID
        permanent=False: Move to Trash folder (reversible)
        permanent=True: Flag as deleted and expunge (permanent)
        """
        if not self.imap:
            return {"success": False, "error": "Not connected"}

        try:
            success_count = 0
            failed_ids = []

            if permanent:
                # Permanent delete: flag and expunge
                self.imap.select("INBOX")
                for email_id in email_ids:
                    try:
                        status, _ = self.imap.store(email_id.encode(), '+FLAGS', '\\Deleted')
                        if status == "OK":
                            success_count += 1
                        else:
                            failed_ids.append(email_id)
                    except Exception as e:
                        logger.error(f"Failed to delete {email_id}: {e}")
                        failed_ids.append(email_id)
                
                if success_count > 0:
                    self.imap.expunge()
            
            else:
                # Soft delete: COPY to Trash, then delete from INBOX
                self.imap.select("INBOX")
                
                for email_id in email_ids:
                    try:
                        # Copy to Trash folder
                        status, _ = self.imap.copy(email_id.encode(), 'Trash')
                        
                        if status == "OK":
                            # Now delete from INBOX
                            self.imap.store(email_id.encode(), '+FLAGS', '\\Deleted')
                            success_count += 1
                        else:
                            failed_ids.append(email_id)
                    except Exception as e:
                        logger.error(f"Failed to move {email_id} to trash: {e}")
                        failed_ids.append(email_id)
                
                # Expunge to remove from INBOX (but they're in Trash now)
                if success_count > 0:
                    self.imap.expunge()

            return {
                "success": True,
                "deleted_count": success_count,
                "failed_count": len(failed_ids),
                "failed_ids": failed_ids
            }

        except Exception as e:
            logger.error(f"Delete operation failed: {e}")
            return {"success": False, "error": str(e)}

    def send_message(
        self, 
        to: str, 
        subject: str, 
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict:
        """Send an email via SMTP"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        if not self.imap:
            return {"success": False, "error": "Not connected"}
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Yahoo SMTP settings
            smtp_server = "smtp.mail.yahoo.com"
            smtp_port = 587
            
            # Send via SMTP
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                
                recipients = [to]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                server.send_message(msg, self.email, recipients)
            
            logger.info(f"Email sent to {to}")
            return {
                "success": True,
                "message": f"Email sent to {to}"
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e)
            }
