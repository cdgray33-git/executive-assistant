"""
Priority Engine - Learns what's urgent for the user
Location: server/intelligence/priority_engine.py
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import os

logger = logging.getLogger("priority_engine")

DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
PRIORITY_DATA = DATA_DIR / "intelligence" / "priority_patterns.json"


class PriorityEngine:
    """Learns user priority patterns from behavior"""
    
    def __init__(self):
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict:
        """Load learned priority patterns"""
        try:
            if PRIORITY_DATA.exists():
                with open(PRIORITY_DATA, 'r') as f:
                    return json.load(f)
            return {
                "senders": {},  # sender -> priority score
                "keywords": {},  # keyword -> priority score
                "domains": {},  # domain -> priority score
                "time_patterns": {},  # time-based patterns
                "response_times": {}  # sender -> avg response time
            }
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            return {"senders": {}, "keywords": {}, "domains": {}, "time_patterns": {}, "response_times": {}}
    
    def _save_patterns(self):
        """Save learned patterns"""
        try:
            PRIORITY_DATA.parent.mkdir(parents=True, exist_ok=True)
            with open(PRIORITY_DATA, 'w') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
    
    def learn_from_action(self, email: Dict, action: str, time_to_action: Optional[float] = None):
        """
        Learn from user action on email
        
        Args:
            email: Email dict
            action: Action taken (opened_immediately, starred, replied_fast, ignored, etc.)
            time_to_action: Seconds until action taken
        """
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        
        # Extract domain
        domain = sender.split("@")[-1] if "@" in sender else ""
        
        # Priority scores based on action
        action_scores = {
            "opened_immediately": 3.0,
            "starred": 2.5,
            "replied_fast": 3.0,
            "opened_within_hour": 1.5,
            "opened_within_day": 0.5,
            "ignored_week": -1.0,
            "deleted_immediately": -2.0
        }
        
        score_delta = action_scores.get(action, 0.0)
        
        # Update sender priority
        if sender:
            if sender not in self.patterns["senders"]:
                self.patterns["senders"][sender] = {"score": 5.0, "count": 0}
            
            current = self.patterns["senders"][sender]
            current["count"] += 1
            # Weighted average with decay
            current["score"] = (current["score"] * 0.8) + (score_delta * 0.2)
        
        # Update domain priority
        if domain:
            if domain not in self.patterns["domains"]:
                self.patterns["domains"][domain] = {"score": 5.0, "count": 0}
            
            current = self.patterns["domains"][domain]
            current["count"] += 1
            current["score"] = (current["score"] * 0.9) + (score_delta * 0.1)
        
        # Extract and learn keywords
        keywords = [word for word in subject.split() if len(word) > 4]
        for keyword in keywords[:5]:  # Limit to 5 keywords
            if keyword not in self.patterns["keywords"]:
                self.patterns["keywords"][keyword] = {"score": 5.0, "count": 0}
            
            current = self.patterns["keywords"][keyword]
            current["count"] += 1
            current["score"] = (current["score"] * 0.9) + (score_delta * 0.1)
        
        # Learn response time patterns
        if time_to_action and action in ["replied_fast", "opened_immediately"]:
            if sender not in self.patterns["response_times"]:
                self.patterns["response_times"][sender] = []
            
            self.patterns["response_times"][sender].append(time_to_action)
            # Keep only last 10 response times
            self.patterns["response_times"][sender] = self.patterns["response_times"][sender][-10:]
        
        self._save_patterns()
    
    def calculate_priority(self, email: Dict) -> float:
        """
        Calculate priority score for email
        
        Args:
            email: Email dict
            
        Returns:
            Priority score (0-10, higher = more urgent)
        """
        score = 5.0  # Base score
        
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        domain = sender.split("@")[-1] if "@" in sender else ""
        
        # Sender priority
        if sender in self.patterns["senders"]:
            sender_data = self.patterns["senders"][sender]
            score += (sender_data["score"] - 5.0) * 0.4
        
        # Domain priority
        if domain in self.patterns["domains"]:
            domain_data = self.patterns["domains"][domain]
            score += (domain_data["score"] - 5.0) * 0.2
        
        # Keyword priority
        keywords = [word for word in subject.split() if len(word) > 4]
        keyword_boost = 0
        for keyword in keywords:
            if keyword in self.patterns["keywords"]:
                keyword_data = self.patterns["keywords"][keyword]
                keyword_boost += (keyword_data["score"] - 5.0) * 0.1
        score += keyword_boost
        
        # Urgency keywords (hard-coded high priority)
        urgent_keywords = ["urgent", "asap", "immediate", "important", "critical"]
        if any(kw in subject for kw in urgent_keywords):
            score += 2.0
        
        # Calendar-related
        if "invite" in subject or "meeting" in subject or "calendar" in subject:
            score += 1.5
        
        # Reply to thread
        if subject.startswith("re:"):
            score += 1.0
        
        # Clamp to 0-10
        return max(0.0, min(10.0, score))
    
    def should_notify_immediately(self, email: Dict) -> bool:
        """Determine if user should be notified immediately"""
        priority = self.calculate_priority(email)
        return priority >= 8.0
    
    def get_sender_insights(self, sender: str) -> Dict[str, Any]:
        """Get learned insights about a sender"""
        sender = sender.lower()
        
        if sender not in self.patterns["senders"]:
            return {"known": False}
        
        sender_data = self.patterns["senders"][sender]
        avg_response_time = None
        
        if sender in self.patterns["response_times"]:
            times = self.patterns["response_times"][sender]
            avg_response_time = sum(times) / len(times) if times else None
        
        return {
            "known": True,
            "priority_score": sender_data["score"],
            "email_count": sender_data["count"],
            "avg_response_time_seconds": avg_response_time,
            "should_prioritize": sender_data["score"] > 7.0
        }