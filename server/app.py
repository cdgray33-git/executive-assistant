"""
Updated FastAPI application with Phase 3 integration
Location: server/app.py (REPLACE EXISTING)
"""
import os
import logging
from logging.handlers import RotatingFileHandler
import os
import json
from pathlib import Path
from typing import Optional, Any, Dict, List

import uuid

from fastapi import FastAPI, Request, Header, Depends, HTTPException
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# local helpers
from server.security import require_api_key
from server.llm.ollama_adapter import OllamaAdapter
from server.connectors.yahoo_connector import YahooConnector
from server.spam_detector import SpamDetector
from server.agent import ExecutiveAgent

# Initialize agent
agent = ExecutiveAgent()

# Conversation Memory (optional - requires PostgreSQL)
try:
    from server.managers.conversation_memory import ConversationMemory
    conversation_memory = ConversationMemory()
    HAS_MEMORY = True
    print("✅ Conversation memory enabled")
except Exception as e:
    print(f"⚠️  Conversation memory disabled: {e}")
    conversation_memory = None
    HAS_MEMORY = False


# Phase 2: Assistant functions
from server import assistant_functions

# Phase 3: Account management
from server.managers.account_manager import AccountManager

logger = logging.getLogger("executive_assistant")
logging.basicConfig(level=logging.INFO)

# # Setup file logging for debugging
# os.makedirs("logs", exist_ok=True)
# file_handler = RotatingFileHandler(
#     "logs/jarvis.log",
#     maxBytes=10*1024*1024,  # 10MB
#     backupCount=5
# )
# file_handler.setFormatter(logging.Formatter(
#     "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# ))
# logging.getLogger().addHandler(file_handler)

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


@app.on_event("startup")
async def startup_cleanup():
    """Clear stuck organization records on server start"""
    from server.database.connection import get_db_session
    from sqlalchemy import text
    try:
        with get_db_session() as session:
            result = session.execute(text("""
                UPDATE email_organization_progress 
                SET status = 'error', last_error = 'Server restarted'
                WHERE status = 'running' 
                AND last_update < NOW() - INTERVAL '1 hour'
            """))
            if result.rowcount > 0:
                logger.info(f"Cleaned up {result.rowcount} stuck organization record(s)")
    except Exception as e:
        logger.error(f"Startup cleanup failed: {e}")
# Service instances

@app.on_event("startup")
async def startup_monitors():
    """Start background email monitoring services"""
    import asyncio
    from server.services.email_monitor import EmailMonitor
    from server.services.meeting_response_monitor import MeetingResponseMonitor
    from server.intelligence.context_engine import ContextEngine
    
    try:
        context_engine = ContextEngine()
        email_monitor = EmailMonitor(account_mgr, email_manager_instance, context_engine, poll_interval=180)
        meeting_monitor = MeetingResponseMonitor(email_manager_instance, poll_interval=180)
        asyncio.create_task(email_monitor.start())
        asyncio.create_task(meeting_monitor.start())
        logger.info("✅ Email monitors started! Polling every 3 minutes.")
    except Exception as e:
        logger.error(f"Failed to start monitors: {e}")
ollama = OllamaAdapter()
spam_detector = SpamDetector()
account_mgr = AccountManager()


def verify_key(x_api_key: Optional[str] = Header(None)):
    """FastAPI dependency that verifies X-API-Key header"""
    require_api_key(x_api_key)


# ==================== PYDANTIC MODELS ====================

# Legacy models (Phase 1)
class ConnectRequest(BaseModel):
    account_id: str

class CategorizeRequest(BaseModel):
    emails: List[Dict]

class DeleteRequest(BaseModel):
    account_id: str
    email_ids: List[str]
    permanent: bool = False

# Phase 3 models
class AddAccountOAuthRequest(BaseModel):
    account_id: str
    provider: str  # 'gmail' or 'hotmail'
    email: str
    client_id: str
    client_secret: str

class AddAccountPasswordRequest(BaseModel):
    account_id: str
    provider: str  # 'yahoo', 'comcast', or 'apple'
    email: str
    app_password: str

class RemoveAccountRequest(BaseModel):
    account_id: str


# ==================== HEALTH & STATUS ENDPOINTS ====================

@app.get("/health")
async def health():
    """Service health endpoint"""
    healthy = ollama.ping()
    return {
        "status": "healthy" if healthy else "degraded",
        "ollama": healthy,
        "accounts_configured": len(account_mgr.vault.list_accounts())
    }


