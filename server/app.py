"""
FastAPI application adapted for native macOS Ollama usage.

- Binds to localhost only
- Uses server/security.require_api_key to protect function endpoints
- Provides lightweight status & health endpoints for launchd checks
- Email management and document generation endpoints
"""
import os
import sys
import logging
from typing import Optional, Any, Dict, List

# Add parent directory to path to allow imports when running from server directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# local helpers - import each separately to handle different path scenarios
try:
    # When run from server directory
    from security import require_api_key
except ImportError:
    # When server is on path
    from server.security import require_api_key

try:
    # When run from server directory
    from llm.ollama_adapter import OllamaAdapter
except ImportError:
    # When server is on path
    from server.llm.ollama_adapter import OllamaAdapter

# Import assistant_functions - try local import first (when running from server dir), then absolute
try:
    import assistant_functions
except ImportError:
    from server import assistant_functions

logger = logging.getLogger("executive_assistant")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Executive Assistant API (native mac)")

# Restrict CORS to the local UI
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://127.0.0.1:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ollama adapter instance
ollama = OllamaAdapter()

# Mount static files for UI
ui_dir = os.path.join(parent_dir, "ui")
if os.path.exists(ui_dir):
    app.mount("/ui", StaticFiles(directory=ui_dir), name="ui")

# Request models for new endpoints
class BulkEmailCleanupRequest(BaseModel):
    account_id: str
    criteria: Dict[str, Any]
    dry_run: bool = True

class EmailCategorizationRequest(BaseModel):
    account_id: str
    max_messages: int = 100
    dry_run: bool = True

class SpamFilterRequest(BaseModel):
    account_id: str
    max_messages: int = 100
    delete: bool = False
    dry_run: bool = True

class PresentationRequest(BaseModel):
    title: str
    slides: List[Dict[str, Any]]
    output_filename: Optional[str] = None

class BriefingRequest(BaseModel):
    title: str
    summary: str
    key_points: List[str]
    action_items: List[str]
    format: str = "docx"

class DocumentRequest(BaseModel):
    doc_type: str
    title: str
    content: str
    format: str = "docx"

def verify_key(x_api_key: Optional[str] = Header(None)):
    """
    FastAPI dependency that verifies X-API-Key header using server.security.require_api_key.
    """
    require_api_key(x_api_key)


@app.get("/")
async def root():
    """Redirect root to UI or show welcome message."""
    ui_index = os.path.join(parent_dir, "ui", "index.html")
    if os.path.exists(ui_index):
        return FileResponse(ui_index)
    return {
        "message": "Executive Assistant API",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "models": "/api/models",
            "functions": "/api/functions",
            "function_call": "/api/function_call (POST)",
            "chat": "/api/chat (POST)",
            "ui": "/ui/ (if available)"
        }
    }


@app.get("/health")
async def health():
    """Service health endpoint suitable for launchd or supervisor checks."""
    healthy = ollama.ping()
    return {"status": "healthy" if healthy else "degraded", "ollama": healthy}


@app.get("/api/status")
async def api_status():
    return {"status": "ok", "host": "local", "user": os.environ.get("USER", "unknown")}


@app.get("/api/models", dependencies=[Depends(verify_key)])
async def api_models():
    """List models available to the local Ollama runtime. Requires API key if configured."""
    models = ollama.list_models()
    return {"models": models}


@app.post("/api/function_call", dependencies=[Depends(verify_key)])
async def function_call(payload: Dict[str, Any]):
    """
    Function-call endpoint that executes assistant functions.
    Routes calls to assistant_functions.execute_function().
    """
    try:
        name = payload.get("name") or payload.get("function_name")
        args = payload.get("arguments", {})
        if not name:
            return {"status": "error", "error": "function name required"}
        
        logger.info("Function call: %s %s", name, args)
        
        # Execute the function through assistant_functions module
        result = await assistant_functions.execute_function(name, args)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("function_call error")
        return {"status": "error", "error": str(e)}


