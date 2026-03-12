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
    
    def search_events(self, query: str, days: int = 30) -> Dict[str, Any]:
        """
        Search for events by query string in database
        
        Args:
            query: Search term (date like '3/12', 'next week', topic, attendee)
            days: Number of days to search ahead
            
        Returns:
            Matching events
        """
        try:
            from server.database.connection import get_db_session
            from sqlalchemy import text
            from dateutil import parser as date_parser
            
            query_lower = query.lower()
            now = datetime.now(self.timezone)
            
            # Parse relative date terms FIRST
            query_date = None
            start_date = now.date()
            end_date = (now + timedelta(days=days)).date()
            
            relative_terms = {
                'today': (0, 0),
                'tomorrow': (1, 1),
                'this week': (0, 6 - now.weekday()),
                'next week': (7 - now.weekday(), 13 - now.weekday()),
                'this month': (0, 30),
                'next month': (30, 60)
            }
            
            # Check for relative date terms
            date_range_query = False
            for term, (start_offset, end_offset) in relative_terms.items():
                if term in query_lower:
                    start_date = (now + timedelta(days=start_offset)).date()
                    end_date = (now + timedelta(days=end_offset)).date()
                    date_range_query = True
                    break
            
            # If no relative term found, try parsing as specific date
            if not date_range_query:
                try:
                    parsed = date_parser.parse(query, fuzzy=True)
                    query_date = parsed.strftime('%Y-%m-%d')
                except:
                    pass
                
                # Reset end_date for normal queries
                end_date = (now + timedelta(days=days)).date()

            # Query database
            with get_db_session() as db:
                if date_range_query:
                    # Search by date range (relative terms like "next week")
                    sql = text("""
                        SELECT id, event_id, title, date, time, duration,
                               attendees, status, description
                        FROM meetings
                        WHERE date >= :start_date
                        AND date <= :end_date
                        ORDER BY date, time
                    """)
                    result = db.execute(sql, {
                        'start_date': start_date,
                        'end_date': end_date
                    })
                elif query_date:
                    # Search by specific date
                    sql = text("""
                        SELECT id, event_id, title, date, time, duration,
                               attendees, status, description
                        FROM meetings
                        WHERE date = :query_date
                        AND date >= :start_date
                        AND date <= :end_date
                    """)
                    result = db.execute(sql, {
                        'query_date': query_date,
                        'start_date': start_date,
                        'end_date': end_date
                    })
                else:
                    # Search by title or attendees
                    sql = text("""
                        SELECT id, event_id, title, date, time, duration,
                               attendees, status, description
                        FROM meetings
                        WHERE (LOWER(title) LIKE :query OR LOWER(attendees::text) LIKE :query)
                        AND date >= :start_date
                        AND date <= :end_date
                    """)
                    result = db.execute(sql, {
                        'query': f'%{query_lower}%',
                        'start_date': now.date(),
                        'end_date': end_date.date()
                    })
                
                matches = []
                for row in result:
                    matches.append({
                        'id': row.id,
                        'event_id': row.event_id,
                        'title': row.title,
                        'date': str(row.date),
                        'time': str(row.time),
                        'duration': row.duration,
                        'attendees': row.attendees,
                        'status': row.status,
                        'description': row.description
                    })
                
                return {
                    "status": "success",
                    "events": matches,
                    "count": len(matches),
                    "query": query
                }
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return {"status": "error", "error": str(e)}

    def get_events(self, days: int = 7, **kwargs) -> Dict[str, Any]:
        """
        Get upcoming calendar events from database
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of events
        """
        try:
            from server.database.connection import get_db_session
            from sqlalchemy import text
            
            now = datetime.now(self.timezone)
            end_date = now + timedelta(days=days)
            
            with get_db_session() as db:
                result = db.execute(text("""
                    SELECT id, event_id, title, date, time, duration,
                           attendees, status, description
                    FROM meetings
                    WHERE date >= :start_date
                    AND date <= :end_date
                    ORDER BY date, time
                """), {
                    'start_date': now.date(),
                    'end_date': end_date.date()
                })
                
                events = []
                for row in result:
                    # Construct datetime from date + time
                    event_datetime = datetime.combine(row.date, row.time)
                    event_datetime = self.timezone.localize(event_datetime)
                    end_datetime = event_datetime + timedelta(minutes=row.duration)
                    
                    events.append({
                        'id': row.id,
                        'event_id': row.event_id,
                        'title': row.title,
                        'date': str(row.date),
                        'time': str(row.time),
                        'duration': row.duration,
                        'attendees': row.attendees,
                        'status': row.status,
                        'description': row.description
                    })
                
                return {
                    "status": "success",
                    "events": events,
                    "count": len(events),
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
    
