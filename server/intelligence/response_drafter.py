"""
Response Drafter - AI-powered email response generation
Location: server/intelligence/response_drafter.py
"""
import logging
from typing import Dict, Any, Optional

from server.intelligence.tone_learner import ToneLearner
from server.llm.ollama_adapter import OllamaAdapter

logger = logging.getLogger("response_drafter")


class ResponseDrafter:
    """Drafts email responses using AI and learned tone"""
    
    def __init__(self, tone_learner: ToneLearner, ollama: OllamaAdapter):
        self.tone_learner = tone_learner
        self.ollama = ollama
        
    def draft_response(self, original_email: Dict, context: Dict, 
                       instruction: Optional[str] = None) -> Dict[str, Any]:
        """Draft response to an email"""
        try:
            sender = original_email.get("from", "")
            subject = original_email.get("subject", "")
            body = original_email.get("body", "")
            
            tone = self.tone_learner.get_tone_for_recipient(sender)
            prompt = self._build_prompt(original_email, context, tone, instruction)
            response_body = self.ollama.generate(prompt, model="qwen2.5:7b-instruct")
            formatted_body = self.tone_learner.draft_with_tone(sender, response_body)
            
            response_subject = f"Re: {subject}" if not subject.startswith("Re:") else subject
            confidence = self._calculate_confidence(context, tone)
            
            return {
                "status": "success",
                "draft": {
                    "to": sender,
                    "subject": response_subject,
                    "body": formatted_body,
                    "confidence": confidence,
                    "auto_send_recommended": confidence >= 0.95
                }
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _build_prompt(self, email: Dict, context: Dict, tone: Dict, instruction: Optional[str]) -> str:
        sender = email.get("from", "")
        subject = email.get("subject", "")
        body = email.get("body", "")
        relationship = context.get("contact", {}).get("relationship", "unknown")
        
        prompt = f"""Draft a professional email response.

Original Email:
From: {sender}
Subject: {subject}
Body: {body[:500]}

Context:
- Relationship: {relationship}
- Tone should be: {tone['formality']}
- Priority: {context.get('priority', {}).get('level', 'normal')}
"""
        
        if instruction:
            prompt += f"\nSpecific instruction: {instruction}"
        
        prompt += "\n\nWrite ONLY the body content (no greeting/closing, those will be added). Be concise and helpful."
        
        return prompt
    
    def _calculate_confidence(self, context: Dict, tone: Dict) -> float:
        confidence = 0.7
        if tone["samples"] > 5:
            confidence += 0.1
        if context.get("sender_insights", {}).get("known"):
            confidence += 0.1
        if context.get("priority", {}).get("score", 5) < 6:
            confidence += 0.05
        return min(0.99, confidence)