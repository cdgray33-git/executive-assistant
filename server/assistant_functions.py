"""
assistant_functions.py
Comprehensive assistant functions including email management, document generation,
and presentation automation for executive productivity tasks.
"""
import os
import json
import random
import logging
import email
import imaplib
import smtplib
import asyncio
import re
from datetime import datetime, timedelta
from email.message import EmailMessage
from email.header import decode_header
from typing import Dict, List, Optional, Any

# Configure logging with file handler
LOG_DIR = os.path.expanduser("~/ExecutiveAssistant/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "assistant.log")

# Set up logger - only configure if no handlers exist yet
logger = logging.getLogger("assistant_functions")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    # Add file handler
    file_handler = logging.FileHandler(LOG_FILE, mode='a')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

# Data directories
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
NOTES_DIR = os.path.join(ROOT, "notes")
CALENDAR_FILE = os.path.join(ROOT, "calendar", "events.json")
CONTACTS_FILE = os.path.join(ROOT, "contacts", "contacts.json")
EMAIL_ACCOUNTS_FILE = os.path.join(ROOT, "email_accounts.json")
OUTPUT_DIR = os.path.join(ROOT, "outputs")
PPTX_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "presentations")
DOCX_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "documents")
PDF_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "pdfs")

# Ensure directories exist
for directory in [NOTES_DIR, os.path.dirname(CALENDAR_FILE), os.path.dirname(CONTACTS_FILE),
                  OUTPUT_DIR, PPTX_OUTPUT_DIR, DOCX_OUTPUT_DIR, PDF_OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuration constants
SPAM_SCORE_THRESHOLD = 5  # X-Spam-Score threshold for spam detection
EMAIL_BATCH_SIZE = 100  # Number of emails to process in a single batch
CONTENT_PREVIEW_LENGTH = 300  # Length of email preview text
OLD_PROMOTIONS_DAYS = 365  # Days threshold for old promotions cleanup

# Initialize files if missing
if not os.path.exists(CALENDAR_FILE):
    with open(CALENDAR_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(CONTACTS_FILE):
    with open(CONTACTS_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(EMAIL_ACCOUNTS_FILE):
    with open(EMAIL_ACCOUNTS_FILE, "w") as f:
        json.dump({}, f)

# Function registry metadata
FUNCTION_REGISTRY = {
    "test_connection": {"description": "Test connection", "parameters": ["query"]},
    "take_notes": {"description": "Save a note", "parameters": ["content", "title"]},
    "get_notes": {"description": "Get a note or list", "parameters": ["title"]},
    "add_calendar_event": {"description": "Add event", "parameters": ["title", "date", "time", "description"]},
    "get_calendar": {"description": "Get calendar events", "parameters": ["days"]},
    "add_contact": {"description": "Add contact", "parameters": ["name", "email", "phone", "notes"]},
    "search_contacts": {"description": "Search contacts", "parameters": ["query"]},
    "fetch_recent_emails": {"description": "Fetch recent emails (all or unread only)", "parameters": ["account_id", "max_messages", "unread_only"]},
    "fetch_unread_emails": {"description": "Fetch unread emails", "parameters": ["account_id", "max_messages"]},
    "mark_email_read": {"description": "Mark email read", "parameters": ["account_id", "uid"]},
    "send_email": {"description": "Send an email", "parameters": ["account_id", "to", "subject", "body"]},
    "bulk_delete_emails": {"description": "Bulk delete emails by criteria", "parameters": ["account_id", "criteria", "dry_run"]},
    "categorize_emails": {"description": "Auto-categorize emails into folders", "parameters": ["account_id", "max_messages", "dry_run"]},
    "detect_spam": {"description": "Detect and optionally delete spam", "parameters": ["account_id", "max_messages", "delete", "dry_run"]},
    "move_spam_to_folder": {"description": "Move spam emails to Spam folder (recommended - does not delete)", "parameters": ["account_id", "max_messages", "dry_run"]},
    "cleanup_inbox": {"description": "Automated inbox cleanup workflow", "parameters": ["account_id", "dry_run"]},
    "generate_presentation": {"description": "Generate PowerPoint presentation", "parameters": ["title", "slides", "output_filename"]},
    "create_briefing": {"description": "Create briefing document", "parameters": ["title", "summary", "key_points", "action_items", "format"]},
    "write_document": {"description": "Create formatted document", "parameters": ["doc_type", "title", "content", "format"]},
    "summarize_text": {"description": "Summarize text", "parameters": ["text"]}
}


def _load_email_accounts():
    """Load email accounts from JSON file."""
    try:
        with open(EMAIL_ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_email_accounts(accounts):
    """Save email accounts to JSON file."""
    with open(EMAIL_ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    os.chmod(EMAIL_ACCOUNTS_FILE, 0o600)


def _decode_header(h):
    """Decode email header."""
    parts = decode_header(h)
    out = ""
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out += text.decode(enc or "utf-8", errors="replace")
            except Exception:
                out += text.decode("utf-8", errors="replace")
        else:
            out += text
    return out


def _connect_imap(account_info: Dict) -> imaplib.IMAP4_SSL:
    """Connect to IMAP server."""
    host = account_info["imap_host"]
    port = int(account_info.get("imap_port", 993))
    use_ssl = account_info.get("use_ssl", True)
    username = account_info["username"]
    password = account_info["password"]
    
    if use_ssl:
        M = imaplib.IMAP4_SSL(host, port)
    else:
        M = imaplib.IMAP4(host, port)
    M.login(username, password)
    return M


def _is_spam(msg: email.message.Message) -> bool:
    """
    Detect spam based on headers, content heuristics, and patterns.
    """
    subject = _decode_header(msg.get("Subject", "")).lower()
    from_addr = _decode_header(msg.get("From", "")).lower()
    
    # Common spam patterns
    spam_keywords = [
        "viagra", "cialis", "lottery", "winner", "prize", "claim now",
        "act now", "limited time", "click here", "make money fast",
        "nigerian prince", "inheritance", "congratulations you won",
        "free money", "work from home", "miracle cure"
    ]
    
    # Check spam score in headers
    spam_score = msg.get("X-Spam-Score", "")
    if spam_score:
        try:
            # Extract numeric value using regex to handle various formats like "5.2" or "score=5.2"
            match = re.search(r'[-+]?\d*\.?\d+', spam_score)
            if match:
                score_val = abs(float(match.group()))
                if score_val > SPAM_SCORE_THRESHOLD:
                    return True
        except (ValueError, AttributeError):
            pass  # Invalid spam score format, continue with other checks
    
    # Check spam status
    spam_status = msg.get("X-Spam-Status", "").lower()
    if "yes" in spam_status:
        return True
    
    # Check subject and from for spam keywords
    for keyword in spam_keywords:
        if keyword in subject or keyword in from_addr:
            return True
    
    # Check for suspicious patterns
    if re.search(r'\d{10,}', subject):  # Long number sequences
        return True
    
    if subject.count('!') > 3:  # Excessive exclamation marks
        return True
    
    return False


def _categorize_email(msg: email.message.Message) -> str:
    """
    Categorize email based on content analysis.
    Returns folder name: "Personal", "Work", "Promotions", "Social", "Spam"
    """
    if _is_spam(msg):
        return "Spam"
    
    subject = _decode_header(msg.get("Subject", "")).lower()
    from_addr = _decode_header(msg.get("From", "")).lower()
    
    # Promotions indicators
    promo_keywords = ["sale", "discount", "offer", "deal", "coupon", "promotion", "subscribe", "unsubscribe"]
    if any(kw in subject or kw in from_addr for kw in promo_keywords):
        return "Promotions"
    
    # Social media indicators
    social_domains = ["facebook", "twitter", "linkedin", "instagram", "pinterest"]
    if any(domain in from_addr for domain in social_domains):
        return "Social"
    
    # Work indicators (can be customized based on user's domain)
    work_keywords = ["meeting", "project", "deadline", "report", "invoice", "contract"]
    if any(kw in subject for kw in work_keywords):
        return "Work"
    
    # Default to Personal
    return "Personal"


def _ensure_folder_exists(M: imaplib.IMAP4_SSL, folder_name: str) -> bool:
    """Ensure a folder exists, create it if it doesn't."""
    try:
        # Try to select the folder - this is the most reliable check
        typ, data = M.select(folder_name, readonly=True)
        if typ == 'OK':
            # Folder exists, go back to INBOX
            M.select('INBOX')
            return True
        
        # Folder doesn't exist, try to create it
        typ, data = M.create(folder_name)
        if typ != 'OK':
            logger.error(f"Failed to create folder {folder_name}: {data}")
            return False
        
        logger.info(f"Created folder: {folder_name}")
        M.select('INBOX')  # Go back to INBOX
        return True
    except Exception as e:
        logger.error(f"Error ensuring folder exists: {e}")
        return False
        return False


def _move_email_to_folder(M: imaplib.IMAP4_SSL, uid: bytes, target_folder: str) -> bool:
    """Move an email to a target folder using UID."""
    try:
        # Ensure UID is bytes
        if isinstance(uid, str):
            uid = uid.encode()
        
        # Copy to target folder
        typ, data = M.uid('COPY', uid, target_folder)
        if typ != 'OK':
            logger.error(f"Failed to copy email {uid} to {target_folder}: {data}")
            return False
        
        # Mark original as deleted
        typ, data = M.uid('STORE', uid, '+FLAGS', '(\\Deleted)')
        if typ != 'OK':
            logger.error(f"Failed to mark email {uid} as deleted: {data}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error moving email: {e}")
        return False


# Basic functions
async def test_connection(query="test", **kwargs):
    """Test connection to assistant."""
    return {
        "message": f"Assistant reachable. Query: {query}",
        "timestamp": datetime.now().isoformat(),
        "functions": list(FUNCTION_REGISTRY.keys())
    }


async def take_notes(content, title=None, **kwargs):
    """Save a note to file."""
    if not title:
        title = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title).strip().replace(' ', '_') + ".txt"
    path = os.path.join(NOTES_DIR, filename)
    with open(path, "w") as f:
        f.write(content)
    return {"message": "note saved", "filename": filename, "timestamp": datetime.now().isoformat()}


async def get_notes(title=None, **kwargs):
    """Get a specific note or list all notes."""
    if title:
        filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title).strip().replace(' ', '_') + ".txt"
        path = os.path.join(NOTES_DIR, filename)
        try:
            with open(path) as f:
                return {"title": title, "content": f.read(), "timestamp": datetime.now().isoformat()}
        except FileNotFoundError:
            return {"error": "not found", "available": await list_notes()}
    return await list_notes()


async def list_notes(**kwargs):
    """List all available notes."""
    notes = []
    for fn in os.listdir(NOTES_DIR):
        if fn.endswith(".txt"):
            notes.append({"title": fn.replace('_', ' ').replace('.txt', ''), "filename": fn})
    return {"notes": notes, "count": len(notes)}


# Calendar functions
async def add_calendar_event(title, date, time=None, description=None, **kwargs):
    """Add a calendar event."""
    with open(CALENDAR_FILE) as f:
        events = json.load(f)
    event = {
        "id": str(random.randint(10000, 99999)),
        "title": title,
        "date": date,
        "time": time,
        "description": description,
        "created_at": datetime.now().isoformat()
    }
    events.append(event)
    with open(CALENDAR_FILE, "w") as f:
        json.dump(events, f, indent=2)
    return {"message": "event added", "event": event}


async def get_calendar(days=7, **kwargs):
    """Get calendar events for next N days."""
    with open(CALENDAR_FILE) as f:
        all_events = json.load(f)
    today = datetime.now().date()
    end = today + timedelta(days=int(days))
    events = []
    for ev in all_events:
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            if today <= d <= end:
                events.append(ev)
        except Exception:
            pass
    return {"events": events, "count": len(events)}


# Contacts functions
async def add_contact(name, email=None, phone=None, notes=None, **kwargs):
    """Add a contact."""
    with open(CONTACTS_FILE) as f:
        contacts = json.load(f)
    contact = {
        "id": str(random.randint(10000, 99999)),
        "name": name,
        "email": email,
        "phone": phone,
        "notes": notes,
        "created_at": datetime.now().isoformat()
    }
    contacts.append(contact)
    with open(CONTACTS_FILE, "w") as f:
        json.dump(contacts, f, indent=2)
    return {"message": "contact added", "contact": contact}


async def search_contacts(query, **kwargs):
    """Search contacts."""
    with open(CONTACTS_FILE) as f:
        contacts = json.load(f)
    q = query.lower()
    matches = [c for c in contacts if q in (c.get("name", "") + c.get("email", "") + c.get("phone", "") + c.get("notes", "")).lower()]
    return {"contacts": matches, "count": len(matches)}


# Email account management
async def add_email_account(account_id, imap_host, imap_port, smtp_host, smtp_port, username, password, use_ssl=True, **kwargs):
    """Add an email account."""
    def _sync():
        accounts = _load_email_accounts()
        accounts[account_id] = {
            "imap_host": imap_host,
            "imap_port": int(imap_port),
            "smtp_host": smtp_host,
            "smtp_port": int(smtp_port),
            "username": username,
            "password": password,
            "use_ssl": bool(use_ssl)
        }
        _save_email_accounts(accounts)
        return {"message": f"Saved account {account_id}"}
    return await asyncio.to_thread(_sync)


async def list_email_accounts(**kwargs):
    """List configured email accounts."""
    accounts = _load_email_accounts()
    return {"accounts": list(accounts.keys()), "count": len(accounts)}


# Enhanced email functions
async def fetch_recent_emails(account_id, max_messages=10, unread_only=False, **kwargs):
    """Fetch recent emails from account (all emails or unread only)."""
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found", "available": list(accounts.keys())}
        
        try:
            M = _connect_imap(acct)
            M.select("INBOX")
            
            # Search for unread emails or all emails
            if unread_only:
                typ, data = M.search(None, "UNSEEN")
            else:
                typ, data = M.search(None, "ALL")
                
            uids = data[0].split() if data and data[0] else []
            uids = uids[-int(max_messages):]  # Get the last N emails
            results = []
            
            for uid in reversed(uids):
                typ, msg_data = M.fetch(uid, "(RFC822 FLAGS)")
                raw = msg_data[0][1]
                flags = msg_data[0][0].decode() if msg_data[0][0] else ""
                is_unread = "\\Seen" not in flags
                
                msg = email.message_from_bytes(raw)
                subject = _decode_header(msg.get("Subject", ""))
                frm = _decode_header(msg.get("From", ""))
                date = msg.get("Date", "")
                body = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        disp = str(part.get("Content-Disposition"))
                        if ctype == "text/plain" and "attachment" not in disp:
                            try:
                                body = part.get_payload(decode=True).decode(errors="replace")
                            except Exception:
                                body = str(part.get_payload())
                            break
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="replace")
                    except Exception:
                        body = str(msg.get_payload())
                
                preview = " ".join(body.strip().splitlines())[:400] + ("..." if len(body) > 400 else "")
                results.append({
                    "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                    "from": frm,
                    "subject": subject,
                    "date": date,
                    "preview": preview,
                    "unread": is_unread
                })
            
            M.logout()
            return {"messages": results, "count": len(results)}
        except imaplib.IMAP4.error as e:
            return {"error": f"IMAP error: {str(e)}"}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}
    
    return await asyncio.to_thread(_sync)


async def fetch_unread_emails(account_id, max_messages=10, **kwargs):
    """Fetch unread emails from account (wrapper for backwards compatibility)."""
    return await fetch_recent_emails(account_id, max_messages, unread_only=True, **kwargs)


async def mark_email_read(account_id, uid, **kwargs):
    """Mark an email as read."""
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        try:
            M = _connect_imap(acct)
            M.select("INBOX")
            M.store(uid, '+FLAGS', '\\Seen')
            M.logout()
            return {"message": f"Marked {uid} as read"}
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def send_email(account_id, to, subject, body, **kwargs):
    """Send an email."""
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        smtp_host = acct["smtp_host"]
        smtp_port = int(acct["smtp_port"])
        username = acct["username"]
        password = acct["password"]
        use_ssl = acct.get("use_ssl", True)
        
        try:
            msg = EmailMessage()
            msg["From"] = username
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)
            
            if smtp_port == 465 or use_ssl:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
                server.starttls()
            
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            return {"message": "Email sent"}
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def bulk_delete_emails(account_id, criteria: Dict, dry_run=True, **kwargs):
    """
    Bulk delete emails based on criteria.
    criteria = {
        "older_than_days": int (e.g., 365 for 1 year),
        "folder": str (e.g., "Promotions", "INBOX"),
        "from_contains": str (optional),
        "subject_contains": str (optional)
    }
    """
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        try:
            M = _connect_imap(acct)
            folder = criteria.get("folder", "INBOX")
            M.select(folder)
            
            # Build search criteria
            search_parts = []
            
            if "older_than_days" in criteria:
                cutoff_date = datetime.now() - timedelta(days=int(criteria["older_than_days"]))
                date_str = cutoff_date.strftime("%d-%b-%Y")
                search_parts.append(f'BEFORE {date_str}')
            
            if "from_contains" in criteria:
                search_parts.append(f'FROM "{criteria["from_contains"]}"')
            
            if "subject_contains" in criteria:
                search_parts.append(f'SUBJECT "{criteria["subject_contains"]}"')
            
            # Default to ALL if no criteria
            search_query = " ".join(search_parts) if search_parts else "ALL"
            
            # Process in batches to avoid timeout
            batch_size = 100
            typ, data = M.search(None, search_query)
            uids = data[0].split() if data and data[0] else []
            
            total_count = len(uids)
            deleted_count = 0
            
            if dry_run:
                M.logout()
                return {
                    "message": "Dry run - no emails deleted",
                    "would_delete": total_count,
                    "criteria": criteria
                }
            
            # Delete in batches
            for i in range(0, len(uids), batch_size):
                batch = uids[i:i + batch_size]
                for uid in batch:
                    M.store(uid, '+FLAGS', '\\Deleted')
                    deleted_count += 1
                M.expunge()  # Permanently remove deleted messages
            
            M.logout()
            return {
                "message": f"Deleted {deleted_count} emails",
                "deleted_count": deleted_count,
                "criteria": criteria
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def categorize_emails(account_id, max_messages=EMAIL_BATCH_SIZE, dry_run=True, **kwargs):
    """
    Auto-categorize emails into folders.
    Creates folders if they don't exist.
    """
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        try:
            M = _connect_imap(acct)
            M.select("INBOX")
            
            # Get messages to categorize
            typ, data = M.search(None, "ALL")
            uids = data[0].split() if data and data[0] else []
            uids = uids[-int(max_messages):]
            
            categorization_results = {}
            
            for uid in uids:
                typ, msg_data = M.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                category = _categorize_email(msg)
                
                if category not in categorization_results:
                    categorization_results[category] = 0
                categorization_results[category] += 1
                
                if not dry_run:
                    # Ensure folder exists
                    folder_name = category
                    try:
                        M.create(folder_name)
                    except:
                        pass  # Folder might already exist
                    
                    # Copy message to folder and delete from INBOX
                    try:
                        M.copy(uid, folder_name)
                        M.store(uid, '+FLAGS', '\\Deleted')
                    except Exception as e:
                        logger.warning(f"Failed to move message {uid}: {e}")
            
            if not dry_run:
                M.expunge()
            
            M.logout()
            
            return {
                "message": "Categorization complete" if not dry_run else "Dry run - no emails moved",
                "categorization": categorization_results,
                "total_processed": len(uids),
                "dry_run": dry_run
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def detect_spam(account_id, max_messages=EMAIL_BATCH_SIZE, delete=False, dry_run=True, **kwargs):
    """
    Detect spam emails and optionally delete them.
    """
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        try:
            M = _connect_imap(acct)
            M.select("INBOX")
            
            typ, data = M.search(None, "ALL")
            uids = data[0].split() if data and data[0] else []
            uids = uids[-int(max_messages):]
            
            spam_messages = []
            
            for uid in uids:
                typ, msg_data = M.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                if _is_spam(msg):
                    subject = _decode_header(msg.get("Subject", ""))
                    frm = _decode_header(msg.get("From", ""))
                    spam_messages.append({
                        "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                        "from": frm,
                        "subject": subject
                    })
                    
                    if delete and not dry_run:
                        M.store(uid, '+FLAGS', '\\Deleted')
            
            if delete and not dry_run:
                M.expunge()
            
            M.logout()
            
            return {
                "message": f"{'Would delete' if dry_run else 'Deleted'} {len(spam_messages)} spam messages" if delete else f"Found {len(spam_messages)} spam messages",
                "spam_count": len(spam_messages),
                "spam_messages": spam_messages[:10],  # Return first 10 for preview
                "dry_run": dry_run
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def move_spam_to_folder(account_id, max_messages=EMAIL_BATCH_SIZE, dry_run=False, **kwargs):
    """
    Detect spam emails and move them to the Spam folder (does not delete).
    This is the recommended approach - moves spam to Spam folder for review.
    
    Args:
        account_id: Email account identifier
        max_messages: Maximum number of recent emails to scan (default: 100)
        dry_run: If True, only reports what would be moved without moving
    
    Returns:
        Dictionary with results including count of moved emails and details
    """
    def _sync():
        accounts = _load_email_accounts()
        acct = accounts.get(account_id)
        if not acct:
            return {"error": f"Account {account_id} not found"}
        
        try:
            M = _connect_imap(acct)
            M.select("INBOX")
            
            # Ensure Spam folder exists
            spam_folder = "Spam"
            if not dry_run:
                if not _ensure_folder_exists(M, spam_folder):
                    # Try alternative names
                    for alt_name in ["Junk", "[Gmail]/Spam", "Junk Email"]:
                        if _ensure_folder_exists(M, alt_name):
                            spam_folder = alt_name
                            break
            
            # Search for all emails
            typ, data = M.search(None, "ALL")
            uids = data[0].split() if data and data[0] else []
            uids = uids[-int(max_messages):]  # Get the last N emails
            
            spam_messages = []
            moved_count = 0
            
            for uid in uids:
                typ, msg_data = M.fetch(uid, "(RFC822)")
                if not msg_data or not msg_data[0]:
                    continue
                    
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                
                if _is_spam(msg):
                    subject = _decode_header(msg.get("Subject", ""))
                    frm = _decode_header(msg.get("From", ""))
                    spam_messages.append({
                        "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                        "from": frm,
                        "subject": subject
                    })
                    
                    if not dry_run:
                        # Move to spam folder
                        if _move_email_to_folder(M, uid, spam_folder):
                            moved_count += 1
            
            if not dry_run and moved_count > 0:
                # Expunge deleted messages from INBOX
                M.expunge()
            
            M.logout()
            
            response_msg = f"{'Would move' if dry_run else 'Moved'} {len(spam_messages)} spam email(s) to {spam_folder} folder"
            
            return {
                "message": response_msg,
                "spam_count": len(spam_messages),
                "moved_count": moved_count if not dry_run else 0,
                "spam_messages": spam_messages[:10],  # Return first 10 for preview
                "dry_run": dry_run,
                "target_folder": spam_folder
            }
        except Exception as e:
            logger.exception(f"Error in move_spam_to_folder: {e}")
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def cleanup_inbox(account_id, dry_run=True, **kwargs):
    """
    Automated inbox cleanup workflow:
    1. Delete spam
    2. Categorize emails
    3. Delete old emails (> 1 year) from Promotions
    """
    results = {
        "spam_cleanup": None,
        "categorization": None,
        "old_promotions_cleanup": None
    }
    
    # Step 1: Detect and delete spam
    spam_result = await detect_spam(account_id, max_messages=200, delete=True, dry_run=dry_run)
    results["spam_cleanup"] = spam_result
    
    # Step 2: Categorize emails
    cat_result = await categorize_emails(account_id, max_messages=EMAIL_BATCH_SIZE, dry_run=dry_run)
    results["categorization"] = cat_result
    
    # Step 3: Delete old promotions
    promo_result = await bulk_delete_emails(
        account_id,
        criteria={"older_than_days": OLD_PROMOTIONS_DAYS, "folder": "Promotions"},
        dry_run=dry_run
    )
    results["old_promotions_cleanup"] = promo_result
    
    return {
        "message": "Inbox cleanup complete" if not dry_run else "Inbox cleanup dry run complete",
        "results": results,
        "dry_run": dry_run
    }


# Document generation functions
async def generate_presentation(title, slides: List[Dict], output_filename=None, **kwargs):
    """
    Generate PowerPoint presentation.
    slides = [
        {"type": "title", "title": "...", "subtitle": "..."},
        {"type": "content", "title": "...", "content": "..."},
        {"type": "bullets", "title": "...", "bullets": [...]},
    ]
    """
    def _sync():
        try:
            # Try local import first (when running from server directory)
            try:
                from utils.pptx_generator import generate_presentation as gen_ppt
            except ImportError:
                from server.utils.pptx_generator import generate_presentation as gen_ppt
            
            fname = output_filename if output_filename else f"presentation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
            
            output_path = os.path.join(PPTX_OUTPUT_DIR, fname)
            gen_ppt(title, slides, output_path)
            
            return {
                "message": "Presentation generated",
                "filename": fname,
                "path": output_path,
                "slides_count": len(slides)
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def create_briefing(title, summary, key_points: List[str], action_items: List[str], format="docx", **kwargs):
    """
    Create a briefing document.
    format: "docx" or "pdf"
    """
    def _sync():
        try:
            # Try local import first (when running from server directory)
            try:
                from utils.document_generator import create_briefing_doc
            except ImportError:
                from server.utils.document_generator import create_briefing_doc
            
            filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            
            if format == "docx":
                output_path = os.path.join(DOCX_OUTPUT_DIR, filename)
            else:
                output_path = os.path.join(PDF_OUTPUT_DIR, filename)
            
            create_briefing_doc(title, summary, key_points, action_items, output_path, format)
            
            return {
                "message": "Briefing created",
                "filename": filename,
                "path": output_path,
                "format": format
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


async def write_document(doc_type, title, content, format="docx", **kwargs):
    """
    Create formatted document (letter, memo, meeting notes).
    doc_type: "letter", "memo", "meeting_notes"
    format: "docx" or "pdf"
    """
    def _sync():
        try:
            # Try local import first (when running from server directory)
            try:
                from utils.document_generator import create_document
            except ImportError:
                from server.utils.document_generator import create_document
            
            filename = f"{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            
            if format == "docx":
                output_path = os.path.join(DOCX_OUTPUT_DIR, filename)
            else:
                output_path = os.path.join(PDF_OUTPUT_DIR, filename)
            
            create_document(doc_type, title, content, output_path, format)
            
            return {
                "message": f"{doc_type.replace('_', ' ').title()} created",
                "filename": filename,
                "path": output_path,
                "format": format
            }
        except Exception as e:
            return {"error": str(e)}
    
    return await asyncio.to_thread(_sync)


# Summarize function
async def summarize_text(text, **kwargs):
    """Simple text summarization."""
    words = text.split()
    summary = " ".join(words[:min(30, max(1, len(words) // 3))]) + "..."
    return {"summary": summary, "original_length": len(words)}


# Router: execute function by name
async def execute_function(function_name, arguments):
    """Execute a function by name with given arguments."""
    mapping = {
        "test_connection": test_connection,
        "take_notes": take_notes,
        "get_notes": get_notes,
        "list_notes": list_notes,
        "add_calendar_event": add_calendar_event,
        "get_calendar": get_calendar,
        "add_contact": add_contact,
        "search_contacts": search_contacts,
        "add_email_account": add_email_account,
        "list_email_accounts": list_email_accounts,
        "fetch_recent_emails": fetch_recent_emails,
        "fetch_unread_emails": fetch_unread_emails,
        "mark_email_read": mark_email_read,
        "send_email": send_email,
        "bulk_delete_emails": bulk_delete_emails,
        "categorize_emails": categorize_emails,
        "detect_spam": detect_spam,
        "cleanup_inbox": cleanup_inbox,
        "generate_presentation": generate_presentation,
        "create_briefing": create_briefing,
        "write_document": write_document,
        "summarize_text": summarize_text
    }
    
    fn = mapping.get(function_name)
    if not fn:
        return {"error": f"Function '{function_name}' not found", "available": list(mapping.keys())}
    return await fn(**arguments)


def get_function_names():
    """Get list of available function names."""
    return list(FUNCTION_REGISTRY.keys())


def get_function_info():
    """Get function registry information."""
    return FUNCTION_REGISTRY


# Handler functions for NLP intent routing
async def handle_schedule_meeting(params: Dict) -> Dict:
    """Handle meeting scheduling intent."""
    try:
        attendee_email = params.get("attendee_email", "")
        date_str = params.get("date", "")
        time_str = params.get("time", "")
        title = params.get("title", f"Meeting with {attendee_email}")
        
        if not attendee_email or not date_str:
            return {"error": "Missing required parameters: attendee_email and date"}
        
        # Add to calendar
        result = await add_calendar_event(title=title, date=date_str, time=time_str)
        
        # Add contact if provided
        if attendee_email:
            await add_contact(name=attendee_email.split('@')[0], email=attendee_email)
        
        return {"response": f"✓ Meeting scheduled: {title} on {date_str}" + (f" at {time_str}" if time_str else "")}
    except Exception as e:
        logger.error(f"Error handling schedule_meeting: {e}")
        return {"error": str(e)}


async def handle_view_calendar(params: Dict) -> Dict:
    """Handle calendar viewing intent."""
    try:
        days = params.get("days", 7)
        result = await get_calendar(days=days)
        return {"response": result.get("response", "No events found")}
    except Exception as e:
        logger.error(f"Error handling view_calendar: {e}")
        return {"error": str(e)}


async def handle_add_contact(params: Dict) -> Dict:
    """Handle contact addition intent."""
    try:
        name = params.get("name", "")
        email_addr = params.get("email", "")
        phone = params.get("phone", "")
        notes_txt = params.get("notes", "")
        
        if not name and not email_addr:
            return {"error": "Missing required parameters: name or email"}
        
        result = await add_contact(name=name, email=email_addr, phone=phone, notes=notes_txt)
        return {"response": result.get("response", "Contact added successfully")}
    except Exception as e:
        logger.error(f"Error handling add_contact: {e}")
        return {"error": str(e)}


async def handle_search_contacts(params: Dict) -> Dict:
    """Handle contact search intent."""
    try:
        query = params.get("query", "")
        if not query:
            return {"error": "Missing search query"}
        
        result = await search_contacts(query=query)
        return {"response": result.get("response", "No contacts found")}
    except Exception as e:
        logger.error(f"Error handling search_contacts: {e}")
        return {"error": str(e)}


async def handle_send_email(params: Dict) -> Dict:
    """Handle email sending intent."""
    try:
        to_addr = params.get("to", "")
        subject = params.get("subject", "Message from Executive Assistant")
        body = params.get("body", "")
        
        if not to_addr or not body:
            return {"error": "Missing required parameters: to and body"}
        
        # Get first email account
        accounts = _load_email_accounts()
        if not accounts:
            return {"error": "No email accounts configured"}
        
        account_id = list(accounts.keys())[0]
        result = await send_email(account_id=account_id, to=to_addr, subject=subject, body=body)
        return {"response": result.get("response", "Email sent successfully")}
    except Exception as e:
        logger.error(f"Error handling send_email: {e}")
        return {"error": str(e)}


async def handle_create_presentation(params: Dict) -> Dict:
    """Handle presentation creation intent."""
    try:
        title = params.get("title", "Presentation")
        topic = params.get("topic", title)
        
        # Create default slide structure
        slides = [
            {"title": title, "content": ["Created by Executive Assistant"]},
            {"title": "Overview", "content": [f"Topic: {topic}", "Key points will be covered"]},
            {"title": "Conclusion", "content": ["Thank you"]}
        ]
        
        result = await generate_presentation(title=title, slides=slides)
        
        if "error" in result:
            return {"response": f"Error creating presentation: {result['error']}"}
        
        # Provide detailed feedback with content preview
        response = f"✓ PowerPoint Presentation Created: {title}\n\n"
        response += f"📄 File: {result.get('path', result.get('filename', 'Unknown'))}\n"
        response += f"📊 Slides: {result.get('slides_count', len(slides))}\n\n"
        response += "Slide Preview:\n"
        for i, slide in enumerate(slides, 1):
            response += f"  {i}. {slide.get('title', 'Untitled')}\n"
            content = slide.get('content', [])
            if content:
                for item in content[:2]:  # Show first 2 content items
                    response += f"     • {item}\n"
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error handling create_presentation: {e}")
        return {"response": f"Error creating presentation: {str(e)}"}


async def handle_create_document(params: Dict) -> Dict:
    """Handle document creation intent."""
    try:
        doc_type = params.get("doc_type", "report")
        title = params.get("title", params.get("subject", "Document"))
        content = params.get("content", params.get("message", ""))
        
        # If no meaningful content provided, generate placeholder
        if not content or content == "Document content":
            content = f"This {doc_type} document needs content.\n\n" + \
                     f"Document Type: {doc_type.title()}\n" + \
                     f"Title: {title}\n\n" + \
                     "Please provide the actual content for this document."
        
        result = await write_document(doc_type=doc_type, title=title, content=content)
        
        if "error" in result:
            return {"response": f"Error creating document: {result['error']}"}
        
        # Provide detailed response with content preview
        response = f"✓ {doc_type.title()} Created: {title}\n\n"
        response += f"📄 File: {result.get('path', result.get('filename', 'Unknown'))}\n"
        response += f"📝 Format: {result.get('format', 'docx').upper()}\n\n"
        response += "Content Preview:\n"
        response += "─" * 50 + "\n"
        
        # Show first N characters of content
        preview_content = content[:CONTENT_PREVIEW_LENGTH].strip()
        if len(content) > CONTENT_PREVIEW_LENGTH:
            preview_content += "..."
        response += preview_content + "\n"
        response += "─" * 50 + "\n\n"
        response += f"Total length: {len(content)} characters\n"
        response += "The document has been saved and is ready to use."
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error handling create_document: {e}")
        return {"response": f"Error creating document: {str(e)}"}


async def handle_take_note(params: Dict) -> Dict:
    """Handle note taking intent."""
    try:
        content = params.get("content", "")
        title = params.get("title", None)
        
        if not content:
            return {"error": "Missing note content"}
        
        result = await take_notes(content=content, title=title)
        return {"response": result.get("response", "Note saved successfully")}
    except Exception as e:
        logger.error(f"Error handling take_note: {e}")
        return {"error": str(e)}


async def handle_view_notes(params: Dict) -> Dict:
    """Handle note viewing intent."""
    try:
        result = await list_notes()
        return {"response": result.get("response", "No notes found")}
    except Exception as e:
        logger.error(f"Error handling view_notes: {e}")
        return {"error": str(e)}


async def handle_view_emails(params: Dict) -> Dict:
    """Handle email viewing intent - shows ALL recent emails (read and unread) with filtering support."""
    try:
        # Extract count parameter from various possible keys
        max_messages = params.get("count", params.get("max_messages", params.get("limit", 10)))
        if isinstance(max_messages, str):
            # Try to extract number from string like "7 emails" or "last 5"
            import re
            match = re.search(r'\d+', max_messages)
            if match:
                max_messages = int(match.group())
            else:
                max_messages = 10
        
        # Extract filter parameters (LLM can provide these)
        sender_filter = params.get("sender", params.get("from", params.get("from_email", "")))
        subject_filter = params.get("subject", params.get("subject_contains", ""))
        search_term = params.get("search", params.get("search_term", params.get("keyword", "")))
        
        # Check if user specifically wants unread only
        unread_only = params.get("unread_only", False)
        if isinstance(params.get("query", ""), str):
            query_lower = params.get("query", "").lower()
            if "unread" in query_lower and "only" in query_lower:
                unread_only = True
        
        # Get first email account
        accounts = _load_email_accounts()
        if not accounts:
            return {"response": "No email accounts configured. Please set up an email account first."}
        
        account_id = list(accounts.keys())[0]
        
        # Fetch more emails if we're filtering (to ensure we get enough results after filtering)
        fetch_count = max_messages * 10 if (sender_filter or subject_filter or search_term) else max_messages
        result = await fetch_recent_emails(account_id=account_id, max_messages=fetch_count, unread_only=unread_only)
        
        # Check for error first
        if "error" in result:
            return {"response": f"Could not fetch emails: {result['error']}"}
        
        # fetch_recent_emails returns "messages" key
        if "messages" in result:
            emails = result["messages"]
            if not emails:
                return {"response": "No emails found"}
            
            # Apply client-side filtering based on LLM-extracted parameters
            filtered_emails = emails
            
            if sender_filter:
                sender_lower = sender_filter.lower()
                filtered_emails = [
                    e for e in filtered_emails 
                    if sender_lower in e.get('from', '').lower()
                ]
            
            if subject_filter:
                subject_lower = subject_filter.lower()
                filtered_emails = [
                    e for e in filtered_emails 
                    if subject_lower in e.get('subject', '').lower()
                ]
            
            if search_term:
                search_lower = search_term.lower()
                filtered_emails = [
                    e for e in filtered_emails 
                    if search_lower in e.get('subject', '').lower() 
                    or search_lower in e.get('from', '').lower()
                    or search_lower in e.get('preview', '').lower()
                ]
            
            # Limit to requested count after filtering
            filtered_emails = filtered_emails[:max_messages]
            
            if not filtered_emails:
                filter_desc = []
                if sender_filter:
                    filter_desc.append(f"from {sender_filter}")
                if subject_filter:
                    filter_desc.append(f"with subject containing '{subject_filter}'")
                if search_term:
                    filter_desc.append(f"matching '{search_term}'")
                
                if filter_desc:
                    return {"response": f"No emails found {' and '.join(filter_desc)}"}
                return {"response": "No emails found"}
            
            unread_count = sum(1 for e in filtered_emails if e.get('unread', False))
            email_type = "unread email(s)" if unread_only else f"email(s) ({unread_count} unread)"
            
            # Build filter description for response
            filter_parts = []
            if sender_filter:
                filter_parts.append(f"from {sender_filter}")
            if subject_filter:
                filter_parts.append(f"with subject containing '{subject_filter}'")
            if search_term:
                filter_parts.append(f"matching '{search_term}'")
            
            filter_text = f" {' and '.join(filter_parts)}" if filter_parts else ""
            response = f"Found {len(filtered_emails)} {email_type}{filter_text}:\n\n"
            
            for i, email_data in enumerate(filtered_emails, 1):
                status_icon = "📧 [UNREAD]" if email_data.get('unread', False) else "✓ [READ]"
                response += f"{i}. {status_icon} From: {email_data.get('from', 'Unknown')}\n"
                response += f"   Subject: {email_data.get('subject', 'No subject')}\n"
                response += f"   Date: {email_data.get('date', 'Unknown')}\n"
                preview = email_data.get('preview', '')
                if preview:
                    response += f"   Preview: {preview[:150]}...\n"
                response += "\n"
            
            return {"response": response}
        
        return {"response": "Could not fetch emails"}
    except Exception as e:
        logger.error(f"Error handling view_emails: {e}")
        return {"response": f"Error fetching emails: {str(e)}"}


async def handle_delete_spam(params: Dict) -> Dict:
    """Handle spam deletion intent - moves spam to Spam folder."""
    try:
        max_messages = params.get("max_messages", EMAIL_BATCH_SIZE)
        dry_run = params.get("dry_run", False)
        
        # Get first email account
        accounts = _load_email_accounts()
        if not accounts:
            return {"error": "No email accounts configured"}
        
        account_id = list(accounts.keys())[0]
        result = await move_spam_to_folder(account_id=account_id, max_messages=max_messages, dry_run=dry_run)
        
        # Format response
        if "error" in result:
            return {"response": f"Error: {result['error']}"}
        
        message = result.get("message", "Spam processing completed")
        spam_count = result.get("spam_count", 0)
        target_folder = result.get("target_folder", "Spam")
        
        response = f"{message}\n\n"
        if spam_count > 0:
            response += f"Found {spam_count} spam email(s):\n"
            for i, spam in enumerate(result.get("spam_messages", [])[:5], 1):
                response += f"{i}. From: {spam.get('from', 'Unknown')}\n"
                response += f"   Subject: {spam.get('subject', 'No subject')}\n"
        else:
            response += "No spam emails found in the scanned messages."
        
        return {"response": response}
    except Exception as e:
        logger.error(f"Error handling delete_spam: {e}")
        return {"error": str(e)}


async def handle_categorize_emails(params: Dict) -> Dict:
    """Handle email categorization intent."""
    try:
        dry_run = params.get("dry_run", False)
        
        # Get first email account
        accounts = _load_email_accounts()
        if not accounts:
            return {"error": "No email accounts configured"}
        
        account_id = list(accounts.keys())[0]
        result = await categorize_emails(account_id=account_id, dry_run=dry_run)
        return {"response": result.get("response", "Email categorization completed")}
    except Exception as e:
        logger.error(f"Error handling categorize_emails: {e}")
        return {"error": str(e)}


async def handle_cleanup_emails(params: Dict) -> Dict:
    """Handle email cleanup intent."""
    try:
        dry_run = params.get("dry_run", False)
        
        # Get first email account
        accounts = _load_email_accounts()
        if not accounts:
            return {"error": "No email accounts configured"}
        
        account_id = list(accounts.keys())[0]
        result = await cleanup_inbox(account_id=account_id, dry_run=dry_run)
        return {"response": result.get("response", "Email cleanup completed")}
    except Exception as e:
        logger.error(f"Error handling cleanup_emails: {e}")
        return {"error": str(e)}
