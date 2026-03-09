"""
Meeting Orchestrator - Complex meeting scheduling workflows
Location: server/managers/meeting_orchestrator.py
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from server.managers.email_manager import EmailManager
from server.managers.contact_manager import ContactManager
from server.managers.calendar_block_manager import CalendarBlockManager
from server.managers.calendar_manager import CalendarManager
from datetime import datetime, timedelta

logger = logging.getLogger("meeting_orchestrator")


class MeetingOrchestrator:
    """Orchestrates complex meeting scheduling workflows"""
    
    def __init__(self, email_mgr: EmailManager, calendar_mgr: CalendarManager, contact_mgr: ContactManager):
        self.email_mgr = email_mgr
        self.calendar_mgr = calendar_mgr
        self.contact_mgr = contact_mgr
    
    def _resolve_attendees(self, attendees: List[str]) -> Dict[str, Any]:
        """
        Resolve attendee names to email addresses
        
        Args:
            attendees: List of names or emails
            
        Returns:
            Dict with resolved emails and any errors
        """
        resolved = []
        errors = []
        
        for attendee in attendees:
            # Already an email
            if "@" in attendee:
                resolved.append({
                    "name": attendee,
                    "email": attendee
                })
                continue
            
            # Look up in contacts
            result = self.contact_mgr.get_contact(attendee)
            if result["status"] == "success":
                contact = result["contact"]
                emails = contact.get("emails", [])
                if emails:
                    resolved.append({
                        "name": contact["name"],
                        "email": emails[0]  # Use primary email
                    })
                    # Record interaction
                    self.contact_mgr.record_interaction(attendee)
                else:
                    errors.append(f"Contact '{attendee}' has no email address")
            else:
                errors.append(f"Contact '{attendee}' not found")
        
        return {
            "resolved": resolved,
            "errors": errors
        }
    
    def _draft_meeting_invite(self, title: str, date: str, time: str, 
                              duration: int, attendees: List[Dict]) -> str:
        """
        Draft a meeting invite email
        
        Args:
            title: Meeting title
            date: Date
            time: Time
            duration: Duration in minutes
            attendees: List of attendee dicts
            
        Returns:
            Email body
        """
        attendee_names = ", ".join([a["name"] for a in attendees])
        
        from server.config import get_config
        config = get_config()
        user_name = config.get("user_name", "User")
        ea_name = config.get("ea_name", "JARVIS")
        
        from datetime import datetime
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%A, %B %d, %Y")
        
        time_obj = datetime.strptime(time, "%H:%M")
        formatted_time = time_obj.strftime("%I:%M %p")
        
        recipient = attendees[0]["name"] if len(attendees) == 1 else "Team"
        
        body = f"""Dear {recipient},

I hope this message finds you well.

I would like to invite you to a meeting to discuss {title}.

Meeting Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Subject: {title}
Date: {formatted_date}
Time: {formatted_time}
Duration: {duration} minutes
Attendees: {attendee_names}

Please confirm your availability at your earliest convenience. If this time does not work for you, kindly suggest an alternative that suits your schedule.

I look forward to our discussion.

