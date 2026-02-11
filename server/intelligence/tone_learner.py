"""
Tone Learner - Learns user's communication style
Location: server/intelligence/tone_learner.py
"""
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
import re

logger = logging.getLogger("tone_learner")

DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
TONE_DATA = DATA_DIR / "intelligence" / "tone_profiles.json"


class ToneLearner:
    """Learns user's writing style and tone"""
    
    def __init__(self):
        self.profiles = self._load_profiles()
        
    def _load_profiles(self) -> Dict:
        """Load tone profiles"""
        try:
            if TONE_DATA.exists():
                with open(TONE_DATA, 'r') as f:
                    return json.load(f)
            return {
                "by_recipient": {},  # recipient -> tone profile
                "by_domain": {},  # domain -> tone profile
                "global": self._default_profile()
            }
        except Exception as e:
            logger.error(f"Error loading tone profiles: {e}")
            return {"by_recipient": {}, "by_domain": {}, "global": self._default_profile()}
    
    def _default_profile(self) -> Dict:
        """Default tone profile"""
        return {
            "formality": "neutral",  # casual, neutral, formal
            "greeting": "Hi",
            "closing": "Best regards",
            "avg_length": 100,
            "uses_emoji": False,
            "sentence_style": "medium",  # short, medium, long
            "samples": 0
        }
    
    def _save_profiles(self):
        """Save tone profiles"""
        try:
            TONE_DATA.parent.mkdir(parents=True, exist_ok=True)
            with open(TONE_DATA, 'w') as f:
                json.dump(self.profiles, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tone profiles: {e}")
    
    def learn_from_sent_email(self, to: str, subject: str, body: str):
        """
        Learn from a sent email
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
        """
        to = to.lower()
        domain = to.split("@")[-1] if "@" in to else ""
        
        # Analyze email characteristics
        profile = self._analyze_email(body)
        
        # Update recipient-specific profile
        if to not in self.profiles["by_recipient"]:
            self.profiles["by_recipient"][to] = self._default_profile()
        
        self._merge_profile(self.profiles["by_recipient"][to], profile)
        
        # Update domain profile
        if domain:
            if domain not in self.profiles["by_domain"]:
                self.profiles["by_domain"][domain] = self._default_profile()
            
            self._merge_profile(self.profiles["by_domain"][domain], profile)
        
        # Update global profile
        self._merge_profile(self.profiles["global"], profile)
        
        self._save_profiles()
    
    def _analyze_email(self, body: str) -> Dict:
        """Analyze email to extract tone characteristics"""
        profile = self._default_profile()
        
        # Extract greeting
        first_line = body.split('\n')[0].strip()
        if first_line.startswith(("Hi", "Hello", "Hey", "Dear")):
            profile["greeting"] = first_line.split(',')[0] if ',' in first_line else first_line.split()[0]
        
        # Extract closing
        lines = body.strip().split('\n')
        for i in range(len(lines) - 1, max(len(lines) - 5, -1), -1):
            line = lines[i].strip()
            if line in ["Best regards", "Best", "Thanks", "Thank you", "Sincerely", "Cheers", "Regards"]:
                profile["closing"] = line
                break
        
        # Detect emoji usage
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            "]+", flags=re.UNICODE)
        profile["uses_emoji"] = bool(emoji_pattern.search(body))
        
        # Analyze formality
        formal_indicators = ["dear", "sincerely", "regards", "respectfully"]
        casual_indicators = ["hey", "thanks", "cheers", "lol"]
        
        body_lower = body.lower()
        formal_count = sum(1 for word in formal_indicators if word in body_lower)
        casual_count = sum(1 for word in casual_indicators if word in body_lower)
        
        if formal_count > casual_count:
            profile["formality"] = "formal"
        elif casual_count > formal_count:
            profile["formality"] = "casual"
        else:
            profile["formality"] = "neutral"
        
        # Average length
        profile["avg_length"] = len(body)
        
        # Sentence style
        sentences = body.split('.')
        avg_sentence_length = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        
        if avg_sentence_length < 10:
            profile["sentence_style"] = "short"
        elif avg_sentence_length > 20:
            profile["sentence_style"] = "long"
        else:
            profile["sentence_style"] = "medium"
        
        return profile
    
    def _merge_profile(self, existing: Dict, new: Dict):
        """Merge new profile data into existing (weighted average)"""
        samples = existing["samples"]
        weight_old = samples / (samples + 1)
        weight_new = 1 / (samples + 1)
        
        # Weighted average for numeric values
        existing["avg_length"] = int(existing["avg_length"] * weight_old + new["avg_length"] * weight_new)
        
        # Most recent wins for categorical
        if samples < 3:  # Learn quickly at first
            existing["greeting"] = new["greeting"]
            existing["closing"] = new["closing"]
            existing["formality"] = new["formality"]
            existing["sentence_style"] = new["sentence_style"]
        
        # Emoji usage (any usage = True)
        existing["uses_emoji"] = existing["uses_emoji"] or new["uses_emoji"]
        
        existing["samples"] += 1
    
    def get_tone_for_recipient(self, to: str) -> Dict:
        """Get appropriate tone profile for recipient"""
        to = to.lower()
        domain = to.split("@")[-1] if "@" in to else ""
        
        # Check recipient-specific
        if to in self.profiles["by_recipient"] and self.profiles["by_recipient"][to]["samples"] > 0:
            return self.profiles["by_recipient"][to]
        
        # Check domain
        if domain in self.profiles["by_domain"] and self.profiles["by_domain"][domain]["samples"] > 0:
            return self.profiles["by_domain"][domain]
        
        # Fall back to global
        return self.profiles["global"]
    
    def draft_with_tone(self, to: str, content: str) -> str:
        """
        Draft email with learned tone
        
        Args:
            to: Recipient
            content: Core content to include
            
        Returns:
            Formatted email with appropriate tone
        """
        tone = self.get_tone_for_recipient(to)
        
        # Extract recipient name
        recipient_name = to.split("@")[0].replace(".", " ").title()
        
        # Build email
        parts = []
        
        # Greeting
        greeting = tone["greeting"]
        if greeting in ["Hi", "Hello", "Hey"]:
            parts.append(f"{greeting} {recipient_name},")
        else:
            parts.append(f"{greeting},")
        
        parts.append("")  # Blank line
        
        # Content
        parts.append(content)
        
        parts.append("")  # Blank line
        
        # Closing
        parts.append(tone["closing"])
        
        # Add emoji if user typically uses them
        if tone["uses_emoji"] and tone["formality"] == "casual":
            parts[-1] += " ??"
        
        return "\n".join(parts)