@app.get("/api/status")
async def api_status():
    return {
        "status": "ok",
        "host": "local",
        "user": os.environ.get("USER", "unknown"),
        "functions_available": len(assistant_functions.FUNCTION_REGISTRY),
        "accounts": len(account_mgr.vault.list_accounts()),
        "phase": "3 - Multi-email connectors"
    }


@app.get("/api/models", dependencies=[Depends(verify_key)])
async def api_models():
    """List models available to Ollama"""
    models = ollama.list_models()
    return {"models": models}


# ==================== FUNCTION CALLING ENDPOINT ====================

@app.post("/api/function_call", dependencies=[Depends(verify_key)])
async def function_call(payload: Dict[str, Any]):
    """
    Central function calling endpoint - routes to all EA capabilities
    """
    try:
        name = payload.get("name") or payload.get("function_name")
        args = payload.get("arguments", {})
        
        if not name:
            return {"status": "error", "error": "function name required"}
        
        logger.info(f"Function call: {name} with args: {args}")
        
        # Execute function via assistant_functions router
        result = await assistant_functions.execute_function(name, args)
        
        return result
        
    except Exception as e:
        logger.exception("function_call error")
        return {"status": "error", "error": str(e)}


@app.get("/api/functions")
async def list_functions():
    """List all available EA functions"""
    return {
        "status": "success",
        "functions": assistant_functions.get_function_info(),
        "count": len(assistant_functions.FUNCTION_REGISTRY)
    }


# ==================== ACCOUNT MANAGEMENT ENDPOINTS (Phase 3) ====================

@app.post("/api/accounts/add/oauth", dependencies=[Depends(verify_key)])
async def add_account_oauth(request: AddAccountOAuthRequest):
    """
    Add an OAuth2-based email account (Gmail or Hotmail)
    This will open a browser window for authorization
    """
    try:
        result = account_mgr.add_account_oauth(
            account_id=request.account_id,
            provider=request.provider,
            email=request.email,
            client_id=request.client_id,
            client_secret=request.client_secret
        )
        return result
    except Exception as e:
        logger.error(f"Add OAuth account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/add/password", dependencies=[Depends(verify_key)])
async def add_account_password(request: AddAccountPasswordRequest):
    """
    Add a password-based email account (Yahoo, Comcast, Apple)
    """
    try:
        result = account_mgr.add_account_password(
            account_id=request.account_id,
            provider=request.provider,
            email=request.email,
            app_password=request.app_password
        )
        return result
    except Exception as e:
        logger.error(f"Add password account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/accounts/{account_id}", dependencies=[Depends(verify_key)])
async def remove_account(account_id: str):
    """Remove an email account"""
    try:
        result = account_mgr.remove_account(account_id)
        return result
    except Exception as e:
        logger.error(f"Remove account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts", dependencies=[Depends(verify_key)])
async def list_accounts():
    """List all configured email accounts"""
    try:
        result = account_mgr.list_accounts()
        return result
    except Exception as e:
        logger.error(f"List accounts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/test", dependencies=[Depends(verify_key)])
