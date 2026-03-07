"""
Executive Assistant Function Registry and Router
Handles all function calls from Open WebUI via Ollama
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import managers (will create these next)
from server.managers.email_manager import EmailManager
from server.managers.calendar_manager import CalendarManager
from server.managers.contact_manager import ContactManager
from server.managers.note_manager import NoteManager
from server.managers.meeting_orchestrator import MeetingOrchestrator
from server.assistant_functions_calendar import block_calendar, check_availability, get_calendar_blocks, CALENDAR_FUNCTIONS
from server.managers.document_generator import DocumentGenerator

logger = logging.getLogger("assistant_functions")

# Initialize managers
email_mgr = EmailManager()
calendar_mgr = CalendarManager()
contact_mgr = ContactManager()
note_mgr = NoteManager()
meeting_mgr = MeetingOrchestrator(email_mgr, calendar_mgr, contact_mgr)
doc_mgr = DocumentGenerator()


# Draft approval helper
from server.draft_manager import DraftManager
_draft_mgr = DraftManager()

def _create_draft_for_approval(**kwargs):
    """Create email draft instead of sending directly"""
    draft_id = _draft_mgr.create_draft(
        to=kwargs.get('to'),
        subject=kwargs.get('subject'),
        body=kwargs.get('body'),
        from_account=kwargs.get('from_account', 'default'),
        cc=kwargs.get('cc'),
        bcc=kwargs.get('bcc'),
        context={"source": "agent", "timestamp": datetime.now().isoformat()}
    )
    return {
        "status": "draft_created",
        "draft_id": draft_id,
        "message": f"Draft created for review. Draft ID: {draft_id}",
        "drafts_created": [{
            "draft_id": draft_id,
            "to": kwargs.get('to'),
            "subject": kwargs.get('subject'),
            "name": kwargs.get('to')
        }]
    }

# Function Registry - Defines all available EA functions
FUNCTION_REGISTRY = {
    # Email Management
    "check_email": {
        "description": "Check all email accounts for new messages",
        "parameters": {},
        "function": lambda **k: email_mgr.check_all_accounts()
    },
    "send_email": {
        "description": "Send an email (creates draft for approval first)",
        "parameters": {
            "to": "recipient email or name",
            "subject": "email subject",
            "body": "email content",
            "from_account": "optional: specific account to send from"
        },
        "function": lambda **k: _create_draft_for_approval(**k)
    },
    "draft_email": {
        "description": "Draft an email without sending",
        "parameters": {
            "to": "recipient",
            "subject": "subject",
            "context": "what the email is about"
        },
        "function": lambda **k: email_mgr.draft_email(**k)
    },
    "search_email": {
        "description": "Search emails",
        "parameters": {
            "query": "search terms",
            "account": "optional: specific account"
        },
        "function": lambda **k: email_mgr.search_email(**k)
    },
    "categorize_inbox": {
        "description": "Auto-categorize and organize inbox",
        "parameters": {},
        "function": lambda **k: email_mgr.categorize_all_accounts()
    },
    
    # Calendar Management
    "check_calendar": {
        "description": "View calendar events",
        "parameters": {
            "days": "number of days to look ahead (default 7)"
        },
        "function": lambda **k: calendar_mgr.get_events(**k)
    },
    "add_event": {
        "description": "Add a calendar event",
        "parameters": {
            "title": "event title",
            "date": "event date (YYYY-MM-DD)",
            "time": "event time (HH:MM)",
            "duration": "duration in minutes (default 60)",
            "description": "optional description"
        },
        "function": lambda **k: calendar_mgr.add_event(**k)
    },
    "check_availability": {
        "description": "Check if time slot is available",
        "parameters": {
            "date": "date to check",
            "time": "time to check",
            "duration": "duration needed in minutes"
        },
        "function": lambda **k: calendar_mgr.check_availability(**k)
    },
    "update_event": {
        "description": "Update an existing event",
        "parameters": {
            "event_id": "event identifier",
            "updates": "dict of fields to update"
        },
        "function": lambda **k: calendar_mgr.update_event(**k)
    },
    "delete_event": {
        "description": "Delete a calendar event",
        "parameters": {
            "event_id": "event identifier"
        },
        "function": lambda **k: calendar_mgr.delete_event(**k)
    },
    
    # Contact Management
    "add_contact": {
        "description": "Add a new contact",
        "parameters": {
            "name": "contact name",
            "email": "email address",
            "phone": "optional phone number",
            "notes": "optional notes"
        },
        "function": lambda **k: contact_mgr.add_contact(**k)
    },
    "search_contacts": {
        "description": "Search contacts",
        "parameters": {
            "query": "name, email, or phone to search"
        },
        "function": lambda **k: contact_mgr.search_contacts(**k)
    },
    "get_contact": {
        "description": "Get contact details",
        "parameters": {
            "identifier": "name or email"
        },
        "function": lambda **k: contact_mgr.get_contact(**k)
    },
    "update_contact": {
        "description": "Update contact information",
        "parameters": {
            "identifier": "name or email",
            "updates": "dict of fields to update"
        },
        "function": lambda **k: contact_mgr.update_contact(**k)
    },
    
    # Meeting Orchestration
    "schedule_meeting": {
        "description": "Schedule a meeting with attendees (full workflow)",
        "parameters": {
            "attendees": "list of names or emails",
            "title": "meeting title",
            "date": "preferred date",
            "time": "preferred time",
            "duration": "duration in minutes (default 60)",
            "description": "optional meeting description"
        },
        "function": lambda **k: meeting_mgr.schedule_meeting(**k)
    },
    "search_calendar": {
        "description": "Search for meetings/events by date, topic, or attendee",
        "parameters": {
            "query": "search term (date like '3/12', 'next week', topic, or attendee name)",
            "days": "optional: number of days to search (default 30)"
        },
        "function": lambda **k: calendar_mgr.search_events(k.get('query', ''), days=k.get('days', 30))
    },
    "update_meeting": {
        "description": "Update an existing meeting time or details",
        "parameters": {
            "event_id": "event ID from search results",
            "start_time": "optional: new start time (HH:MM format)",
            "date": "optional: new date",
            "title": "optional: new title",
            "duration": "optional: new duration in minutes"
        },
        "function": lambda **k: calendar_mgr.update_event(k.get('event_id'), k)
    },
        "reschedule_meeting": {
        "description": "Reschedule an existing meeting",
        "parameters": {
            "meeting_id": "event identifier",
            "new_date": "new date",
            "new_time": "new time"
        },
        "function": lambda **k: meeting_mgr.reschedule_meeting(**k)
    },
    "cancel_meeting": {
        "description": "Cancel a meeting and notify attendees",
        "parameters": {
            "meeting_id": "event identifier",
            "reason": "optional cancellation reason"
        },
        "function": lambda **k: meeting_mgr.cancel_meeting(**k)
    },
    
    # Notes & Tasks
    "take_note": {
        "description": "Save a note",
        "parameters": {
            "content": "note content",
            "title": "optional title"
        },
        "function": lambda **k: note_mgr.save_note(**k)
    },
    "get_notes": {
        "description": "Retrieve notes",
        "parameters": {
            "query": "optional search query"
        },
        "function": lambda **k: note_mgr.get_notes(**k)
    },
    "create_task": {
        "description": "Create a task/reminder",
        "parameters": {
            "task": "task description",
            "due_date": "optional due date",
            "priority": "optional priority (high/medium/low)"
        },
        "function": lambda **k: note_mgr.create_task(**k)
    },
    
    # Document Generation
    "create_powerpoint": {
        "description": "Create a PowerPoint presentation",
        "parameters": {
            "title": "presentation title",
            "slides": "list of slide content",
            "template": "optional template name"
        },
        "function": lambda **k: doc_mgr.create_powerpoint(**k)
    },
    "create_memo": {
        "description": "Create a memo document",
        "parameters": {
            "to": "recipient",
            "from_": "sender",
            "subject": "memo subject",
            "content": "memo body"
        },
        "function": lambda **k: doc_mgr.create_memo(**k)
    },
    "create_drawing": {
        "description": "Create a simple drawing/diagram",
        "parameters": {
            "description": "what to draw",
            "format": "png or svg (default png)"
        },
        "function": lambda **k: doc_mgr.create_drawing(**k)
    }
    ,
    "cleanup_spam": {
        "description": "Safely identify and move spam emails to trash (reversible, uses AI categorization)",
        "parameters": {
            "account_id": "Specific email account or None for all accounts (optional)",
            "max_emails": "Maximum emails to process per account (default: 100, optional)",
            "preview_only": "If true, show what would be deleted without deleting (default: false, optional)"
        },
        "function": lambda **k: email_mgr.cleanup_spam_safe(**k)
    },
    "setup_email_folders": {
        "description": "Create organized email folders (Priority, Personal, Work, Finance, etc.) for all accounts",
        "parameters": {},
        "function": lambda **k: email_mgr.setup_all_accounts(**k)
    },
    "ensure_folders": {
        "description": "Ensure email folders exist for a specific account",
        "parameters": {
            "account_id": "Email account ID to setup folders for"
        },
        "function": lambda **k: email_mgr.ensure_folders_exist(**k)
    }
}


async def execute_function(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a function by name with given arguments
    
    Args:
        function_name: Name of function to execute
        arguments: Dictionary of arguments to pass
        
    Returns:
        Dictionary with execution results
    """
    try:
        if function_name not in FUNCTION_REGISTRY:
            return {
                "status": "error",
                "error": f"Function '{function_name}' not found",
                "available_functions": list(FUNCTION_REGISTRY.keys())
            }
        
        logger.info(f"Executing function: {function_name} with args: {arguments}")
        
        # Get function from registry
        func_info = FUNCTION_REGISTRY[function_name]
        func = func_info["function"]
        
        # Execute function (handle both sync and async)
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(func):
            result = await func(**arguments)
        else:
            result = func(**arguments)
        
        return {
            "status": "success",
            "function": function_name,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing {function_name}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "function": function_name,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def get_function_info() -> Dict[str, Any]:
    """Get information about all available functions"""
    return {
        name: {
            "description": info["description"],
            "parameters": info["parameters"]
        }
        for name, info in FUNCTION_REGISTRY.items()
    }


def get_function_names() -> list:
    """Get list of all function names"""
    return list(FUNCTION_REGISTRY.keys())