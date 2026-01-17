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

# Ollama adapter instance with model validation
ollama = OllamaAdapter()

# Check and auto-pull models at startup
async def ensure_ollama_models():
    """Ensure required Ollama models are available, pull if missing."""
    import subprocess
    
    required_models = ["llama3.2:3b", "llama2"]
    default_model = "llama3.2:3b"
    
    try:
        # Check if Ollama is running
        if not await ollama.ping():
            logger.warning("Ollama is not running. Start with: ollama serve")
            return False
        
        # List available models
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        available_models = result.stdout
        
        logger.info(f"Available Ollama models:\n{available_models}")
        
        # Check if we have at least one required model
        has_model = False
        for model in required_models:
            if model in available_models:
                has_model = True
                logger.info(f"✓ Model {model} is available")
                break
        
        if not has_model:
            logger.warning(f"No required models found. Attempting to pull {default_model}...")
            pull_result = subprocess.run(["ollama", "pull", default_model], 
                                        capture_output=True, text=True, timeout=300)
            if pull_result.returncode == 0:
                logger.info(f"✓ Successfully pulled {default_model}")
                return True
            else:
                logger.error(f"✗ Failed to pull {default_model}: {pull_result.stderr}")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking Ollama models: {e}")
        return False

# Store model check result
ollama_models_ready = False

@app.on_event("startup")
async def startup_event():
    """Check Ollama models at startup and auto-pull if needed."""
    global ollama_models_ready
    logger.info("=" * 60)
    logger.info("Executive Assistant Server Starting...")
    logger.info("=" * 60)
    logger.info("Checking Ollama models...")
    ollama_models_ready = await ensure_ollama_models()
    if ollama_models_ready:
        logger.info("✓ Ollama models ready for AI-powered NLP")
    else:
        logger.warning("✗ Ollama models not available - will use pattern matching fallback")
        logger.warning("To enable AI features:")
        logger.warning("  1. Start Ollama: ollama serve")
        logger.warning("  2. Pull a model: ollama pull llama3.2:3b")
        logger.warning("  3. Check logs: ~/ExecutiveAssistant/logs/server_stderr.log")
    logger.info("=" * 60)

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
    Natural language chat endpoint with LLM-powered NLP support for all assistant functions.
    Uses Ollama to understand intent and extract parameters from natural language.
    """
    try:
        data = await request.json()
        prompt_original = data.get("prompt", "").strip()
        
        if not prompt_original:
            return {"response": "Please provide a message."}
        
        # Use Ollama LLM to interpret the user's intent
        llm_result = await interpret_with_llm(prompt_original, ollama)
        
        if llm_result.get("error"):
            # Fallback to pattern matching if LLM fails
            logger.warning(f"LLM interpretation failed, using pattern matching: {llm_result.get('error')}")
            return await chat_pattern_matching(prompt_original)
        
        # Route to appropriate handler based on LLM-identified intent
        intent = llm_result.get("intent", "unknown")
        params = llm_result.get("parameters", {})
        
        logger.info(f"LLM Intent: {intent}, Parameters: {params}")
        
        # Execute based on intent
        if intent == "schedule_meeting":
            return await handle_schedule_meeting(params)
        elif intent == "view_calendar":
            return await handle_view_calendar(params)
        elif intent == "add_contact":
            return await handle_add_contact(params)
        elif intent == "search_contacts":
            return await handle_search_contacts(params)
        elif intent == "send_email":
            return await handle_send_email(params)
        elif intent == "create_presentation":
            return await handle_create_presentation(params)
        elif intent == "create_document":
            return await handle_create_document(params)
        elif intent == "take_note":
            return await handle_take_note(params)
        elif intent == "view_notes":
            return await handle_view_notes(params)
        elif intent == "view_emails":
            return await handle_view_emails(params)
        elif intent == "delete_spam":
            return await handle_delete_spam(params)
        elif intent == "categorize_emails":
            return await handle_categorize_emails(params)
        elif intent == "cleanup_emails":
            return await handle_cleanup_emails(params)
        else:
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


async def interpret_with_llm(prompt: str, ollama_adapter: OllamaAdapter) -> Dict[str, Any]:
    """
    Use Ollama LLM to interpret user intent and extract parameters.
    Returns: {"intent": "action_name", "parameters": {...}}
    """
    try:
        # Check if Ollama is available
        if not await ollama_adapter.ping():
            logger.warning("Ollama LLM not available - falling back to pattern matching")
            logger.warning("To enable AI-powered NLP:")
            logger.warning("  1. Open a terminal and run: ollama serve")
            logger.warning("  2. Pull a model: ollama pull llama3.2:3b")
            logger.warning("  3. Restart the Executive Assistant")
            return {"error": "Ollama LLM is currently unavailable. Please try again or use specific phrases above"}
        
        # Create a structured prompt for the LLM
        system_prompt = """You are an intent classifier for an Executive Assistant. 
