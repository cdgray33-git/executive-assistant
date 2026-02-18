"""
Meeting Response Monitor Service
Polls emails for meeting responses and updates database
"""
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from server.managers.email_manager import EmailManager
from server.managers.meeting_response_parser import MeetingResponseParser
from server.database.connection import get_db_connection
from sqlalchemy import text

logger = logging.getLogger(__name__)

class MeetingResponseMonitor:
    def __init__(self, email_manager: EmailManager, poll_interval: int = 180):
        """
        Initialize meeting response monitor
        
        Args:
            email_manager: EmailManager instance
            poll_interval: Polling interval in seconds (default 180 = 3 minutes)
        """
        self.email_manager = email_manager
        self.parser = MeetingResponseParser()
        self.poll_interval = poll_interval
        self.running = False
        
    async def start(self):
        """Start monitoring service"""
        self.running = True
        logger.info(f"Meeting response monitor started (polling every {self.poll_interval}s)")
        
        while self.running:
            try:
                await self._check_responses()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)  # Wait 1 min on error
    
    def stop(self):
        """Stop monitoring service"""
        self.running = False
        logger.info("Meeting response monitor stopped")
    
    async def _check_responses(self):
        """Check for new meeting responses"""
        try:
            # Get meetings that need response checking
            meetings = self._get_pending_meetings()
            
            if not meetings:
                return
            
            logger.info(f"Checking responses for {len(meetings)} meeting(s)")
            
            # Get new emails since last check
            primary_account = self.email_manager.get_primary_account()
            if not primary_account:
                logger.warning("No primary email account configured")
                return
            
            # Fetch recent emails (last 24 hours)
            since_date = datetime.now() - timedelta(days=1)
            emails = self.email_manager.get_messages(
                account_id=primary_account,
                folder="INBOX",
                limit=50
            )
            
            if not emails or emails.get("status") != "success":
                return
            
            # Parse each email for meeting responses
            for email in emails.get("messages", []):
                response = self.parser.parse_response(email)
                
                if response:
                    self._process_response(response, meetings)
            
            # Update last_checked timestamp
            self._update_last_checked(meetings)
            
        except Exception as e:
            logger.error(f"Response check failed: {e}")
    
    def _get_pending_meetings(self) -> List[Dict]:
        """Get meetings awaiting responses"""
        try:
            with get_db_connection() as db:
                meetings = db.execute(text("""
                    SELECT id, event_id, ics_uid, title, attendees, 
                           date, time, duration, last_checked
                    FROM meetings
                    WHERE status = 'scheduled'
                    AND response_status IN ('pending', 'partial')
                    AND date >= CURRENT_DATE
                    AND (last_checked IS NULL OR last_checked < NOW() - INTERVAL '3 minutes')
                    ORDER BY date, time
                    LIMIT 20
                """)).fetchall()
                
                return [{
                    "id": m[0],
                    "event_id": m[1],
                    "ics_uid": m[2],
                    "title": m[3],
                    "attendees": m[4],
                    "date": m[5],
                    "time": m[6],
                    "duration": m[7],
                    "last_checked": m[8]
                } for m in meetings]
                
        except Exception as e:
            logger.error(f"Get pending meetings failed: {e}")
            return []
    
    def _process_response(self, response: Dict[str, Any], meetings: List[Dict]):
        """Process a meeting response and update database"""
        try:
            # Find matching meeting by ICS UID or title
            meeting = None
            for m in meetings:
                if response.get("ics_uid") and m.get("ics_uid") == response["ics_uid"]:
                    meeting = m
                    break
            
            if not meeting:
                return
            
            logger.info(f"Processing {response['type']} from {response['attendee_email']} for meeting: {meeting['title']}")
            
            # Update attendee responses
            with get_db_connection() as db:
                # Get current attendee responses
                result = db.execute(text("""
                    SELECT attendee_responses FROM meetings WHERE id = :mid
                """), {"mid": meeting["id"]}).fetchone()
                
                current_responses = result[0] if result and result[0] else []
                
                # Add/update this response
                updated = False
                for i, resp in enumerate(current_responses):
                    if resp.get("email") == response["attendee_email"]:
                        current_responses[i] = {
                            "email": response["attendee_email"],
                            "status": response["type"],
                            "timestamp": datetime.now().isoformat(),
                            "message": response.get("message"),
                            "proposed_time": response.get("proposed_time")
                        }
                        updated = True
                        break
                
                if not updated:
                    current_responses.append({
                        "email": response["attendee_email"],
                        "status": response["type"],
                        "timestamp": datetime.now().isoformat(),
                        "message": response.get("message"),
                        "proposed_time": response.get("proposed_time")
                    })
                
                # Determine overall response status
                attendees = meeting.get("attendees", [])
                total_attendees = len(attendees) if isinstance(attendees, list) else 1
                response_count = len(current_responses)
                
                if response_count == 0:
                    overall_status = "pending"
                elif response_count < total_attendees:
                    overall_status = "partial"
                else:
                    # Check if all accepted
                    all_accepted = all(r["status"] == "accept" for r in current_responses)
                    overall_status = "confirmed" if all_accepted else "partial"
                
                # Update database
                db.execute(text("""
                    UPDATE meetings
                    SET attendee_responses = :responses,
                        response_status = :status,
                        updated_at = NOW()
                    WHERE id = :mid
                """), {
                    "responses": current_responses,
                    "status": overall_status,
                    "mid": meeting["id"]
                })
                db.commit()
                
                logger.info(f"Updated meeting {meeting['id']}: {overall_status} ({response_count}/{total_attendees} responses)")
                
        except Exception as e:
            logger.error(f"Process response failed: {e}")
    
    def _update_last_checked(self, meetings: List[Dict]):
        """Update last_checked timestamp for meetings"""
        try:
            meeting_ids = [m["id"] for m in meetings]
            if not meeting_ids:
                return
            
            with get_db_connection() as db:
                db.execute(text("""
                    UPDATE meetings
                    SET last_checked = NOW()
                    WHERE id = ANY(:ids)
                """), {"ids": meeting_ids})
                db.commit()
                
        except Exception as e:
            logger.error(f"Update last_checked failed: {e}")
