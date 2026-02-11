"""
Context Engine - Analyzes email context for smart routing
Location: server/intelligence/context_engine.py
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from server.intelligence.priority_engine import PriorityEngine
from server.intelligence.category_learner import CategoryLearner
from server.managers.contact_manager import ContactManager

logger = logging.getLogger("context_engine")


class ContextEngine:
    """Analyzes email context for intelligent processing"""
    
    def __init__(self, priority_engine: PriorityEngine, 
                 category_learner: CategoryLearner,
                 contact_mgr: ContactManager):
        self.priority_engine = priority_engine
        self.category_learner = category_learner
        self.contact_mgr = contact_mgr
        
    def analyze_email(self, email: Dict, account_id: str) -> Dict[str, Any]:
        """
        Comprehensive email context analysis
        
        Args:
            email: Email dict
            account_id: Account that received email
            
        Returns:
            Context analysis dict
        """
        sender = email.get("from", "")
        subject = email.get("subject", "")
        body = email.get("body", "")
        
        context = {
            "email_id": email.get("id"),
            "account_id": account_id,
            "sender": sender,
            "subject": subject,
            "analyzed_at": datetime.now().isoformat()
        }
        
        # Priority analysis
        priority_score = self.priority_engine.calculate_priority(email)
        context["priority"] = {
            "score": priority_score,
            "level": self._priority_level(priority_score),
            "notify_immediately": priority_score >= 8.0
        }
        
        # Sender insights
        sender_insights = self.priority_engine.get_sender_insights(sender)
        context["sender_insights"] = sender_insights
        
        # Contact relationship
        contact = self.contact_mgr.get_contact_by_email(sender)
        context["contact"] = {
            "known": contact is not None,
            "name": contact.get("name") if contact else None,
            "relationship": self._determine_relationship(contact, account_id)
        }
        
        # Category suggestion
        category_suggestion = self.category_learner.suggest_category(email)
        context["category_suggestion"] = category_suggestion
        
        # Content analysis
        context["content_flags"] = self._analyze_content(subject, body)
        
        # Recommended action
        context["recommended_action"] = self._recommend_action(context)
        
        # Smart account selection for reply
        context["reply_from_account"] = self._select_reply_account(email, account_id)
        
        return context
    
    def _priority_level(self, score: float) -> str:
        """Convert priority score to level"""
        if score >= 8.0:
            return "urgent"
        elif score >= 6.5:
            return "high"
        elif score >= 4.5:
            return "normal"
        else:
            return "low"
    
    def _determine_relationship(self, contact: Optional[Dict], account_id: str) -> str:
        """Determine relationship type"""
        if not contact:
            return "unknown"
        
        tags = contact.get("tags", [])
        notes = contact.get("notes", "").lower()
        
        if "family" in tags or "family" in notes:
            return "family"
        elif "work" in tags or "colleague" in notes:
            return "work"
        elif "friend" in tags:
            return "personal"
        
        # Guess from email domain and account
        # TODO: Implement domain matching
        
        return "acquaintance"
    
    def _analyze_content(self, subject: str, body: str) -> Dict[str, bool]:
        """Analyze email content for special flags"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        combined = subject_lower + " " + body_lower
        
        return {
            "has_calendar_invite": ".ics" in body or "calendar" in combined,
            "has_meeting_request": "meeting" in combined or "schedule" in combined,
            "has_attachments": False,  # TODO: Detect from email data
            "is_forwarded": subject_lower.startswith("fwd:") or subject_lower.startswith("fw:"),
            "is_reply": subject_lower.startswith("re:"),
            "has_question": "?" in subject or "?" in body[:500],
            "requests_action": any(word in combined for word in ["please", "could you", "can you", "action required"]),
            "is_automated": any(word in combined for word in ["do not reply", "automated", "no-reply"]),
            "has_deadline": any(word in combined for word in ["deadline", "due date", "by end of"]),
        }
    
    def _recommend_action(self, context: Dict) -> str:
        """Recommend action based on context"""
        priority = context["priority"]["score"]
        flags = context["content_flags"]
        sender_insights = context["sender_insights"]
        
        # Urgent priority
        if priority >= 8.0:
            if flags["has_meeting_request"]:
                return "schedule_meeting"
            elif flags["requests_action"]:
                return "respond_immediately"
            else:
                return "review_immediately"
        
        # Calendar invite
        if flags["has_calendar_invite"]:
            return "process_calendar_invite"
        
        # Known important sender expecting fast response
        if sender_insights.get("should_prioritize"):
            avg_response = sender_insights.get("avg_response_time_seconds")
            if avg_response and avg_response < 3600:  # Usually respond within hour
                return "respond_soon"
        
        # Question requiring answer
        if flags["has_question"] and not flags["is_automated"]:
            return "respond_when_available"
        
        # Automated message
        if flags["is_automated"]:
            return "auto_file"
        
        # Default
        return "review_later"
    
    def _select_reply_account(self, email: Dict, received_account: str) -> str:
        """Smart account selection for reply"""
        # For now, reply from same account that received
        # TODO: Implement smart selection based on:
        # - Thread history
        # - Contact association
        # - Email content domain
        
        return received_account