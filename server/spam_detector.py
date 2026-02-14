"""
AI-powered spam detector using Ollama LLM
Categorizes emails as spam/keep/unsure with reasoning
"""
import logging
from typing import List, Dict
from server.llm.ollama_adapter import OllamaAdapter

logger = logging.getLogger("spam_detector")

class SpamDetector:
    """Uses Ollama to intelligently categorize emails"""
    
    def __init__(self, model_name: str = "qwen2.5:7b-instruct"):
        self.ollama = OllamaAdapter()
        self.model = model_name
    
    def categorize_email(self, email: Dict) -> Dict:
        """
        Categorize a single email using AI
        Returns: {"category": "spam"|"keep"|"unsure", "reasoning": "...", ...}
        """
        prompt = self._build_prompt(email)
        
        try:
            response = self.ollama.generate(
                model=self.model,
                prompt=prompt,
                temperature=0.1  # Low temp for consistent categorization
            )
            
            # DEBUG: Print what we got
            print(f"\n?? DEBUG - Raw Ollama response type: {type(response)}")
            print(f"?? DEBUG - Raw Ollama response: {response[:500] if isinstance(response, str) else response}")
            
            # FIX: Handle Ollama response object properly
            if isinstance(response, dict):
                # If response is a dict, extract the content
                response_text = response.get('message', {}).get('content', '') or response.get('response', '')
            elif hasattr(response, 'message'):
                # If response is an object with message attribute
                response_text = response.message.content if hasattr(response.message, 'content') else str(response)
            else:
                # Fallback to string conversion
                response_text = str(response)
            
            print(f"?? DEBUG - Extracted text: {response_text[:300] if response_text else 'EMPTY!'}")
            
            category, reasoning = self._parse_response(response_text)
            
            print(f"?? DEBUG - Parsed category: {category}, reasoning: {reasoning[:100] if reasoning else 'NONE'}\n")
            
            return {
                **email,
                "category": category,
                "reasoning": reasoning
            }
        
        except Exception as e:
            logger.error(f"Categorization failed for {email.get('id')}: {e}")
            print(f"? EXCEPTION: {e}")
            return {
                **email,
                "category": "unsure",
                "reasoning": f"Error: {str(e)}"
            }
    
    def batch_categorize(self, emails: List[Dict], 
                         batch_size: int = 10) -> List[Dict]:
        """
        Categorize multiple emails in batches
        Shows progress for large batches
        """
        results = []
        total = len(emails)
        
        logger.info(f"Categorizing {total} emails...")
        
        for i in range(0, total, batch_size):
            batch = emails[i:i+batch_size]
            
            for email in batch:
                result = self.categorize_email(email)
                results.append(result)
            
            # Progress logging
            done = min(i + batch_size, total)
            logger.info(f"Progress: {done}/{total} emails categorized")
        
        # Summary
        spam_count = sum(1 for r in results if r.get("category") == "spam")
        keep_count = sum(1 for r in results if r.get("category") == "keep")
        unsure_count = sum(1 for r in results if r.get("category") == "unsure")
        
        logger.info(f"? Done: {spam_count} spam, {keep_count} keep, {unsure_count} unsure")
        
        return results
    
    def _build_prompt(self, email: Dict) -> str:
        """Build categorization prompt for the LLM"""
        return f"""You are an email categorization assistant. Analyze this email and categorize it as SPAM, KEEP, or UNSURE.

**Email Details:**
From: {email.get('from', 'Unknown')}
Subject: {email.get('subject', 'No subject')}
Date: {email.get('date', 'Unknown')}
Size: {email.get('size_kb', 0)} KB

**Instructions:**
- SPAM: Promotional emails, newsletters, automated notifications, marketing, social media updates, etc.
- KEEP: Personal emails, important business correspondence, financial statements, receipts
- UNSURE: Can't determine with confidence

**Response format (use EXACTLY this format):**
CATEGORY: [SPAM|KEEP|UNSURE]
REASONING: [Brief explanation]

Respond now:"""
    
    def _parse_response(self, response: str) -> tuple:
        """
        Parse LLM response into category and reasoning
        Returns: (category, reasoning)
        """
        response = response.strip().upper()
        
        # Extract category
        category = "unsure"  # default
        if "CATEGORY:" in response:
            for line in response.split('\n'):
                if line.strip().startswith("CATEGORY:"):
                    cat_value = line.split(":", 1)[1].strip()
                    if "SPAM" in cat_value:
                        category = "spam"
                    elif "KEEP" in cat_value:
                        category = "keep"
                    elif "UNSURE" in cat_value:
                        category = "unsure"
                    break
        
        # Extract reasoning
        reasoning = ""
        if "REASONING:" in response:
            parts = response.split("REASONING:", 1)
            if len(parts) > 1:
                reasoning = parts[1].strip().split('\n')[0][:200]  # First 200 chars
        
        if not reasoning:
            reasoning = "No reasoning provided"
        
        return category.lower(), reasoning