@app.get("/api/functions", dependencies=[Depends(verify_key)])
async def list_functions():
    """List available assistant functions."""
    try:
        return {"functions": assistant_functions.get_function_info()}
    except Exception as e:
        logger.exception("list_functions error")
        return {"status": "error", "error": str(e)}


@app.post("/api/chat")
async def chat(request: Request):
    """
    Natural language chat endpoint with comprehensive NLP support for all assistant functions.
    Supports email management, calendar, contacts, document generation, and more.
    """
    try:
        data = await request.json()
        prompt_original = data.get("prompt", "").strip()
        prompt = prompt_original.lower()
        
        if not prompt:
            return {"response": "Please provide a message."}
        
        # === CALENDAR MANAGEMENT ===
        if any(word in prompt for word in ["calendar", "meeting", "schedule", "appointment", "event"]):
            # Adding a calendar event
            if any(action in prompt for action in ["add", "create", "schedule", "set up", "book"]):
                import re
                from datetime import datetime, timedelta
                
                # Extract email address if present
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt_original)
                email_addr = email_match.group(0) if email_match else None
                
                # Extract time
                time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?|(\d{1,2})\s*(am|pm)', prompt)
                meeting_time = None
                if time_match:
                    if time_match.group(4):  # Format like "2pm"
                        hour = int(time_match.group(4))
                        minute = 0
                        period = time_match.group(5)
                    else:  # Format like "1:30pm"
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2)) if time_match.group(2) else 0
                        period = time_match.group(3)
                    
                    if period:
                        if period == 'pm' and hour != 12:
                            hour += 12
                        elif period == 'am' and hour == 12:
                            hour = 0
                    meeting_time = f"{hour:02d}:{minute:02d}"
                
                # Extract date
                meeting_date = None
                if "tomorrow" in prompt:
                    meeting_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                elif "today" in prompt:
                    meeting_date = datetime.now().strftime("%Y-%m-%d")
                elif "next week" in prompt:
                    meeting_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                
                # Extract meeting title
                title = "Meeting"
                if email_addr:
                    name = email_addr.split('@')[0].replace('.', ' ').title()
                    title = f"Meeting with {name}"
                
                description = f"Scheduled via Executive Assistant"
                if email_addr:
                    description += f"\nAttendee: {email_addr}"
                
                # Create the calendar event
                if meeting_date:
                    result = await assistant_functions.add_calendar_event(
                        title=title,
                        date=meeting_date,
                        time=meeting_time,
                        description=description
                    )
                    
                    response = f"✓ Calendar event created: {title}\n"
                    response += f"  Date: {meeting_date}\n"
                    if meeting_time:
                        response += f"  Time: {meeting_time}\n"
                    
                    # Add to contacts if email provided
                    if email_addr:
                        contact_name = email_addr.split('@')[0].replace('.', ' ').title()
                        await assistant_functions.add_contact(
                            name=contact_name,
                            email=email_addr,
                            notes=f"Added from calendar meeting on {meeting_date}"
                        )
                        response += f"\n✓ Contact added: {contact_name} ({email_addr})"
                    
                    # Send email invitation if requested
                    if email_addr and any(word in prompt for word in ["send", "email", "invite"]):
                        accounts = await assistant_functions.list_email_accounts()
                        if accounts.get("count", 0) > 0:
                            account_id = accounts.get("accounts", [])[0]
                            subject = f"Meeting Invitation: {title}"
                            body = f"You're invited to a meeting.\n\nDate: {meeting_date}\n"
                            if meeting_time:
                                body += f"Time: {meeting_time}\n"
                            body += f"\nPlease let me know if this time works for you."
                            
                            await assistant_functions.send_email(
                                account_id=account_id,
                                to=email_addr,
                                subject=subject,
                                body=body
                            )
                            response += f"\n\n✓ Meeting invitation sent to {email_addr}"
                    
                    return {"response": response}
                else:
                    return {"response": "I couldn't determine the date. Please specify 'tomorrow', 'today', or a specific date."}
            
            # Viewing calendar
            elif any(action in prompt for word in ["show", "view", "get", "list", "what"]):
                days = 7
                if "today" in prompt:
                    days = 1
                elif "week" in prompt:
                    days = 7
                elif "month" in prompt:
                    days = 30
                
                result = await assistant_functions.get_calendar(days=days)
                events = result.get("events", [])
                
                if not events:
                    return {"response": f"No events scheduled for the next {days} day(s)."}
                
                response = f"Calendar events for the next {days} day(s):\n\n"
                for event in events:
                    response += f"• {event['title']}\n  {event['date']}"
                    if event.get('time'):
                        response += f" at {event['time']}"
                    response += "\n"
                    if event.get('description'):
                        response += f"  {event['description']}\n"
                    response += "\n"
                
                return {"response": response}
        
        # === CONTACTS MANAGEMENT ===
        if any(word in prompt for word in ["contact", "phone", "address"]):
            # Adding a contact
            if any(action in prompt for action in ["add", "create", "save", "new"]):
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt_original)
                email_addr = email_match.group(0) if email_match else None
                
                phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', prompt_original)
                phone_num = phone_match.group(0) if phone_match else None
                
                name = None
                if email_addr:
                    name = email_addr.split('@')[0].replace('.', ' ').title()
                
                if name and (email_addr or phone_num):
                    result = await assistant_functions.add_contact(
                        name=name,
                        email=email_addr,
                        phone=phone_num,
                        notes="Added via chat"
                    )
                    response = f"✓ Contact added: {name}\n"
                    if email_addr:
                        response += f"  Email: {email_addr}\n"
                    if phone_num:
                        response += f"  Phone: {phone_num}"
                    return {"response": response}
                else:
                    return {"response": "Please provide a name and either email or phone number."}
            
            # Searching contacts
            elif any(action in prompt for action in ["search", "find", "look", "show", "get"]):
                words = prompt.split()
                query = " ".join(words[-2:]) if len(words) >= 2 else ""
                
                result = await assistant_functions.search_contacts(query=query)
                contacts = result.get("contacts", [])
                
                if not contacts:
                    return {"response": f"No contacts found matching '{query}'."}
                
                response = f"Found {len(contacts)} contact(s):\n\n"
                for contact in contacts:
                    response += f"• {contact['name']}\n"
                    if contact.get('email'):
                        response += f"  Email: {contact['email']}\n"
                    if contact.get('phone'):
                        response += f"  Phone: {contact['phone']}\n"
                    response += "\n"
                
                return {"response": response}
        
        # === EMAIL SENDING ===
        if any(phrase in prompt for phrase in ["send email", "send an email", "email to", "write email", "compose email"]):
            import re
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', prompt_original)
            recipient = email_match.group(0) if email_match else None
            
            if recipient:
                accounts = await assistant_functions.list_email_accounts()
                if accounts.get("count", 0) == 0:
                    return {"response": "No email accounts configured. Please add an email account first."}
                
                account_id = accounts.get("accounts", [])[0]
                subject = f"Message from Executive Assistant"
                body = f"This is an automated message sent via Executive Assistant."
                
                content_match = re.search(r'(?:about|regarding|re:|subject:)\s+(.+)', prompt)
                if content_match:
                    subject = content_match.group(1).strip().title()
                
                result = await assistant_functions.send_email(
                    account_id=account_id,
                    to=recipient,
                    subject=subject,
                    body=body
                )
                
                if "error" in result:
                    return {"response": f"Error sending email: {result['error']}"}
                
                return {"response": f"✓ Email sent to {recipient}\nSubject: {subject}"}
            else:
                return {"response": "Please specify a recipient email address."}
        
        # === DOCUMENT GENERATION ===
        if any(word in prompt for word in ["powerpoint", "presentation", "slides", "ppt"]):
            if any(action in prompt for action in ["create", "generate", "make", "build"]):
                import re
                title_match = re.search(r'(?:about|on|for|titled|called)\s+["\']?([^"\']+)["\']?', prompt)
                title = title_match.group(1).strip().title() if title_match else "Presentation"
                
                slides = [
                    {"title": title, "content": "Created by Executive Assistant"},
                    {"title": "Overview", "content": "This presentation was automatically generated."}
                ]
                
                result = await assistant_functions.generate_presentation(
                    title=title,
                    slides=slides
                )
                
                if "error" in result:
                    return {"response": f"Error: {result['error']}"}
                
                filename = result.get("filename", "presentation.pptx")
                return {"response": f"✓ PowerPoint created: {filename}\n\nTitle: {title}\nSlides: {len(slides)}\n\nLocation: outputs/presentations/"}
        
        if any(word in prompt for word in ["briefing", "report", "document", "memo"]):
            if any(action in prompt for action in ["create", "generate", "make", "write", "draft"]):
                import re
                title_match = re.search(r'(?:about|on|for|titled|called)\s+["\']?([^"\']+)["\']?', prompt)
                title = title_match.group(1).strip().title() if title_match else "Document"
                
                if "briefing" in prompt:
                    result = await assistant_functions.create_briefing(
                        title=title,
                        summary="This briefing was created by Executive Assistant.",
                        key_points=["Key point 1", "Key point 2"],
                        action_items=["Action item 1"],
                        format="docx"
                    )
                elif "memo" in prompt:
                    result = await assistant_functions.write_document(
                        doc_type="memo",
                        title=title,
                        content="This memo was created by Executive Assistant.",
                        format="docx"
                    )
                else:
                    result = await assistant_functions.write_document(
                        doc_type="report",
                        title=title,
                        content="This report was created by Executive Assistant.",
                        format="docx"
                    )
                
                if "error" in result:
                    return {"response": f"Error: {result['error']}"}
                
                filename = result.get("filename", "document.docx")
                return {"response": f"✓ Document created: {filename}\n\nTitle: {title}\n\nLocation: outputs/documents/"}
        
        # === NOTES ===
        if any(word in prompt for word in ["note", "remind", "remember"]):
            if any(action in prompt for action in ["take", "save", "write", "add", "create"]):
                content = prompt_original
                title = None
                
                import re
                title_match = re.search(r'(?:titled|called|named)\s+["\']?([^"\']+)["\']?', prompt)
                if title_match:
                    title = title_match.group(1).strip()
                
                result = await assistant_functions.take_notes(content=content, title=title)
                return {"response": f"✓ Note saved{' as: ' + title if title else ''}"}
            
            elif any(action in prompt for action in ["show", "get", "list", "view"]):
                result = await assistant_functions.get_notes()
                notes = result.get("notes", [])
                
                if not notes:
                    return {"response": "No notes found."}
                
                response = f"Your notes ({len(notes)}):\n\n"
                for note in notes[:10]:
                    response += f"• {note.get('title', 'Untitled')}\n"
                    preview = note.get('content', '')[:100]
                    response += f"  {preview}{'...' if len(note.get('content', '')) > 100 else ''}\n\n"
                
                return {"response": response}
        
        # === EMAIL MANAGEMENT ===
        if any(keyword in prompt for keyword in ["email", "mail", "inbox", "message", "spam"]):
            accounts = await assistant_functions.list_email_accounts()
            
            if accounts.get("count", 0) == 0:
                return {"response": "No email accounts configured. Please add an email account first."}
            
            account_id = accounts.get("accounts", [])[0] if accounts.get("accounts") else None
            
            if not account_id:
                return {"response": "No email account found."}
            
            # Spam filtering and deletion
            if any(word in prompt for word in ["spam", "junk"]):
                older_than_days = None
                if "6 month" in prompt or "six month" in prompt:
                    older_than_days = 180
                elif "year" in prompt or "12 month" in prompt:
                    older_than_days = 365
                elif "month" in prompt:
                    import re
                    match = re.search(r'(\d+)\s*month', prompt)
                    if match:
                        older_than_days = int(match.group(1)) * 30
                elif "day" in prompt:
                    import re
                    match = re.search(r'(\d+)\s*day', prompt)
                    if match:
                        older_than_days = int(match.group(1))
                
                # Check if this is a deletion command or just viewing
                is_delete_command = any(action in prompt for action in ["delete", "remove", "clean"]) and not any(phrase in prompt for phrase in ["can you", "would you", "could you"])
                
                if older_than_days:
                    criteria = {
                        "older_than_days": older_than_days,
                        "folder": "INBOX"
                    }
                    result = await assistant_functions.bulk_delete_emails(account_id, criteria, dry_run=not is_delete_command)
                    
                    if "error" in result:
                        return {"response": f"Error: {result['error']}"}
                    
                    if not is_delete_command:
                        return {"response": f"I found {result.get('would_delete', 0)} emails older than {older_than_days} days. To delete them, say 'Delete all spam older than {older_than_days} days'."}
                    else:
                        return {"response": f"✓ Deleted {result.get('deleted_count', 0)} emails older than {older_than_days} days."}
                else:
                    max_msgs = 100
                    if "all" in prompt:
                        max_msgs = 500
                    elif "10" in prompt or "ten" in prompt:
                        max_msgs = 10
                    
                    # For spam, always use detect_spam to identify spam messages
                    delete = is_delete_command
                    result = await assistant_functions.detect_spam(account_id, max_messages=max_msgs, delete=delete, dry_run=not delete)
                    
                    if "error" in result:
                        return {"response": f"Error: {result['error']}"}
                    
                    spam_count = result.get("spam_count", 0)
                    spam_messages = result.get("spam_messages", [])
                    
                    if not delete:
                        # Show the spam messages
                        if spam_count == 0:
                            return {"response": "No spam messages found."}
                        
                        response = f"Found {spam_count} spam message(s):\n\n"
                        for i, msg in enumerate(spam_messages[:10], 1):
                            response += f"{i}. From: {msg.get('from', 'Unknown')}\n"
                            response += f"   Subject: {msg.get('subject', 'No subject')}\n"
                            if msg.get('preview'):
                                response += f"   Preview: {msg['preview'][:100]}...\n"
                            response += "\n"
                        
                        if spam_count > 10:
                            response += f"... and {spam_count - 10} more spam messages.\n\n"
                        
                        response += "To delete them, say 'Delete the spam from my inbox'."
                        return {"response": response}
                    else:
                        return {"response": f"✓ Deleted {spam_count} spam messages."}
            
            # Email categorization
            if any(word in prompt for word in ["categorize", "organize", "sort", "folder"]):
                dry_run = any(phrase in prompt for phrase in ["can you", "would you"])
                result = await assistant_functions.categorize_emails(account_id, max_messages=100, dry_run=dry_run)
                
                if "error" in result:
                    return {"response": f"Error: {result['error']}"}
                
                categorized = result.get("categorized", {})
                response = "✓ Email categorization complete:\n\n"
                for category, count in categorized.items():
                    response += f"• {category}: {count} emails\n"
                
                return {"response": response}
            
            # Fetch unread emails
            if any(word in prompt for word in ["last", "recent", "unread", "show", "get", "fetch"]):
                max_msgs = 3
                if "5" in prompt or "five" in prompt:
                    max_msgs = 5
                elif "10" in prompt or "ten" in prompt:
                    max_msgs = 10
                
                result = await assistant_functions.fetch_unread_emails(account_id, max_messages=max_msgs)
                
                if "error" in result:
                    return {"response": f"Error: {result['error']}"}
                
                messages = result.get("messages", [])
                if not messages:
                    return {"response": "No unread emails found."}
                
                response = f"You have {len(messages)} unread email(s):\n\n"
                for i, msg in enumerate(messages, 1):
                    response += f"{i}. From: {msg['from']}\n"
                    response += f"   Subject: {msg['subject']}\n"
                    response += f"   Preview: {msg['preview'][:100]}...\n\n"
                
                return {"response": response}
        
        # Generic help message
        return {
            "response": "I'm your Executive Assistant. I can help you with:\n\n" +
                       "📧 Email: 'Show my last 5 emails', 'Delete all spam'\n" +
                       "📅 Calendar: 'Schedule meeting with john@example.com tomorrow at 2pm'\n" +
                       "👥 Contacts: 'Add contact john@example.com'\n" +
                       "📄 Documents: 'Create a PowerPoint about Q4 results'\n" +
                       "📝 Notes: 'Take a note: Remember to...'\n\n" +
                       "What would you like me to help you with?"
        }
        
    except Exception as e:
        logger.exception("chat error")
        return {"response": f"Error: {str(e)}"}


