"""
AI-Powered Spam Detection using Ollama
"""
import requests
import json
import logging
from typing import List, Dict

logger = logging.getLogger("spam_detector")

class SpamDetector:
    """Uses local Ollama LLM to categorize emails"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2:3b"
    
    def categorize_email(self, from_addr: str, subject: str) -> Dict:
        """
        Categorize single email as spam/keep/unsure
        Returns: {category: "spam"|"keep"|"unsure", confidence: float, reason: str}
        """
        
        prompt = f"""Analyze this email and categorize it as spam, keep, or unsure.

From: {from_addr}
Subject: {subject}

Reply ONLY with JSON in this format:
{{"category": "spam"|"keep"|"unsure", "confidence": 0.0-1.0, "reason": "brief explanation"}}

Spam indicators:
- Unknown/suspicious sender domains
- Marketing/promotional language
- Offers, deals, discounts
- "Act now", "Limited time"
- Generic greetings

Keep indicators:
- Personal correspondence
- Known contacts
- Important services (banks, utilities)
- Purchase confirmations

Be cautious - when uncertain, mark as "unsure"."""

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "").strip()
                
                # Extract JSON from response
                json_start = text.find("{")
                json_end = text.rfind("}") + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = text[json_start:json_end]
                    category_data = json.loads(json_str)
                    
                    return {
                        "category": category_data.get("category", "unsure").lower(),
                        "confidence": float(category_data.get("confidence", 0.5)),
                        "reason": category_data.get("reason", "")
                    }
            
            return {
                "category": "unsure",
                "confidence": 0.0,
                "reason": "Failed to parse LLM response"
            }
        
        except Exception as e:
            logger.error(f"Categorization error: {e}")
            return {
                "category": "unsure",
                "confidence": 0.0,
                "reason": f"Error: {str(e)}"
            }
    
    def batch_categorize(self, emails: List[Dict]) -> List[Dict]:
        """Categorize multiple emails"""
        results = []
        
        for email_item in emails:
            from_addr = email_item.get("from", "")
            subject = email_item.get("subject", "")
            
            category_info = self.categorize_email(from_addr, subject)
            
            results.append({
                **email_item,
                **category_info
            })
        
        return results
