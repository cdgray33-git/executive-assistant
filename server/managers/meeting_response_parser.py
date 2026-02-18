"""
Meeting Response Parser - Ollama-powered intelligent parsing
Detects and extracts meeting responses from emails
"""
import re
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from server.llm.ollama_adapter import OllamaAdapter

logger = logging.getLogger(__name__)

class MeetingResponseParser:
    def __init__(self):
        self.ollama = OllamaAdapter()
        
    def parse_response(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse email for meeting response using Ollama
        
        Returns:
            {
                "type": "accept" | "decline" | "tentative",
                "attendee_email": "user@domain.com",
                "ics_uid": "event-uid-from-ics",
                "proposed_time": {
                    "date": "2026-02-20",
                    "time": "14:00",
                    "timezone": "America/New_York"
                },
                "message": "Optional message from attendee"
            }
        """
        subject = email.get('subject', '')
        body = email.get('body', '')
        sender = email.get('from', '')
        
        # Quick keyword check first
        response_keywords = {
            'accept': ['accepted', 'accept', 'will attend', 'confirmed', 'yes', 'count me in'],
            'decline': ['declined', 'decline', 'cannot attend', 'unable to attend', 'can\'t make it', 'regrets'],
            'tentative': ['tentative', 'maybe', 'might attend', 'not sure', 'possibly']
        }
        
        # Check subject and body for keywords
        combined = f"{subject} {body}".lower()
        detected_type = None
        
        for resp_type, keywords in response_keywords.items():
            if any(kw in combined for kw in keywords):
                detected_type = resp_type
                break
        
        # If no keywords found, not a meeting response
        if not detected_type:
            return None
            
        logger.info(f"Detected {detected_type} response from {sender}")
        
        # Extract ICS UID from email
        ics_uid = self._extract_ics_uid(email)
        
        # Use Ollama to extract details
        prompt = f"""You are analyzing a meeting response email.

Subject: {subject}
From: {sender}
Body: {body[:1000]}

Extract the following:
1. Response type: accept, decline, or tentative
2. Is there a proposed alternative date/time? (yes/no)
3. If yes, extract: date, time, timezone
4. Any personal message from the attendee

Respond ONLY in JSON format:
{{
    "type": "accept|decline|tentative",
    "has_alternative": true|false,
    "proposed_date": "YYYY-MM-DD" or null,
    "proposed_time": "HH:MM" or null,
    "proposed_timezone": "timezone" or null,
    "message": "extracted message" or null
}}"""

        try:
            response = self.ollama.generate(prompt, model="llama3.2:latest")
            parsed = self._parse_ollama_json(response)
            
            result = {
                "type": parsed.get("type", detected_type),
                "attendee_email": self._extract_email(sender),
                "ics_uid": ics_uid,
                "message": parsed.get("message")
            }
            
            # Add proposed time if declined with alternative
            if parsed.get("has_alternative") and parsed.get("proposed_date"):
                result["proposed_time"] = {
                    "date": parsed["proposed_date"],
                    "time": parsed.get("proposed_time", ""),
                    "timezone": parsed.get("proposed_timezone", "UTC")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Ollama parsing failed: {e}")
            # Fallback to keyword-based result
            return {
                "type": detected_type,
                "attendee_email": self._extract_email(sender),
                "ics_uid": ics_uid,
                "message": None
            }
    
    def _extract_ics_uid(self, email: Dict[str, Any]) -> Optional[str]:
        """Extract ICS UID from email body or headers"""
        body = email.get('body', '')
        
        # Common patterns for ICS UID
        patterns = [
            r'UID:([^\s\n]+)',
            r'uid=([^\s&]+)',
            r'event[_-]?id[=:]([^\s\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_email(self, from_field: str) -> str:
        """Extract email from 'Name <email>' format"""
        match = re.search(r'<([^>]+)>', from_field)
        if match:
            return match.group(1).strip().lower()
        return from_field.strip().lower()
    
    def _parse_ollama_json(self, response: str) -> Dict:
        """Parse JSON from Ollama response (handles markdown code blocks)"""
        import json
        
        # Remove markdown code blocks if present
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        response = response.strip()
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise
