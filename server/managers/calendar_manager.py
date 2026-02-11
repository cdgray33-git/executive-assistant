"""
Calendar Manager - Calendar event management with iCloud sync
Location: server/managers/calendar_manager.py
"""
import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import pytz

logger = logging.getLogger("calendar_manager")

# Data paths
DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
CALENDAR_FILE = DATA_DIR / "calendar" / "events.json"


class CalendarManager:
    """Manages calendar events with local storage and iCloud sync"""
    
    def __init__(self):
        self.events = self._load_events()
        self.timezone = pytz.timezone('America/New_York')  # TODO: Make configurable
        
    def _load_events(self) -> List[Dict]:
        """Load events from local storage"""
        try:
            if CALENDAR_FILE.exists():
                with open(CALENDAR_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading events: {e}")
            return []
    
    def _save_events(self):
        """Save events to local storage"""
        try:
            CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CALENDAR_FILE, 'w') as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving events: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _parse_datetime(self, date_str: str, time_str: Optional[str] = None) -> datetime:
        """Parse date and time strings into datetime object"""
        try:
            if time_str:
                dt_str = f"{date_str} {time_str}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Make timezone aware
            return self.timezone.localize(dt)
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            raise ValueError(f"Invalid date/time format: {date_str} {time_str}")
    
    def add_event(self, title: str, date: str, time: str, 
                  duration: int = 60, description: str = None, **kwargs) -> Dict[str, Any]:
        """
        Add a calendar event
        
        Args:
            title: Event title
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            duration: Duration in minutes
            description: Optional description
            
        Returns:
            Created event dict
        """
        try:
            start_dt = self._parse_datetime(date, time)
            end_dt = start_dt + timedelta(minutes=duration)
            
            event = {
                "id": self._generate_event_id(),
                "title": title,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "duration_minutes": duration,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            self.events.append(event)
            self._save_events()
            
            # TODO: Sync to iCloud CalDAV (Phase 5)
            
            logger.info(f"Added event: {title} on {date} at {time}")
            
            return {
                "status": "success",
                "event": event
            }
            
        except Exception as e:
            logger.error(f"Error adding event: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_events(self, days: int = 7, **kwargs) -> Dict[str, Any]:
        """
        Get upcoming calendar events
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of events
        """
        try:
            now = datetime.now(self.timezone)
            end_date = now + timedelta(days=days)
            
            upcoming = []
            for event in self.events:
                event_start = datetime.fromisoformat(event["start"])
                if now <= event_start <= end_date:
                    upcoming.append(event)
            
            # Sort by start time
            upcoming.sort(key=lambda e: e["start"])
            
            return {
                "status": "success",
                "events": upcoming,
                "count": len(upcoming),
                "period": f"Next {days} days"
            }
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_availability(self, date: str, time: str, duration: int = 60, **kwargs) -> Dict[str, Any]:
        """
        Check if a time slot is available
        
        Args:
            date: Date to check
            time: Time to check
            duration: Duration needed in minutes
            
        Returns:
            Availability status
        """
        try:
            start_dt = self._parse_datetime(date, time)
            end_dt = start_dt + timedelta(minutes=duration)
            
            # Check for conflicts
            conflicts = []
            for event in self.events:
                event_start = datetime.fromisoformat(event["start"])
                event_end = datetime.fromisoformat(event["end"])
                
                # Check overlap
                if (start_dt < event_end and end_dt > event_start):
                    conflicts.append({
                        "title": event["title"],
                        "start": event["start"],
                        "end": event["end"]
                    })
            
            available = len(conflicts) == 0
            
            return {
                "status": "success",
                "available": available,
                "requested_time": start_dt.isoformat(),
                "conflicts": conflicts
            }
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return {"status": "error", "error": str(e)}
    
    def update_event(self, event_id: str, updates: Dict, **kwargs) -> Dict[str, Any]:
        """
        Update an existing event
        
        Args:
            event_id: Event ID to update
            updates: Dict of fields to update
            
        Returns:
            Updated event
        """
        try:
            event = next((e for e in self.events if e["id"] == event_id), None)
            
            if not event:
                return {"status": "error", "error": f"Event {event_id} not found"}
            
            # Update fields
            for key, value in updates.items():
                if key in ["date", "time", "duration"]:
                    # Recalculate start/end times
                    if "date" in updates or "time" in updates:
                        date = updates.get("date", event["start"].split("T")[0])
                        time = updates.get("time", event["start"].split("T")[1][:5])
                        duration = updates.get("duration", event["duration_minutes"])
                        
                        start_dt = self._parse_datetime(date, time)
                        end_dt = start_dt + timedelta(minutes=duration)
                        
                        event["start"] = start_dt.isoformat()
                        event["end"] = end_dt.isoformat()
                        event["duration_minutes"] = duration
                else:
                    event[key] = value
            
            event["updated_at"] = datetime.now().isoformat()
            self._save_events()
            
            # TODO: Sync to iCloud (Phase 5)
            
            return {
                "status": "success",
                "event": event
            }
            
        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {"status": "error", "error": str(e)}
    
    def delete_event(self, event_id: str, **kwargs) -> Dict[str, Any]:
        """
        Delete a calendar event
        
        Args:
            event_id: Event ID to delete
            
        Returns:
            Deletion status
        """
        try:
            event = next((e for e in self.events if e["id"] == event_id), None)
            
            if not event:
                return {"status": "error", "error": f"Event {event_id} not found"}
            
            self.events.remove(event)
            self._save_events()
            
            # TODO: Sync to iCloud (Phase 5)
            
            return {
                "status": "success",
                "message": f"Deleted event: {event['title']}"
            }
            
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_event_by_id(self, event_id: str) -> Optional[Dict]:
        """Get a specific event by ID"""
        return next((e for e in self.events if e["id"] == event_id), None)
    
    def search_events(self, query: str) -> List[Dict]:
        """Search events by title or description"""
        query = query.lower()
        return [
            e for e in self.events 
            if query in e["title"].lower() or 
               (e.get("description") and query in e["description"].lower())
        ]