async def test_all_accounts():
    """Test connectivity for all accounts"""
    try:
        result = account_mgr.test_all_accounts()
        return result
    except Exception as e:
        logger.error(f"Test accounts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LEGACY EMAIL ENDPOINTS (Phase 1 - Testing) ====================

@app.post("/api/email/connect")
async def connect_email(request: ConnectRequest):
    """Legacy: Test connection to Yahoo account"""
    try:
        # This endpoint now uses account manager
        connector = account_mgr.get_connector(request.account_id, cache=False)
        success, message = connector.connect()
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        stats = connector.get_mailbox_stats()
        connector.disconnect()
        
        return {
            "success": True,
            "account_id": request.account_id,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/email/preview")
async def preview_emails(account_id: str, count: int = 100, oldest_first: bool = True):
    """Legacy: Preview emails from inbox"""
    try:
        connector = account_mgr.get_connector(account_id, cache=False)
        success, message = connector.connect()
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        emails = connector.preview_emails(count=count, oldest_first=oldest_first)
        connector.disconnect()
        
        return {
            "success": True,
            "count": len(emails),
            "emails": emails
        }
    except Exception as e:
        logger.error(f"Preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/categorize")
async def categorize_emails(request: CategorizeRequest):
    """Legacy: Use AI to categorize emails"""
    try:
        categorized = spam_detector.batch_categorize(request.emails)
        
        spam_count = sum(1 for e in categorized if e.get("category") == "spam")
        keep_count = sum(1 for e in categorized if e.get("category") == "keep")
        unsure_count = sum(1 for e in categorized if e.get("category") == "unsure")
        
        return {
            "success": True,
            "total": len(categorized),
            "spam_count": spam_count,
            "keep_count": keep_count,
            "unsure_count": unsure_count,
            "emails": categorized
        }
    except Exception as e:
        logger.error(f"Categorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/delete")
async def delete_emails(request: DeleteRequest):
    """Legacy: Delete specified emails"""
    try:
        connector = account_mgr.get_connector(request.account_id, cache=False)
        success, message = connector.connect()
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        result = connector.delete_emails(
            email_ids=request.email_ids,
            permanent=request.permanent
        )
        
        connector.disconnect()
        return result
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/email/stats")


# ============================================
# MAILBOX ORGANIZATION ENDPOINTS
# ============================================


async def run_organization_loop(user_id: str, account_id: str):
    logger.info(f"🔄 Organization loop STARTED for {account_id}")
    """Background task to process organization batches"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    import asyncio
    
    organizer = MailboxOrganizer()
    
    
    while True:
        try:
            logger.info(f"🔄 Loop iteration for {account_id}, status check...")
            # Check if still running
            status = organizer.get_progress(user_id, account_id)
            logger.info(f"🔄 Loop iteration for {account_id}, status: {status.get("status")}, {status.get("processed_count")}/{status.get("total_emails")}")
            
            # Exit if completed, cancelled, error, or fully processed
            if status.get("status") not in ["running"]:
                logger.info(f"Organization stopped for {account_id} - status: {status.get("status")}")
                break
            
            if status.get("processed_count", 0) >= status.get("total_emails", 0) and status.get("total_emails", 0) > 0:
                logger.info(f"Organization auto-completed for {account_id} - all emails processed")
                organizer._update_progress(user_id, account_id, {"status": "completed", "completed_at": datetime.now()})
                break
            
            # Process next batch
            result = await organizer.process_batch(user_id, account_id)
            
            if result.get("status") == "completed":
                logger.info(f"Organization completed for {account_id}")
                break
            
            # Wait before next batch
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Organization loop error for {account_id}: {e}")
            break


@app.post("/api/email/organize/start", dependencies=[Depends(verify_key)])
async def start_organization(background_tasks: BackgroundTasks, account_id: str, batch_size: int = 3000, user_id: str = "default_user"):
    """Start mailbox organization for an account"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    
    # Clean up any stuck records for this account
    logger.info(f"🧹 Checking for stuck organization records for {account_id}...")
    try:
        from server.database.connection import get_db_session
        from sqlalchemy import text
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE email_organization_progress 
                    SET status = 'cancelled', completed_at = NOW(), spam_count = 0, keep_count = 0, moved_count = 0, unsure_count = 0, processed_count = 0 
                    WHERE account_id = :account_id 
                    AND status IN ('running', 'starting') 
                    AND user_id = :user_id
                """),
                {"account_id": account_id, "user_id": user_id}
            )
            session.commit()
            if result.rowcount > 0:
                logger.info(f"✅ Cancelled {result.rowcount} stuck record(s) for {account_id}")
    except Exception as e:
        logger.warning(f"Cleanup failed (non-critical): {e}")
    result = organizer.start_organization(user_id, account_id, batch_size)
    if result.get("status") == "success":
        background_tasks.add_task(run_organization_loop, user_id, account_id)
    return result


@app.post("/api/email/organize/pause", dependencies=[Depends(verify_key)])
async def pause_organization(account_id: str, user_id: str = "default_user"):
    """Pause ongoing organization"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    

    return organizer.pause_organization(user_id, account_id)

@app.post("/api/email/organize/cancel", dependencies=[Depends(verify_key)])
async def cancel_organization(account_id: str, user_id: str = "default_user"):
    """Cancel organization (not resumable)"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    
    return organizer.cancel_organization(user_id, account_id)


@app.post("/api/email/organize/retry", dependencies=[Depends(verify_key)])
async def retry_organization(account_id: str, user_id: str = "default_user"):
    """Retry organization after error"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    
    return organizer.retry_organization(user_id, account_id)


@app.get("/api/email/organize/status/{account_id}", dependencies=[Depends(verify_key)])
async def get_organization_status(account_id: str, user_id: str = "default_user"):
    """Get organization progress for specific account"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    
    progress = organizer.get_progress(user_id, account_id)
    if not progress:
        return {"status": "not_started", "message": "No organization in progress"}
    return progress


@app.get("/api/email/organize/status", dependencies=[Depends(verify_key)])
async def get_all_organization_status(user_id: str = "default_user"):
    """Get organization status for all accounts"""
    from server.managers.mailbox_organizer import MailboxOrganizer
    organizer = MailboxOrganizer()
    
    return {"accounts": organizer.get_all_progress(user_id)}

async def get_email_stats(account_id: str):
    """Legacy: Get mailbox statistics"""
    try:
        connector = account_mgr.get_connector(account_id, cache=False)
        success, message = connector.connect()
        
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        stats = connector.get_mailbox_stats()
        connector.disconnect()
        
        return {
            "success": True,
            "account_id": account_id,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CHAT ENDPOINT (JARVIS Interface) ====================

class ChatRequest(BaseModel):
    message: str
    reset: bool = False

@app.post("/api/chat", dependencies=[Depends(verify_key)])
async def chat_with_agent(request: ChatRequest):
    """Chat with JARVIS - WITH CONVERSATION MEMORY"""
    try:
        user_config = get_config()
        user_id = user_config.get("user_name", "default_user")
        session_id = str(uuid.uuid4())
        
        if request.reset:
            agent.reset_conversation()
            if conversation_memory: conversation_memory.store_conversation(user_id, session_id, "system", "Conversation reset")
            return {"status": "success", "message": "Conversation reset. How can I help you?", "session_id": session_id}
        
        if conversation_memory: conversation_memory.store_conversation(user_id, session_id, "user", request.message)
        result = await agent.chat(request.message)
        if conversation_memory: conversation_memory.store_conversation(user_id, session_id, "assistant", result.get("response", ""), function_calls=result.get("function_calls"))
        
        return {"status": "success", "session_id": session_id, **result}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
async def get_chat_history():
    """Get conversation history"""
    return {
        "status": "success",
        "history": agent.conversation_history,
        "count": len(agent.conversation_history)
    }


# Serve React UI

# ==================== CONFIG ENDPOINTS ====================

from server.config import get_config, save_config, update_config, reset_config

@app.get("/api/config")
async def get_user_config():
    """Get user configuration (EA name, preferences, etc.)"""
    try:
        config = get_config()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        logger.error(f"Get config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ConfigUpdateRequest(BaseModel):
    ea_name: Optional[str] = None
    user_name: Optional[str] = None
    banner_text: Optional[str] = None
    model: Optional[str] = None
    auto_cleanup: Optional[Dict] = None
    ui_preferences: Optional[Dict] = None


@app.post("/api/config")
async def update_user_config(request: ConfigUpdateRequest):
    """Update user configuration"""
    try:
        updates = request.dict(exclude_none=True)
        config = update_config(updates)
        return {
            "status": "success",
            "config": config,
            "message": "Configuration updated successfully"
        }
    except Exception as e:
        logger.error(f"Update config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reset")
async def reset_user_config():
    """Reset configuration to defaults"""
    try:
        config = reset_config()
        return {
            "status": "success",
            "config": config,
            "message": "Configuration reset to defaults"
        }
    except Exception as e:
        logger.error(f"Reset config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ASSISTANT COMMAND ENDPOINT ====================

class AssistantCommandRequest(BaseModel):
    command: str
    attachment: Optional[Dict] = None


@app.post("/api/assistant/command", dependencies=[Depends(verify_key)])
async def assistant_command(request: AssistantCommandRequest):
    """
    Unified NLP command interface with optional file attachment
    Examples: "clean my spam", "check email", "edit this presentation"
    """
    try:
        # Get user config and generate session ID
        user_config = get_config()
        user_id = user_config.get("user_name", "default_user")
        session_id = str(uuid.uuid4())

        # Handle reset
        if hasattr(request, 'reset') and request.reset:
            agent.reset_conversation()
            if conversation_memory:
                conversation_memory.store_conversation(user_id, session_id, "system", "Conversation reset")
            return {"status": "success", "message": "Conversation reset", "session_id": session_id}

        # Store user message
        if conversation_memory:
            conversation_memory.store_conversation(user_id, session_id, "user", request.command)

        # Process request
        if request.attachment:
            result = await agent.chat_with_attachment(request.command, request.attachment)
        else:
            result = await agent.chat(request.command)

        # Store assistant response
        if conversation_memory:
            conversation_memory.store_conversation(
                user_id, session_id, "assistant",
                result.get("response", ""),
                function_calls=result.get("function_calls")
            )

        return {
            "status": "success",
            "session_id": session_id,
            **result
        }
    except Exception as e:
        logger.info(f"Returning to UI: status={result.get('status')}, has_drafts={'drafts_created' in result}")
        logger.error(f"Assistant command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== Email Draft Management Endpoints =====
from server.draft_manager import draft_manager
from server.managers.email_manager import EmailManager

email_manager_instance = EmailManager()

@app.get("/api/drafts/pending", dependencies=[Depends(verify_key)])
async def get_pending_drafts():
    """Get all pending email drafts"""
    return {"drafts": draft_manager.list_pending()}

@app.post("/api/drafts/approve", dependencies=[Depends(verify_key)])
async def approve_draft(request: dict):
    """Approve and send a draft email"""
    draft_id = request.get("draft_id")
    
    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id required")
    
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft_manager.approve_draft(draft_id)
    
    try:
        result = email_manager_instance.send_email(
            to=draft["to"],
            subject=draft["subject"],
            body=draft["body"],
            from_account=draft["from_account"],
            cc=draft.get("cc"),
            bcc=draft.get("bcc")
        )
        
        draft_manager.delete_draft(draft_id)
        
        return {
            "status": "success",
            "message": "Email sent successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to send approved email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drafts/reject", dependencies=[Depends(verify_key)])
async def reject_draft(request: dict):
    """Reject and delete a draft email"""
    draft_id = request.get("draft_id")
    
    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id required")
    
    if draft_manager.delete_draft(draft_id):
        return {"status": "success", "message": "Draft deleted"}
    else:
        raise HTTPException(status_code=404, detail="Draft not found")

@app.post("/api/drafts/edit", dependencies=[Depends(verify_key)])
async def edit_draft(request: dict):
    """Edit a draft email"""
    draft_id = request.get("draft_id")
    updates = request.get("updates", {})
    
    if not draft_id:
        raise HTTPException(status_code=400, detail="draft_id required")
    
    draft = draft_manager.get_draft(draft_id)
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    for field in ["subject", "body", "to", "cc", "bcc"]:
        if field in updates:
            draft[field] = updates[field]
    
    return {"status": "success", "draft": draft}


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

ui_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui-build", "dist")

if os.path.exists(ui_dist):
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(ui_dist, "assets")), name="assets")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_ui():
        return FileResponse(os.path.join(ui_dist, "index.html"))

# ==================== MEETINGS API ====================

@app.get("/api/meetings")
async def get_meetings(
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    x_api_key: Optional[str] = Header(None)
):
    """
    Get meetings with optional filters
    
    Query params:
        status: Filter by status (scheduled, confirmed, cancelled)
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
    """
    try:
        verify_key(x_api_key)
        
        from server.database.connection import get_db_session
        from sqlalchemy import text
        
        query = """
            SELECT id, event_id, title, date, time, duration, 
                   attendees, status, response_status, attendee_responses,
                   description, created_at
            FROM meetings
            WHERE 1=1
        """
        params = {}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        if start_date:
            query += " AND date >= :start_date"
            params["start_date"] = start_date
        
        if end_date:
            query += " AND date <= :end_date"
            params["end_date"] = end_date
        
        query += " ORDER BY date, time"
        
        with get_db_session() as db:
            meetings = db.execute(text(query), params).fetchall()
        
        meetings_list = [{
            "id": m[0],
            "event_id": m[1],
            "title": m[2],
            "date": m[3].isoformat() if m[3] else None,
            "time": str(m[4]) if m[4] else None,
            "duration": m[5],
            "attendees": m[6],
            "status": m[7],
            "response_status": m[8],
            "attendee_responses": m[9] or [],
            "description": m[10],
            "created_at": m[11].isoformat() if m[11] else None
        } for m in meetings]
        
        return {
            "status": "success",
            "meetings": meetings_list,
            "count": len(meetings_list)
        }
        
    except Exception as e:
        logger.error(f"Get meetings failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/meetings/{meeting_id}/responses")
async def get_meeting_responses(
    meeting_id: int,
    x_api_key: Optional[str] = Header(None)
):
    """Get response details for a specific meeting"""
    try:
        verify_key(x_api_key)
        
        from server.database.connection import get_db_session
        from sqlalchemy import text
        
        with get_db_session() as db:
            meeting = db.execute(text("""
                SELECT title, attendees, attendee_responses, response_status
                FROM meetings WHERE id = :mid
            """), {"mid": meeting_id}).fetchone()
        
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        return {
            "status": "success",
            "meeting": {
                "title": meeting[0],
                "attendees": meeting[1],
                "responses": meeting[2] or [],
                "overall_status": meeting[3]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get meeting responses failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