Best regards,
{user_name}
Executive Assistant: {ea_name}"""

        return body

        
        return body
    
    def schedule_meeting(self, attendees: List[str], title: str, date: str, time: str,
                        duration: int = 60, description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Schedule a meeting with full workflow"""
        try:
            logger.info(f"Scheduling meeting: {title} with {len(attendees)} attendees")
            
            # Step 1: Resolve attendees
            attendee_result = self._resolve_attendees(attendees)
            if attendee_result["errors"]:
                return {"status": "partial_error", "errors": attendee_result["errors"], "message": "Some attendees could not be resolved"}
            resolved_attendees = attendee_result["resolved"]
            
            # Step 2: Check availability
            avail_result = self.calendar_mgr.check_availability(date, time, duration)
            if not avail_result.get("available"):
                return {"status": "error", "error": "Time slot not available", "conflicts": avail_result.get("conflicts", [])}
            
            # Step 3: Create calendar event
            event_result = self.calendar_mgr.add_event(title=title, date=date, time=time, duration=duration, description=description or f"Meeting with {', '.join([a['name'] for a in resolved_attendees])}")
            if event_result["status"] != "success":
                return event_result
            event = event_result["event"]
            
            # Step 4: Draft invite email
            invite_body = self._draft_meeting_invite(title, date, time, duration, resolved_attendees)
            
            # Step 5: Send invites
            invites_sent = []
            failed_invites = []
            for attendee in resolved_attendees:
                try:
                    # Create draft for approval
                    from server.draft_manager import DraftManager
                    draft_mgr = DraftManager()
                    draft_id = draft_mgr.create_draft(
                        to=attendee["email"],
                        subject=f"Meeting Invitation: {title}",
                        body=invite_body,
                        from_account="default",
                        context={"type": "meeting_invite"}
                    )
                    result = {"status": "draft_created", "draft_id": draft_id}
                    if result.get("status") == "draft_created":
                        invites_sent.append({"to": attendee["email"], "name": attendee["name"], "status": "draft_created", "draft_id": draft_id})
                        logger.info(f"Created draft meeting invite for {attendee['email']}")
                    else:
                        failed_invites.append({"to": attendee["email"], "error": result.get("error")})
                except Exception as e:
                    failed_invites.append({"to": attendee["email"], "error": str(e)})
            
            # Step 6: Store in database (optional)
            try:
                from server.database.connection import get_db_session
                from sqlalchemy import text
                import json
                # Check for calendar conflicts before scheduling
                try:
                    from datetime import datetime
                    meeting_start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                    meeting_end = meeting_start + timedelta(minutes=duration)
                    availability = self.calendar_block_mgr.check_availability("default_user", meeting_start, meeting_end)
                    
                    if not availability["available"]:
                        conflicts_str = ", ".join([c["title"] for c in availability["conflicts"]])
                        logger.warning(f"Meeting conflict detected: {conflicts_str}")
                        return {
                            "status": "conflict",
                            "message": f"⚠️ Time slot conflicts with: {conflicts_str}. Would you like to schedule at a different time?",
                            "conflicts": availability["conflicts"]
                        }
                except Exception as conflict_err:
                    logger.warning(f"Conflict check failed (proceeding anyway): {conflict_err}")

                with get_db_session() as db:
                    db.execute(text("INSERT INTO meetings (event_id, user_id, title, date, time, duration, description, attendees, status) VALUES (:eid, :uid, :t, :d, :tm, :dur, :desc, :att, :st)"), 
                              {"eid": event["id"], "uid": "default_user", "t": title, "d": date, "tm": time, "dur": duration, "desc": description or "", "att": json.dumps(resolved_attendees), "st": "scheduled"})
                logger.info(f"Meeting stored in database")
            except:
                pass
            
            return {"status": "success", "meeting": {"event_id": event["id"], "title": title, "date": date, "time": time, "duration": duration, "attendees": resolved_attendees}, "invites_sent": invites_sent, "failed_invites": failed_invites, "drafts_created": [{"draft_id": inv.get("draft_id", inv.get("to")), "to": inv["to"], "name": inv["name"]} for inv in invites_sent], "message": f"Meeting scheduled. Created {len(invites_sent)} draft invitation(s) for approval. Please review in the chat."}
        except Exception as e:
            logger.error(f"Error scheduling meeting: {e}")
            return {"status": "error", "error": str(e)}

    def reschedule_meeting(self, meeting_id: str, new_date: str, new_time: str, **kwargs) -> Dict[str, Any]:
        """
        Reschedule an existing meeting
        
        Args:
            meeting_id: Event ID
            new_date: New date
            new_time: New time
            
        Returns:
            Reschedule result
        """
        try:
            # Get existing event
            event = self.calendar_mgr.get_event_by_id(meeting_id)
            if not event:
                return {"status": "error", "error": f"Meeting {meeting_id} not found"}
            
            # Check new time availability
            duration = event["duration_minutes"]
            avail_result = self.calendar_mgr.check_availability(new_date, new_time, duration)
            
            if not avail_result.get("available"):
                return {
                    "status": "error",
                    "error": "New time slot not available",
                    "conflicts": avail_result.get("conflicts", [])
                }
            
            # Update event
            update_result = self.calendar_mgr.update_event(
                event_id=meeting_id,
                updates={
                    "date": new_date,
                    "time": new_time
                }
            )
            
            if update_result["status"] != "success":
                return update_result
            
            # TODO: Send reschedule notification emails (Phase 3)
            
            return {
                "status": "success",
                "message": f"Meeting rescheduled to {new_date} at {new_time}",
                "event": update_result["event"]
            }
            
        except Exception as e:
            logger.error(f"Error rescheduling meeting: {e}")
            return {"status": "error", "error": str(e)}
    
    def cancel_meeting(self, meeting_id: str, reason: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Cancel a meeting and notify attendees
        
        Args:
            meeting_id: Event ID
            reason: Optional cancellation reason
            
        Returns:
            Cancellation result
        """
        try:
            # Get event details
            event = self.calendar_mgr.get_event_by_id(meeting_id)
            if not event:
                return {"status": "error", "error": f"Meeting {meeting_id} not found"}
            
            # Delete from calendar
            delete_result = self.calendar_mgr.delete_event(meeting_id)
            
            if delete_result["status"] != "success":
                return delete_result
            
            # TODO: Send cancellation emails (Phase 3)
            cancellation_msg = f"The meeting '{event['title']}' has been cancelled."
            if reason:
                cancellation_msg += f"\n\nReason: {reason}"
            
            return {
                "status": "success",
                "message": f"Meeting '{event['title']}' cancelled",
                "notification": cancellation_msg
            }
            
        except Exception as e:
            logger.error(f"Error cancelling meeting: {e}")
            return {"status": "error", "error": str(e)}