"""
Updated FastAPI application with Phase 3 integration
Location: server/app.py (REPLACE EXISTING)
"""
import os
import logging
import json
from pathlib import Path
from typing import Optional, Any, Dict, List

from fastapi import FastAPI, Request, Header, Depends, HTTPException
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


# Phase 2: Assistant functions
from server import assistant_functions

# Phase 3: Account management
from server.managers.account_manager import AccountManager

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

# Service instances
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
    """
    Chat with JARVIS - the conversational AI assistant
    Supports function calling and multi-turn conversations
    """
    try:
        if request.reset:
            agent.reset_conversation()
            return {
                "status": "success",
                "message": "Conversation reset. How can I help you?"
            }
        
        # Process message through agent
        result = await agent.chat(request.message)
        
        return {
            "status": "success",
            **result
        }
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history", dependencies=[Depends(verify_key)])
async def get_chat_history():
    """Get conversation history"""
    return {
        "status": "success",
        "history": agent.conversation_history,
        "count": len(agent.conversation_history)
    }


# Serve React UI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

ui_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "dist")

if os.path.exists(ui_dist):
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(ui_dist, "assets")), name="assets")
    
    # Serve index.html at root
    @app.get("/")
    async def serve_ui():
        return FileResponse(os.path.join(ui_dist, "index.html"))
