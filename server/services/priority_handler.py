"""
Priority Handler - Handles high-priority emails
Location: server/services/priority_handler.py
"""
import logging
from typing import Dict, Any

from server.managers.email_manager import EmailManager
from server.intelligence.context_engine import ContextEngine
from server.intelligence.response_drafter import ResponseDrafter

logger = logging.getLogger("priority_handler")


class PriorityHandler:
    """Handles urgent/priority emails automatically"""
    
    def __init__(self, email_mgr: EmailManager, context_engine: ContextEngine, 
                 response_drafter: ResponseDrafter):
        self.email_mgr = email_mgr
        self.context_engine = context_engine
        self.response_drafter = response_drafter
        
    def process_priority_email(self, email: Dict, account_id: str) -> Dict[str, Any]:
        """Process high-priority email"""
        context = self.context_engine.analyze_email(email, account_id)
        action = context["recommended_action"]
        
        result = {"email_id": email.get("id"), "actions_taken": []}
        
        if action == "respond_immediately":
            draft = self.response_drafter.draft_response(email, context)
            if draft["status"] == "success" and draft["draft"]["auto_send_recommended"]:
                # Auto-send if confidence high
                send_result = self.email_mgr.send_email(
                    to=draft["draft"]["to"],
                    subject=draft["draft"]["subject"],
                    body=draft["draft"]["body"],
                    from_account=account_id
                )
                result["actions_taken"].append({"action": "auto_replied", "result": send_result})
            else:
                result["actions_taken"].append({"action": "drafted_reply", "draft": draft})
        
        elif action == "schedule_meeting":
            result["actions_taken"].append({"action": "meeting_workflow_triggered"})
        
        return result