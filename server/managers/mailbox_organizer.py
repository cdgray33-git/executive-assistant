"""
Mailbox Organization Manager
Handles batch processing of email backlogs with pause/resume capability
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import text

from server.database.connection import get_db_session
from server.managers.email_manager import EmailManager
from server.managers.account_manager import AccountManager

logger = logging.getLogger("mailbox_organizer")


class MailboxOrganizer:
    """Manages large-scale mailbox organization with progress tracking"""
    
    def __init__(self):
        self.email_mgr = EmailManager()
        self.account_mgr = AccountManager()
    
    def get_progress(self, user_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        """Get current organization progress for account"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT * FROM email_organization_progress
                        WHERE user_id = :user_id AND account_id = :account_id
                    """),
                    {"user_id": user_id, "account_id": account_id}
                )
                row = result.fetchone()
                
                if not row:
                    return None
                
                progress_pct = (row.processed_count / row.total_emails * 100) if row.total_emails > 0 else 0
                
                return {
                    "status": row.status,
                    "progress_percent": round(progress_pct, 2),
                    "processed_count": row.processed_count,
                    "total_emails": row.total_emails,
                    "spam_count": row.spam_count,
                    "keep_count": row.keep_count,
                    "unsure_count": row.unsure_count,
                    "moved_count": row.moved_count,
                    "error_count": row.error_count,
                    "batch_size": row.batch_size,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "estimated_completion": row.estimated_completion.isoformat() if row.estimated_completion else None,
                    "last_error": row.last_error,
                    "can_resume": row.status in ['paused', 'error']
                }
        except Exception as e:
            logger.error(f"Error getting progress: {e}")
            return None
    
    def get_all_progress(self, user_id: str) -> list:
        """Get organization progress for all accounts"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT account_id, email_address, provider, status,
                               processed_count, total_emails, started_at, completed_at
                        FROM email_organization_progress
                        WHERE user_id = :user_id
                        ORDER BY last_update DESC
                    """),
                    {"user_id": user_id}
                )
                rows = result.fetchall()
                
                return [{
                    "account_id": row.account_id,
                    "email_address": row.email_address,
                    "provider": row.provider,
                    "status": row.status,
                    "progress_percent": round((row.processed_count / row.total_emails * 100) if row.total_emails > 0 else 0, 2),
                    "processed_count": row.processed_count,
                    "total_emails": row.total_emails,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None
                } for row in rows]
        except Exception as e:
            logger.error(f"Error getting all progress: {e}")
            return []
    
    def start_organization(self, user_id: str, account_id: str, batch_size: int = 3000) -> Dict[str, Any]:
        """Start or resume mailbox organization"""
        try:
            existing = self.get_progress(user_id, account_id)
            
            if existing and existing['status'] == 'running':
                return {"status": "error", "message": "Organization already in progress"}
            
            accounts = self.account_mgr.vault.list_accounts()
            if account_id not in accounts:
                return {"status": "error", "message": f"Account {account_id} not found"}
            
            account_info = accounts[account_id]
            provider = account_info.get('provider', 'unknown')
            email_address = account_info.get('email', '')
            
            connector = self.account_mgr.get_connector(account_id, cache=False)
            success, msg = connector.connect()
            
            if not success:
                return {"status": "error", "message": f"Connection failed: {msg}"}
            
            logger.info(f"Ensuring folders exist for {account_id}...")
            folder_result = self.email_mgr.ensure_folders_exist(account_id)
            
            # Get total email count (capped at batch_size, max 3000)
            try:
                safe_limit = min(batch_size, 3000)
                emails = connector.preview_emails(count=safe_limit, oldest_first=True)
                total_emails = len(emails)
            except Exception as e:
                logger.warning(f"Could not get exact count: {e}")
                total_emails = batch_size
            connector.disconnect()
            
            with get_db_session() as session:
                if existing and existing['status'] in ['paused', 'error']:
                    session.execute(
                        text("""
                            UPDATE email_organization_progress
                            SET status = 'running', last_update = NOW(), retry_count = retry_count + 1
                            WHERE user_id = :user_id AND account_id = :account_id
                        """),
                        {"user_id": user_id, "account_id": account_id}
                    )
                    action = "resumed"
                else:
                    session.execute(
                        text("""
                            INSERT INTO email_organization_progress
                            (user_id, account_id, provider, email_address, total_emails, batch_size, status, started_at)
                            VALUES (:user_id, :account_id, :provider, :email_address, :total_emails, :batch_size, 'running', NOW())
                            ON CONFLICT (user_id, account_id) 
                            DO UPDATE SET 
                                status = 'running', total_emails = :total_emails, batch_size = :batch_size,
                                processed_count = 0, started_at = NOW(), last_update = NOW()
                        """),
                        {"user_id": user_id, "account_id": account_id, "provider": provider,
                         "email_address": email_address, "total_emails": total_emails, "batch_size": batch_size}
                    )
                    action = "started"
            
            return {
                "status": "success", "action": action, "total_emails": total_emails,
                "batch_size": batch_size, "folders_created": folder_result.get('folders_created', []),
                "message": f"Organization {action} for {email_address}"
            }
        except Exception as e:
            logger.error(f"Error starting organization: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    def pause_organization(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Pause current organization"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        UPDATE email_organization_progress
                        SET status = 'paused', last_update = NOW()
                        WHERE user_id = :user_id AND account_id = :account_id AND status = 'running'
                        RETURNING processed_count
                    """),
                    {"user_id": user_id, "account_id": account_id}
                )
                row = result.fetchone()
                
                if not row:
                    return {"status": "error", "message": "No active organization to pause"}
                
                return {"status": "success", "message": "Organization paused", "processed_count": row.processed_count}
        except Exception as e:
            logger.error(f"Error pausing: {e}")
            return {"status": "error", "message": str(e)}
    
    def cancel_organization(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Cancel organization (not resumable)"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        UPDATE email_organization_progress
                        SET status = 'cancelled', completed_at = NOW(), last_update = NOW()
                        WHERE user_id = :user_id AND account_id = :account_id AND status IN ('running', 'paused')
                        RETURNING processed_count, spam_count, keep_count, unsure_count
                    """),
                    {"user_id": user_id, "account_id": account_id}
                )
                row = result.fetchone()
                
                if not row:
                    return {"status": "error", "message": "No organization to cancel"}
                
                return {
                    "status": "success", "message": "Organization cancelled",
                    "processed_count": row.processed_count, "spam_count": row.spam_count,
                    "keep_count": row.keep_count, "unsure_count": row.unsure_count
                }
        except Exception as e:
            logger.error(f"Error cancelling: {e}")
            return {"status": "error", "message": str(e)}
    
    def retry_organization(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Retry after error"""
        try:
            progress = self.get_progress(user_id, account_id)
            
            if not progress:
                return {"status": "error", "message": "No organization found"}
            
            if progress['status'] != 'error':
                return {"status": "error", "message": "Can only retry after error"}
            
            if progress.get('retry_count', 0) >= 3:
                return {"status": "error", "message": "Max retries (3) exceeded"}
            
            with get_db_session() as session:
                session.execute(
                    text("""
                        UPDATE email_organization_progress
                        SET status = 'running', last_update = NOW(), retry_count = retry_count + 1
                        WHERE user_id = :user_id AND account_id = :account_id
                    """),
                    {"user_id": user_id, "account_id": account_id}
                )
            
            return {"status": "success", "message": "Retrying", "retry_count": progress.get('retry_count', 0) + 1}
        except Exception as e:
            logger.error(f"Error retrying: {e}")
            return {"status": "error", "message": str(e)}
    
    def process_batch(self, user_id: str, account_id: str) -> Dict[str, Any]:
        """Process single batch of emails (called by background task)"""
        try:
            if self._check_pause_flag(user_id, account_id):
                return {"status": "paused", "message": "Organization paused by user"}
            
            progress = self.get_progress(user_id, account_id)
            if not progress or progress['status'] != 'running':
                return {"status": "error", "message": "Not in running state"}
            
            batch_size = progress['batch_size']
            
            # Define progress callback
            def update_progress(counts):
                self._update_progress(user_id, account_id, counts)
            
            result = self.email_mgr.cleanup_spam_safe(
                account_id=account_id,
                max_emails=batch_size,
                auto_categorize=True,
                update_progress_callback=update_progress
            )
            
            if result.get('status') != 'success':
                self._update_progress(user_id, account_id, {
                    'status': 'error',
                    'last_error': result.get('message', 'Unknown error')
                })
                return result
            
            updates = {
                'processed_count': progress['processed_count'] + result.get('total_checked', 0),
                'spam_count': progress['spam_count'] + result.get('spam_count', 0),
                'keep_count': progress['keep_count'] + result.get('keep_count', 0),
                'unsure_count': progress['unsure_count'] + result.get('unsure_count', 0),
                'moved_count': progress['moved_count'] + result.get('categorized_count', 0),
                'current_batch': progress.get('current_batch', 0) + 1
            }
            
            if updates['processed_count'] > 0:
                time_elapsed = (datetime.now() - datetime.fromisoformat(progress['started_at'])).total_seconds()
                rate = updates['processed_count'] / time_elapsed
                remaining = progress['total_emails'] - updates['processed_count']
                eta_seconds = remaining / rate if rate > 0 else 0
                updates['estimated_completion'] = datetime.now() + timedelta(seconds=eta_seconds)
            
            if updates['processed_count'] >= progress['total_emails']:
                updates['status'] = 'completed'
                updates['completed_at'] = datetime.now()
            
            self._update_progress(user_id, account_id, updates)
            
            return {
                "status": "success",
                "processed_this_batch": result.get('total_checked', 0),
                "total_processed": updates['processed_count'],
                "is_complete": updates.get('status') == 'completed'
            }
        except Exception as e:
            logger.error(f"Error processing batch: {e}", exc_info=True)
            self._update_progress(user_id, account_id, {
                'status': 'error',
                'last_error': str(e),
                'error_count': progress.get('error_count', 0) + 1
            })
            return {"status": "error", "message": str(e)}
    
    def _check_pause_flag(self, user_id: str, account_id: str) -> bool:
        """Check if user requested pause"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("SELECT status FROM email_organization_progress WHERE user_id = :user_id AND account_id = :account_id"),
                    {"user_id": user_id, "account_id": account_id}
                )
                row = result.fetchone()
                return row and row.status == 'paused'
        except Exception as e:
            logger.error(f"Error checking pause: {e}")
            return False
    
    def _update_progress(self, user_id: str, account_id: str, updates: Dict) -> None:
        """Update progress in database"""
        try:
            set_clauses = []
            params = {"user_id": user_id, "account_id": account_id}
            
            for key, value in updates.items():
                set_clauses.append(f"{key} = :{key}")
                params[key] = value
            
            set_clauses.append("last_update = NOW()")
            
            query = f"UPDATE email_organization_progress SET {', '.join(set_clauses)} WHERE user_id = :user_id AND account_id = :account_id"
            
            with get_db_session() as session:
                session.execute(text(query), params)
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def cleanup_old_records(self, days: int = 4) -> int:
        """Delete completed/cancelled records older than specified days"""
        try:
            with get_db_session() as session:
                result = session.execute(
                    text("""
                        DELETE FROM email_organization_progress
                        WHERE status IN ('completed', 'cancelled')
                        AND completed_at < NOW() - INTERVAL ':days days'
                        RETURNING id
                    """),
                    {"days": days}
                )
                count = len(result.fetchall())
                logger.info(f"Cleaned up {count} old records")
                return count
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
            return 0
