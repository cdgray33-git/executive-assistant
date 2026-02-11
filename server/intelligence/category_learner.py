"""
Category Learner - Learns email categorization patterns
Location: server/intelligence/category_learner.py
"""
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

logger = logging.getLogger("category_learner")

DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
CATEGORY_DATA = DATA_DIR / "intelligence" / "category_rules.json"


class CategoryLearner:
    """Learns email categorization from user corrections"""
    
    def __init__(self):
        self.rules = self._load_rules()
        
    def _load_rules(self) -> Dict:
        """Load learned categorization rules"""
        try:
            if CATEGORY_DATA.exists():
                with open(CATEGORY_DATA, 'r') as f:
                    return json.load(f)
            return {
                "sender_rules": {},  # sender -> category
                "domain_rules": {},  # domain -> category
                "subject_patterns": {},  # pattern -> category
                "corrections": []  # history of user corrections
            }
        except Exception as e:
            logger.error(f"Error loading category rules: {e}")
            return {"sender_rules": {}, "domain_rules": {}, "subject_patterns": {}, "corrections": []}
    
    def _save_rules(self):
        """Save learned rules"""
        try:
            CATEGORY_DATA.parent.mkdir(parents=True, exist_ok=True)
            with open(CATEGORY_DATA, 'w') as f:
                json.dump(self.rules, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving category rules: {e}")
    
    def learn_from_correction(self, email: Dict, ai_category: str, correct_category: str):
        """
        Learn from user correcting AI categorization
        
        Args:
            email: Email dict
            ai_category: What AI suggested
            correct_category: What user chose
        """
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        domain = sender.split("@")[-1] if "@" in sender else ""
        
        # Record correction
        self.rules["corrections"].append({
            "sender": sender,
            "subject": subject,
            "ai_category": ai_category,
            "correct_category": correct_category,
            "timestamp": None
        })
        
        # Keep only last 1000 corrections
        self.rules["corrections"] = self.rules["corrections"][-1000:]
        
        # Create sender rule
        if sender:
            if sender not in self.rules["sender_rules"]:
                self.rules["sender_rules"][sender] = {}
            
            if correct_category not in self.rules["sender_rules"][sender]:
                self.rules["sender_rules"][sender][correct_category] = 0
            
            self.rules["sender_rules"][sender][correct_category] += 1
        
        # Create domain rule (less weight than sender)
        if domain:
            if domain not in self.rules["domain_rules"]:
                self.rules["domain_rules"][domain] = {}
            
            if correct_category not in self.rules["domain_rules"][domain]:
                self.rules["domain_rules"][domain][correct_category] = 0
            
            self.rules["domain_rules"][domain][correct_category] += 1
        
        # Extract subject patterns (simple keyword matching)
        keywords = [word for word in subject.split() if len(word) > 4]
        for keyword in keywords[:3]:  # Top 3 keywords
            if keyword not in self.rules["subject_patterns"]:
                self.rules["subject_patterns"][keyword] = {}
            
            if correct_category not in self.rules["subject_patterns"][keyword]:
                self.rules["subject_patterns"][keyword][correct_category] = 0
            
            self.rules["subject_patterns"][keyword][correct_category] += 1
        
        self._save_rules()
    
    def suggest_category(self, email: Dict) -> Optional[Dict[str, Any]]:
        """
        Suggest category based on learned rules
        
        Args:
            email: Email dict
            
        Returns:
            Dict with category and confidence, or None
        """
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        domain = sender.split("@")[-1] if "@" in sender else ""
        
        scores = {}
        
        # Check sender rules (high confidence)
        if sender in self.rules["sender_rules"]:
            sender_cats = self.rules["sender_rules"][sender]
            total = sum(sender_cats.values())
            for cat, count in sender_cats.items():
                confidence = count / total
                if confidence > 0.7:  # High confidence threshold
                    scores[cat] = scores.get(cat, 0) + confidence * 0.6
        
        # Check domain rules (medium confidence)
        if domain in self.rules["domain_rules"]:
            domain_cats = self.rules["domain_rules"][domain]
            total = sum(domain_cats.values())
            for cat, count in domain_cats.items():
                confidence = count / total
                if confidence > 0.5:
                    scores[cat] = scores.get(cat, 0) + confidence * 0.3
        
        # Check subject patterns (low confidence)
        keywords = [word for word in subject.split() if len(word) > 4]
        for keyword in keywords:
            if keyword in self.rules["subject_patterns"]:
                pattern_cats = self.rules["subject_patterns"][keyword]
                total = sum(pattern_cats.values())
                for cat, count in pattern_cats.items():
                    confidence = count / total
                    scores[cat] = scores.get(cat, 0) + confidence * 0.1
        
        # Return highest scoring category if above threshold
        if scores:
            best_category = max(scores, key=scores.get)
            confidence = scores[best_category]
            
            if confidence > 0.6:  # Overall confidence threshold
                return {
                    "category": best_category,
                    "confidence": confidence,
                    "source": "learned_rules"
                }
        
        return None
    
    def get_sender_category_history(self, sender: str) -> Dict[str, int]:
        """Get categorization history for a sender"""
        sender = sender.lower()
        return self.rules["sender_rules"].get(sender, {})