"""
Meeting Orchestrator - Complex meeting scheduling workflows
Location: server/managers/meeting_orchestrator.py
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from server.managers.email_manager import EmailManager
from server.managers.calendar_manager import CalendarManager
from server.managers.contact_manager import ContactManager

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
        
        body = f"""Hi everyone,

I'd like to schedule a meeting with the following details:

Meeting: {title}
Date: {date}
Time: {time}
Duration: {duration} minutes
Attendees: {attendee_names}

Please let me know if this time works for you. If you have any conflicts, please suggest an alternative time.

Looking forward to meeting with you all.

Best regards"""
        
        return body
    
    def schedule_meeting(self, attendees: List[str], title: str, date: str, time: str,
                        duration: int = 60, description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Schedule a meeting with full workflow
        
        Workflow:
        1. Resolve attendees to emails
        2. Check calendar availability
        3. Create calendar event
        4. Draft invite emails
        5. Send invites
        6. Return summary
        
        Args:
            attendees: List of attendee names or emails
            title: Meeting title
            date: Date (YYYY-MM-DD)
            time: Time (HH:MM)
            duration: Duration in minutes
            description: Optional description
            
        Returns:
            Meeting scheduling result
        """
        try:
            logger.info(f"Scheduling meeting: {title} with {len(attendees)} attendees")
            
            # Step 1: Resolve attendees
            attendee_result = self._resolve_attendees(attendees)
            if attendee_result["errors"]:
                return {
                    "status": "partial_error",
                    "errors": attendee_result["errors"],
                    "message": "Some attendees could not be resolved"
                }
            
            resolved_attendees = attendee_result["resolved"]
            
            # Step 2: Check availability
            avail_result = self.calendar_mgr.check_availability(date, time, duration)
            if not avail_result.get("available"):
                return {
                    "status": "error",
                    "error": "Time slot not available",
                    "conflicts": avail_result.get("conflicts", [])
                }
            
            # Step 3: Create calendar event
            event_result = self.calendar_mgr.add_event(
                title=title,
                date=date,
                time=time,
                duration=duration,
                description=description or f"Meeting with {', '.join([a['name'] for a in resolved_attendees])}"
            )
            
            if event_result["status"] != "success":
                return event_result
            
            event = event_result["event"]
            
            # Step 4: Draft invite email
            invite_body = self._draft_meeting_invite(title, date, time, duration, resolved_attendees)
            
            # Step 5: Send invites (TODO: Implement in Phase 3)
            # For now, return draft
            invites_sent = []
            for attendee in resolved_attendees:
                # TODO: Actually send email
                invites_sent.append({
                    "to": attendee["email"],
                    "subject": f"Meeting Invitation: {title}",
                    "body": invite_body,
                    "status": "draft"  # Will be "sent" when implemented
                })
            
            logger.info(f"Meeting scheduled: {title} (Event ID: {event['id']})")
            
            return {
                "status": "success",
                "meeting": {
                    "event_id": event["id"],
                    "title": title,
                    "date": date,
                    "time": time,
                    "duration": duration,
                    "attendees": resolved_attendees
                },
                "invites": invites_sent,
                "message": f"Meeting scheduled with {len(resolved_attendees)} attendees"
            }
            
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