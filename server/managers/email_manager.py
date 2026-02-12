"""
Updated Email Manager with multi-connector support
Location: server/managers/email_manager.py (REPLACE EXISTING)
"""
import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from server.managers.account_manager import AccountManager
from server.spam_detector import SpamDetector
from server.llm.ollama_adapter import OllamaAdapter

logger = logging.getLogger("email_manager")

# Data paths
DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
LEARNING_FILE = DATA_DIR / "intelligence" / "sender_history.json"

# Email categories (18 total)
EMAIL_CATEGORIES = [
    "Priority",
    "Personal",
    "Work",
    "School",
    "Private",
    "Finance",
    "Shopping",
    "Calendar & Events",
    "Social Media",
    "Newsletters",
    "Photos & Media",
    "Productivity",
    "Family",
    "Health & Medical",
    "Receipts & Confirmations",
    "Spam",
    "Archive",
    "Inbox"
]


class EmailManager:
    """Manages all email operations across multiple accounts"""
    
    def __init__(self):
        self.account_mgr = AccountManager()
        self.spam_detector = SpamDetector()
        self.ollama = OllamaAdapter()
        self.sender_history = self._load_sender_history()
        
    def _load_sender_history(self) -> Dict:
        """Load sender history for learning"""
        try:
            if LEARNING_FILE.exists():
                with open(LEARNING_FILE, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading sender history: {e}")
            return {}
    
    def _save_sender_history(self):
        """Save updated sender history"""
        try:
            LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LEARNING_FILE, 'w') as f:
                json.dump(self.sender_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving sender history: {e}")
    
    def _categorize_email(self, email: Dict) -> str:
        """
        Categorize an email using AI and learning patterns
        
        Args:
            email: Email dict with sender, subject, body, etc.
            
        Returns:
            Category name
        """
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        
        # Check if spam
        spam_result = self.spam_detector.categorize_message(
            subject=email.get("subject", ""),
            sender=email.get("from", ""),
            body=email.get("body", "")
        )
        if spam_result.get("category") == "spam":
            return "Spam"
        
        # Check learned patterns
        if sender in self.sender_history:
            history = self.sender_history[sender]
            if history.get("category") and history.get("confidence", 0) > 0.8:
                return history["category"]
        
        # Check for calendar invites
        if "invite" in subject or ".ics" in str(email.get("attachments", [])):
            return "Calendar & Events"
        
        # Check for attachments
        attachments = email.get("attachments", [])
        if attachments:
            extensions = [att.get("filename", "").split(".")[-1].lower() for att in attachments]
            if any(ext in ["jpg", "jpeg", "png", "gif", "mp4", "mov"] for ext in extensions):
                return "Photos & Media"
            if any(ext in ["docx", "pptx", "xlsx", "pdf"] for ext in extensions):
                return "Productivity"
        
        # Use AI for categorization
        prompt = f"""Categorize this email into ONE of these categories:
{', '.join(EMAIL_CATEGORIES)}

Email details:
From: {email.get('from', '')}
Subject: {email.get('subject', '')}
Preview: {email.get('body', '')[:200]}

Respond with ONLY the category name, nothing else."""
        
        try:
            response = self.ollama.generate(prompt, model="qwen2.5:7b-instruct")
            category = response.strip()
            
            # Validate category
            if category in EMAIL_CATEGORIES:
                # Update learning
                if sender not in self.sender_history:
                    self.sender_history[sender] = {
                        "category": category,
                        "confidence": 0.5,
                        "count": 1
                    }
                else:
                    hist = self.sender_history[sender]
                    if hist.get("category") == category:
                        hist["confidence"] = min(1.0, hist["confidence"] + 0.1)
                        hist["count"] = hist.get("count", 0) + 1
                
                self._save_sender_history()
                return category
            
        except Exception as e:
            logger.error(f"AI categorization failed: {e}")
        
        # Default to Inbox
        return "Inbox"
    
    def _calculate_priority_score(self, email: Dict) -> float:
        """
        Calculate priority score (0-10) for an email
        
        Args:
            email: Email dict
            
        Returns:
            Priority score (higher = more urgent)
        """
        score = 5.0  # Base score
        
        sender = email.get("from", "").lower()
        subject = email.get("subject", "").lower()
        
        # Check sender history
        if sender in self.sender_history:
            history = self.sender_history[sender]
            if history.get("priority_boost"):
                score += 3.0
        
        # Urgency keywords in subject
        urgent_keywords = ["urgent", "asap", "important", "action required", "immediate"]
        if any(keyword in subject for keyword in urgent_keywords):
            score += 2.0
        
        # Calendar invite
        if "invite" in subject or "meeting" in subject:
            score += 1.5
        
        # Reply to existing thread (user was engaged)
        if subject.startswith("re:"):
            score += 1.0
        
        return min(10.0, score)
    
    def check_all_accounts(self) -> Dict[str, Any]:
        """Check all email accounts for new messages"""
        results = {
            "total_new": 0,
            "by_account": {},
            "priority_messages": [],
            "timestamp": datetime.now().isoformat()
        }
        
        accounts = self.account_mgr.vault.list_accounts()
        
        for account_id, metadata in accounts.items():
            try:
                connector = self.account_mgr.get_connector(account_id, cache=False)
                success, message = connector.connect()
                
                if not success:
                    results["by_account"][account_id] = {"error": message}
                    continue
                
                # Get new messages
                emails = connector.preview_emails(count=50, oldest_first=False)
                connector.disconnect()
                
                new_count = len(emails)
                results["total_new"] += new_count
                
                # Categorize and check priority
                priority_emails = []
                for email in emails:
                    category = self._categorize_email(email)
                    priority_score = self._calculate_priority_score(email)
                    
                    if priority_score >= 8.0:
                        priority_emails.append({
                            "account": account_id,
                            "email": metadata.get("email"),
                            "subject": email.get("subject"),
                            "from": email.get("from"),
                            "priority_score": priority_score,
                            "category": category
                        })
                
                results["by_account"][account_id] = {
                    "email": metadata.get("email"),
                    "new_messages": new_count,
                    "priority_count": len(priority_emails)
                }
                results["priority_messages"].extend(priority_emails)
                
            except Exception as e:
                logger.error(f"Error checking account {account_id}: {e}")
                results["by_account"][account_id] = {"error": str(e)}
        
        return results
    
    def send_email(self, to: str, subject: str, body: str, 
                  from_account: Optional[str] = None,
                  cc: Optional[List[str]] = None,
                  bcc: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to: Recipient email or name
            subject: Email subject
            body: Email body
            from_account: Optional specific account to send from
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            Result dict
        """
        try:
            # Resolve recipient name to email if needed
            if "@" not in to:
                # TODO: Lookup in contacts (already implemented in Phase 2)
                return {"status": "error", "error": "Contact lookup not yet integrated"}
            
            # Select sending account
            if from_account:
                metadata = self.account_mgr.vault.get_account_metadata(from_account)
                if not metadata:
                    return {"status": "error", "error": f"Account {from_account} not found"}
                account_id = from_account
            else:
                # Smart account selection (use first account for now)
                # TODO: Implement smart selection in Phase 4
                accounts = self.account_mgr.vault.list_accounts()
                if not accounts:
                    return {"status": "error", "error": "No email accounts configured"}
                account_id = list(accounts.keys())[0]
            
            # Get connector and send
            connector = self.account_mgr.get_connector(account_id, cache=False)
            success, message = connector.connect()
            
            if not success:
                return {"status": "error", "error": message}
            
            result = connector.send_message(to, subject, body, cc=cc, bcc=bcc)
            connector.disconnect()
            
            if result.get("success"):
                return {
                    "status": "success",
                    "from": account_id,
                    "to": to,
                    "message": "Email sent successfully"
                }
            else:
                return {
                    "status": "error",
                    "error": result.get("error", "Unknown error")
                }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"status": "error", "error": str(e)}
    
    def draft_email(self, to: str, subject: str, context: str) -> Dict[str, Any]:
        """
        Draft an email using AI
        
        Args:
            to: Recipient
            subject: Subject
            context: What the email is about
            
        Returns:
            Drafted email dict
        """
        try:
            # TODO: Implement tone learning (Phase 4)
            # For now, use neutral professional tone
            
            prompt = f"""Draft a professional email with these details:

To: {to}
Subject: {subject}
Context: {context}

Write a clear, professional email. Include appropriate greeting and closing."""
            
            body = self.ollama.generate(prompt, model="qwen2.5:7b-instruct")
            
            return {
                "status": "success",
                "draft": {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "created_at": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error drafting email: {e}")
            return {"status": "error", "error": str(e)}
    
    def search_email(self, query: str, account: Optional[str] = None) -> Dict[str, Any]:
        """
        Search emails across accounts
        
        Args:
            query: Search terms
            account: Optional specific account
            
        Returns:
            Search results
        """
        # TODO: Implement full-text search (Phase 4)
        return {
            "status": "not_implemented",
            "message": "Email search will be implemented in Phase 4"
        }
    
    def categorize_all_accounts(self) -> Dict[str, Any]:
        """
        Automatically categorize and organize all inboxes
        
        Returns:
            Categorization summary
        """
        results = {
            "total_categorized": 0,
            "by_category": {cat: 0 for cat in EMAIL_CATEGORIES},
            "by_account": {},
            "timestamp": datetime.now().isoformat()
        }
        
        accounts = self.account_mgr.vault.list_accounts()
        
        for account_id, metadata in accounts.items():
            try:
                connector = self.account_mgr.get_connector(account_id, cache=False)
                success, message = connector.connect()
                
                if not success:
                    continue
                
                # Get inbox messages
                emails = connector.preview_emails(count=100, oldest_first=True)
                
                account_results = {cat: 0 for cat in EMAIL_CATEGORIES}
                
                for email in emails:
                    category = self._categorize_email(email)
                    results["by_category"][category] += 1
                    account_results[category] += 1
                    results["total_categorized"] += 1
                    
                    # Move to folder if connector supports it
                    if hasattr(connector, 'move_to_folder') and category != "Inbox":
                        try:
                            connector.move_to_folder([email["id"]], category)
                        except Exception as e:
                            logger.warning(f"Failed to move email to {category}: {e}")
                
                connector.disconnect()
                
                results["by_account"][account_id] = {
                    "email": metadata.get("email"),
                    "categorized": sum(account_results.values()),
                    "by_category": account_results
                }
                
            except Exception as e:
                logger.error(f"Error categorizing account {account_id}: {e}")
        
        return results
    def ensure_folders_exist(self, account_id: str) -> Dict[str, Any]:
        """
        Create email folders/labels for all categories if they don't exist
        Works with IMAP (Yahoo, Apple, Comcast) - creates folders
        Gmail/Hotmail use labels (handled differently)
        
        Args:
            account_id: Email account to set up folders for
            
        Returns:
            {
                "status": "success"|"error",
                "account_id": str,
                "folders_created": [list of new folders],
                "folders_existing": [list of existing folders],
                "provider": "yahoo"|"gmail"|etc
            }
        """
        try:
            connector = self.account_mgr.get_connector(account_id)
            success, msg = connector.connect()
            
            if not success:
                return {"status": "error", "error": msg}
            
            provider = connector.provider if hasattr(connector, 'provider') else 'unknown'
            
            # Get existing folders
            if hasattr(connector, 'list_folders'):
                existing_folders = connector.list_folders()
            else:
                # Fallback for connectors without list_folders
                try:
                    import imaplib
                    if hasattr(connector, 'imap'):
                        _, folder_list = connector.imap.list()
                        existing_folders = [f.decode().split('"')[-2] for f in folder_list]
                    else:
                        existing_folders = []
                except:
                    existing_folders = []
            
            folders_created = []
            folders_existing = []
            
            # Create folders for each category (except Inbox - that always exists)
            for category in EMAIL_CATEGORIES:
                if category == "Archive":
                    continue  # Archive is usually built-in
                
                # Check if folder exists (case-insensitive)
                folder_exists = any(category.lower() in str(f).lower() for f in existing_folders)
                
                if folder_exists:
                    folders_existing.append(category)
                else:
                    # Create folder
                    try:
                        if hasattr(connector, 'create_folder'):
                            connector.create_folder(category)
                        elif hasattr(connector, 'imap'):
                            # Direct IMAP folder creation
                            connector.imap.create(category)
                        folders_created.append(category)
                        logger.info(f"Created folder: {category} in {account_id}")
                    except Exception as e:
                        logger.warning(f"Could not create folder {category}: {e}")
            
            connector.disconnect()
            
            return {
                "status": "success",
                "account_id": account_id,
                "provider": provider,
                "folders_created": folders_created,
                "folders_existing": folders_existing,
                "total_folders": len(EMAIL_CATEGORIES),
                "message": f"Setup complete: {len(folders_created)} folders created, {len(folders_existing)} already existed"
            }
            
        except Exception as e:
            logger.error(f"Folder setup error for {account_id}: {e}")
            return {
                "status": "error",
                "account_id": account_id,
                "error": str(e)
            }
    
    
    def setup_all_accounts(self) -> Dict[str, Any]:
        """
        Ensure folders exist for ALL configured accounts
        Run this on first launch or when adding new accounts
        """
        accounts = self.account_mgr.vault.list_accounts()
        results = []
        
        for account_id in accounts:
            result = self.ensure_folders_exist(account_id)
            results.append(result)
        
        total_created = sum(len(r.get('folders_created', [])) for r in results)
        
        return {
            "status": "success",
            "accounts_processed": len(accounts),
            "total_folders_created": total_created,
            "results": results
        }
    def ensure_folders_exist(self, account_id: str) -> Dict[str, Any]:
        """
        Create email folders/labels for all categories if they don't exist
        Works with IMAP (Yahoo, Apple, Comcast) - creates folders
        
        Args:
            account_id: Email account to setup folders for
            
        Returns:
            {"status": "success", "folders_created": [...], "folders_existing": [...]}
        """
        try:
            connector = self.account_mgr.get_connector(account_id)
            success, msg = connector.connect()
            
            if not success:
                return {"status": "error", "error": msg}
            
            provider = connector.provider if hasattr(connector, 'provider') else 'unknown'
            
            # Get existing folders
            existing_folders = []
            try:
                if hasattr(connector, 'list_folders'):
                    existing_folders = connector.list_folders()
                elif hasattr(connector, 'imap'):
                    _, folder_list = connector.imap.list()
                    existing_folders = [f.decode().split('"')[-2] for f in folder_list]
            except:
                pass
            
            folders_created = []
            folders_existing = []
            
            # Create folders for each category (except Inbox/Archive - built-in)
            for category in EMAIL_CATEGORIES:
                if category in ["Archive"]:
                    continue
                
                # Check if folder exists (case-insensitive)
                folder_exists = any(category.lower() in str(f).lower() for f in existing_folders)
                
                if folder_exists:
                    folders_existing.append(category)
                else:
                    # Create folder
                    try:
                        if hasattr(connector, 'create_folder'):
                            connector.create_folder(category)
                        elif hasattr(connector, 'imap'):
                            connector.imap.create(category)
                        folders_created.append(category)
                        logger.info(f"Created folder: {category} in {account_id}")
                    except Exception as e:
                        logger.warning(f"Could not create folder {category}: {e}")
            
            connector.disconnect()
            
            return {
                "status": "success",
                "account_id": account_id,
                "provider": provider,
                "folders_created": folders_created,
                "folders_existing": folders_existing,
                "total_folders": len(EMAIL_CATEGORIES),
                "message": f"Setup complete: {len(folders_created)} created, {len(folders_existing)} existed"
            }
            
        except Exception as e:
            logger.error(f"Folder setup error for {account_id}: {e}")
            return {"status": "error", "account_id": account_id, "error": str(e)}
    
    
    def setup_all_accounts(self) -> Dict[str, Any]:
        """
        Ensure folders exist for ALL configured accounts
        Run this on first launch or when adding new accounts
        """
        accounts = self.account_mgr.vault.list_accounts()
        results = []
        
        for account_id in accounts:
            result = self.ensure_folders_exist(account_id)
            results.append(result)
        
        total_created = sum(len(r.get('folders_created', [])) for r in results)
        
        return {
            "status": "success",
            "accounts_processed": len(accounts),
            "total_folders_created": total_created,
            "results": results
        }
    def cleanup_spam_safe(self, max_emails=50, **kwargs):
        """
        AI-powered spam cleanup for Gmail accounts.
        Moves detected spam to trash for user review (soft delete).
        Similar to cleanup_spam.py but integrated with EmailManager.
        """
        from server.spam_detector import SpamDetector
        from server.connectors.gmail_connector import GmailConnector
        import logging
        
        logger = logging.getLogger("email_manager")
        
        try:
            # Check all Gmail accounts for unread emails
            check_result = self.check_all_accounts()
            
            if check_result.get("status") != "success":
                return {"status": "error", "message": "Failed to check email accounts"}
            
            # Collect unread emails from all accounts
            all_unread = []
            for account_id, account_data in check_result.get("accounts", {}).items():
                unread = account_data.get("unread_emails", [])
                for email in unread:
                    email["account_id"] = account_id
                all_unread.extend(unread)
            
            if not all_unread:
                return {
                    "status": "success",
                    "trashed_count": 0,
                    "total_checked": 0,
                    "message": "No unread emails to process"
                }
            
            # Limit to max_emails
            emails_to_check = all_unread[:max_emails]
            
            # Use AI spam detector (same as your cleanup_spam.py)
            logger.info(f"Running AI spam detection on {len(emails_to_check)} emails...")
            detector = SpamDetector()
            categorized = detector.batch_categorize(emails_to_check)
            
            # Filter spam emails
            spam_emails = [e for e in categorized if e.get("category") == "spam"]
            
            logger.info(f"AI detected {len(spam_emails)} spam emails out of {len(emails_to_check)}")
            
            if not spam_emails:
                return {
                    "status": "success",
                    "trashed_count": 0,
                    "total_checked": len(emails_to_check),
                    "message": "No spam detected in this batch!"
                }
            
            # Move spam to trash (soft delete like your Yahoo script does)
            trashed_count = 0
            failed_count = 0
            
            for email in spam_emails:
                try:
                    account_id = email.get("account_id")
                    email_id = email.get("id")
                    
                    # Get Gmail connector
                    gmail = GmailConnector(account_id)
                    
                    # Trash the email (moves to Trash, NOT permanent)
                    gmail.service.users().messages().trash(
                        userId='me',
                        id=email_id
                    ).execute()
                    
                    trashed_count += 1
                    logger.info(f"Trashed: {email.get('subject')} from {email.get('from')}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to trash email {email_id}: {e}")
            
            return {
                "status": "success",
                "trashed_count": trashed_count,
                "failed_count": failed_count,
                "total_checked": len(emails_to_check),
                "spam_found": len(spam_emails),
                "spam_details": [
                    {
                        "from": e.get("from"),
                        "subject": e.get("subject"),
                        "reasoning": e.get("reasoning")
                    }
                    for e in spam_emails[:5]
                ],
                "message": f"AI detected {len(spam_emails)} spam emails. Moved {trashed_count} to Trash for review. {failed_count} failed."
            }
            
        except Exception as e:
            logger.error(f"Cleanup spam safe failed: {e}")
            return {"status": "error", "message": str(e)}
