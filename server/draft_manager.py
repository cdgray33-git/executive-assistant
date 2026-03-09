"""
Email Draft Management
Handles pending email approvals before sending
SINGLETON PATTERN - Only one instance across application
"""
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

class DraftManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DraftManager, cls).__new__(cls)
            cls._instance.drafts = {}
        return cls._instance

    def create_draft(self, to: str, subject: str, body: str,
                    from_account: str, cc: Optional[list] = None,
                    bcc: Optional[list] = None, context: Optional[Dict] = None) -> str:
        """Create a new email draft and return draft_id"""
        draft_id = str(uuid.uuid4())

        self.drafts[draft_id] = {
            "draft_id": draft_id,
            "to": to,
            "subject": subject,
            "body": body,
            "from_account": from_account,
            "cc": cc or [],
            "bcc": bcc or [],
            "context": context or {},
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        return draft_id

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a draft by ID"""
        return self.drafts.get(draft_id)

    def approve_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        """Mark draft as approved for sending"""
        draft = self.drafts.get(draft_id)
        if draft:
            draft["status"] = "approved"
        return draft

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft"""
        if draft_id in self.drafts:
            del self.drafts[draft_id]
            return True
        return False

    def get_pending_drafts(self) -> List[Dict[str, Any]]:
        """Get all pending drafts"""
        return [d for d in self.drafts.values() if d["status"] == "pending"]
    
    def list_pending(self) -> List[Dict[str, Any]]:
        """Alias for get_pending_drafts() - used by API endpoints"""
        return self.get_pending_drafts()


# Global singleton instance for import
draft_manager = DraftManager()
