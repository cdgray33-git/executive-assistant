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
from pydantic import BaseModel

# local helpers
try:
    # When run from server directory or as module
    from security import require_api_key
    from llm.ollama_adapter import OllamaAdapter
except ImportError:
    # When server is on path
    from server.security import require_api_key
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
    Simple chat endpoint that processes natural language requests.
    For demo purposes, this provides basic keyword matching to email functions.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt", "").lower()
        
        if not prompt:
            return {"response": "Please provide a message."}
        
        # Check if user is asking about emails
        if any(keyword in prompt for keyword in ["email", "mail", "inbox", "message"]):
            # Check if we have any email accounts configured
            accounts = await assistant_functions.list_email_accounts()
            
            if accounts.get("count", 0) == 0:
                return {
                    "response": "No email accounts are configured. Please add an email account first using the web interface or by calling the add_email_account function."
                }
            
            # Get the first account ID
            account_id = accounts.get("accounts", [])[0] if accounts.get("accounts") else None
            
            if not account_id:
                return {"response": "No email account found."}
            
            # Fetch unread emails
            if any(word in prompt for word in ["last", "recent", "unread", "show", "get", "fetch"]):
                max_msgs = 3
                if "5" in prompt or "five" in prompt:
                    max_msgs = 5
                elif "10" in prompt or "ten" in prompt:
                    max_msgs = 10
                
                result = await assistant_functions.fetch_unread_emails(account_id, max_messages=max_msgs)
                
                if "error" in result:
                    return {"response": f"Error fetching emails: {result['error']}"}
                
                messages = result.get("messages", [])
                if not messages:
                    return {"response": "No unread emails found."}
                
                response = f"You have {len(messages)} unread email(s):\n\n"
                for i, msg in enumerate(messages, 1):
                    response += f"{i}. From: {msg['from']}\n"
                    response += f"   Subject: {msg['subject']}\n"
                    response += f"   Preview: {msg['preview'][:100]}...\n\n"
                
                return {"response": response}
        
        # Generic response for non-email queries
        return {
            "response": "I can help you with email management, document generation, and more. Try asking:\n- 'Show me my last 3 emails'\n- 'Fetch my unread emails'\n\nOr use the API endpoints directly for document generation and other features."
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