Analyze the user's request and respond with JSON containing the intent and extracted parameters.

Available intents:
- schedule_meeting: Schedule a calendar event
- view_calendar: Show calendar events
- add_contact: Add a contact
- search_contacts: Find contacts
- send_email: Send an email
- create_presentation: Create PowerPoint
- create_document: Create document/report/briefing/memo
- take_note: Save a note
- view_notes: Show notes
- view_emails: Show emails/messages
- delete_spam: Delete spam/junk emails
- categorize_emails: Organize emails into folders
- cleanup_emails: Bulk cleanup old emails

Extract these parameters when present:
- email: email address
- date: date (relative like "tomorrow" or specific)
- time: time (e.g., "2pm", "14:30")
- title/subject: title or subject
- content/message: content or message body
- name: person's name
- query: search query
- count: number (e.g., "5 emails", "10 days")
- older_than_days: age threshold for emails
- delete: whether to actually delete (vs preview)

Respond ONLY with valid JSON, no other text:
{"intent": "intent_name", "parameters": {"param": "value"}}"""
        
        user_prompt = f"{system_prompt}\n\nUser request: {prompt}"
        
        # Try with llama3.2:3b first, fallback to llama2
        models_to_try = ["llama3.2:3b", "llama2"]
        result = None
        
        for model in models_to_try:
            try:
                # Call Ollama generate
                result = await ollama_adapter.generate(model=model, prompt=user_prompt, stream=False)
                if result and result.get("response"):
                    break
            except Exception as e:
                logger.warning(f"Failed to use model {model}: {e}")
                continue
        
        if not result or not result.get("response"):
            return {"error": "No Ollama models available. Please pull llama3.2:3b or llama2"}
        
        # Extract JSON from response
        response_text = result.get("response", "").strip()
        
        # Try to parse JSON from response
        import json
        import re
        
        # Find JSON in response
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            return parsed
        
        return {"error": "Could not parse LLM response"}
        
    except Exception as e:
        logger.error(f"LLM interpretation error: {e}")
        logger.error("To check logs: tail -50 ~/ExecutiveAssistant/logs/server_stderr.log")
        return {"error": str(e)}


async def chat_pattern_matching(prompt_original: str):
    """
    Fallback pattern matching when LLM is unavailable.
    Returns a help message since the main logic should use LLM.
    """
    return {
        "response": "I'm your Executive Assistant. I can help you with:\n\n" +
                   "📧 Email: 'Show my last 5 emails', 'Delete all spam', 'Remove junk mail'\n" +
                   "📅 Calendar: 'Schedule meeting with john@example.com tomorrow at 2pm'\n" +
                   "👥 Contacts: 'Add contact john@example.com', 'Find contacts'\n" +
                   "📄 Documents: 'Create a PowerPoint about Q4 results', 'Write a report'\n" +
                   "📝 Notes: 'Take a note: Remember to call the client'\n\n" +
                   "(Note: Ollama LLM is currently unavailable. Please try again or use specific phrases above)"
    }


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