# Email management endpoints
@app.post("/api/email/bulk_cleanup", dependencies=[Depends(verify_key)])
async def bulk_email_cleanup(request: BulkEmailCleanupRequest):
    """Bulk delete emails based on criteria."""
    try:
        result = await assistant_functions.bulk_delete_emails(
            request.account_id,
            request.criteria,
            request.dry_run
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("bulk_cleanup error")
        return {"status": "error", "error": str(e)}


@app.post("/api/email/categorize", dependencies=[Depends(verify_key)])
async def categorize_emails(request: EmailCategorizationRequest):
    """Auto-categorize emails into folders."""
    try:
        result = await assistant_functions.categorize_emails(
            request.account_id,
            request.max_messages,
            request.dry_run
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("categorize error")
        return {"status": "error", "error": str(e)}


@app.post("/api/email/spam_filter", dependencies=[Depends(verify_key)])
async def spam_filter(request: SpamFilterRequest):
    """Detect and optionally delete spam emails."""
    try:
        result = await assistant_functions.detect_spam(
            request.account_id,
            request.max_messages,
            request.delete,
            request.dry_run
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("spam_filter error")
        return {"status": "error", "error": str(e)}


@app.post("/api/email/cleanup_inbox", dependencies=[Depends(verify_key)])
async def cleanup_inbox(account_id: str, dry_run: bool = True):
    """Automated inbox cleanup workflow."""
    try:
        result = await assistant_functions.cleanup_inbox(account_id, dry_run)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("cleanup_inbox error")
        return {"status": "error", "error": str(e)}


# Document generation endpoints
@app.post("/api/generate_presentation", dependencies=[Depends(verify_key)])
async def generate_presentation(request: PresentationRequest):
    """Generate PowerPoint presentation."""
    try:
        result = await assistant_functions.generate_presentation(
            request.title,
            request.slides,
            request.output_filename
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("generate_presentation error")
        return {"status": "error", "error": str(e)}


@app.post("/api/create_briefing", dependencies=[Depends(verify_key)])
async def create_briefing(request: BriefingRequest):
    """Create briefing document."""
    try:
        result = await assistant_functions.create_briefing(
            request.title,
            request.summary,
            request.key_points,
            request.action_items,
            request.format
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("create_briefing error")
        return {"status": "error", "error": str(e)}


@app.post("/api/write_document", dependencies=[Depends(verify_key)])
async def write_document(request: DocumentRequest):
    """Create formatted document."""
    try:
        result = await assistant_functions.write_document(
            request.doc_type,
            request.title,
            request.content,
            request.format
        )
        return {"status": "success", "result": result}
    except Exception as e:
        logger.exception("write_document error")
        return {"status": "error", "error": str(e)}
