"""Missing email worker functions"""
import email
import imaplib
from typing import Dict
import logging
import datetime

logger = logging.getLogger(__name__)


async def detect_spam(account_id: str, delete: bool = False, dry_run: bool = False) -> Dict:
    """Detect and optionally delete spam emails."""
    try:
        accounts = _load_email_accounts()
        if account_id not in accounts:
            return {"error": f"Account {account_id} not found"}
        
        account_info = accounts[account_id]
        mail = _connect_imap(account_info)
        mail.select('INBOX')
        
        _, message_numbers = mail.search(None, 'ALL')
        
        spam_count = 0
        deleted_count = 0
        spam_emails = []
        
        for num in message_numbers[0].split()[:50]:
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                if _is_spam(msg):
                    spam_count += 1
                    subject = _decode_header(msg.get('Subject', 'No Subject'))
                    from_addr = _decode_header(msg.get('From', 'Unknown'))
                    
                    spam_emails.append({
                        'subject': subject,
                        'from': from_addr,
                        'uid': num.decode()
                    })
                    
                    if delete and not dry_run:
                        mail.store(num, '+FLAGS', '\\Deleted')
                        deleted_count += 1
            except Exception as e:
                logger.error(f"Error processing email {num}: {e}")
                continue
        
        if delete and not dry_run:
            mail.expunge()
        
        mail.close()
        mail.logout()
        
        result = {
            "spam_found": spam_count,
            "spam_emails": spam_emails[:10],
            "response": f"Found {spam_count} spam emails."
        }
        
        if delete:
            if dry_run:
                result["response"] += f" DRY RUN: Would delete {spam_count} spam emails."
            else:
                result["response"] += f" Deleted {deleted_count} spam emails."
                result["deleted_count"] = deleted_count
        
        return result
        
    except Exception as e:
        logger.error(f"Error detecting spam: {e}")
        return {"error": str(e)}


async def categorize_emails(account_id: str, dry_run: bool = False) -> Dict:
    """Categorize emails into folders."""
    try:
        accounts = _load_email_accounts()
        if account_id not in accounts:
            return {"error": f"Account {account_id} not found"}
        
        account_info = accounts[account_id]
        mail = _connect_imap(account_info)
        mail.select('INBOX')
        
        _, message_numbers = mail.search(None, 'UNSEEN')
        
        categorized = {}
        moved_count = 0
        
        for num in message_numbers[0].split()[:30]:
            try:
                _, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                category = _categorize_email(msg)
                
                if category not in categorized:
                    categorized[category] = []
                
                subject = _decode_header(msg.get('Subject', 'No Subject'))
                categorized[category].append(subject)
                
                if not dry_run:
                    moved_count += 1
                    
            except Exception as e:
                logger.error(f"Error categorizing email {num}: {e}")
                continue
        
        mail.close()
        mail.logout()
        
        summary = "\n".join([f"{cat}: {len(emails)} emails" for cat, emails in categorized.items()])
        
        return {
            "categorized": categorized,
            "moved_count": moved_count if not dry_run else 0,
            "response": f"Categorized emails:\n{summary}" + (" (DRY RUN)" if dry_run else "")
        }
        
    except Exception as e:
        logger.error(f"Error categorizing emails: {e}")
        return {"error": str(e)}


async def cleanup_inbox(account_id: str, dry_run: bool = False) -> Dict:
    """Clean up inbox by deleting old read emails."""
    try:
        accounts = _load_email_accounts()
        if account_id not in accounts:
            return {"error": f"Account {account_id} not found"}
        
        account_info = accounts[account_id]
        mail = _connect_imap(account_info)
        mail.select('INBOX')
        
        date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%d-%b-%Y")
        _, message_numbers = mail.search(None, f'(SEEN BEFORE {date})')
        
        total_found = len(message_numbers[0].split()) if message_numbers[0] else 0
        deleted_count = 0
        
        if not dry_run and total_found > 0:
            for num in message_numbers[0].split():
                try:
                    mail.store(num, '+FLAGS', '\\Deleted')
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting email {num}: {e}")
            
            mail.expunge()
        
        mail.close()
        mail.logout()
        
        response = f"Found {total_found} old read emails."
        if dry_run:
            response += f" DRY RUN: Would delete {total_found} emails."
        else:
            response += f" Deleted {deleted_count} emails."
        
        return {
            "found": total_found,
            "deleted": deleted_count if not dry_run else 0,
            "response": response
        }
        
    except Exception as e:
        logger.error(f"Error cleaning inbox: {e}")
        return {"error": str(e)}