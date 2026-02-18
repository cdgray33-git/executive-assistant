"""
Calendar Assistant Functions - Block management and availability checking
These functions are registered with the agent for calendar blocking
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from server.managers.calendar_block_manager import CalendarBlockManager

logger = logging.getLogger(__name__)

# Initialize manager
calendar_block_mgr = CalendarBlockManager()

def block_calendar(title: str, start_time: str, end_time: str = None, 
                   duration_minutes: int = None, block_type: str = "busy",
                   description: str = None, user_id: str = "default_user") -> Dict[str, Any]:
    """
    Block time on user's calendar
    
    Args:
        title: Block title (e.g., "Lunch", "Out of Office", "Gym")
        start_time: Start time (natural language or ISO format)
        end_time: End time (optional if duration provided)
        duration_minutes: Duration in minutes (optional if end_time provided)
        block_type: busy, out-of-office, lunch, meeting, personal
        description: Optional description
        user_id: User identifier
        
    Examples:
        "Block my calendar tomorrow 12-1pm for lunch"
        "I'm out of office next Monday"
        "Block 9-10am daily for gym" (recurring not implemented yet)
    """
    try:
        # Parse start time
        start_dt = dateparser.parse(start_time)
        if not start_dt:
            return {"status": "error", "error": f"Could not parse start time: {start_time}"}
        
        # Calculate end time
        if end_time:
            end_dt = dateparser.parse(end_time)
            if not end_dt:
                return {"status": "error", "error": f"Could not parse end time: {end_time}"}
        elif duration_minutes:
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        else:
            # Default to 1 hour
            end_dt = start_dt + timedelta(hours=1)
        
        # Validate times
        if end_dt <= start_dt:
            return {"status": "error", "error": "End time must be after start time"}
        
        # Check for conflicts
        availability = calendar_block_mgr.check_availability(user_id, start_dt, end_dt)
        
        if not availability["available"]:
            conflicts_str = ", ".join([f"{c['title']} ({c['start']} - {c['end']})" 
                                      for c in availability["conflicts"]])
            return {
                "status": "conflict",
                "message": f"Time slot conflicts with: {conflicts_str}",
                "conflicts": availability["conflicts"],
                "suggestion": "Would you like me to find an alternative time?"
            }
        
        # Block the calendar
        result = calendar_block_mgr.block_calendar(
            user_id=user_id,
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            block_type=block_type,
            description=description
        )
        
        return result
        
    except Exception as e:
        logger.error(f"block_calendar failed: {e}")
        return {"status": "error", "error": str(e)}


def check_availability(date: str = None, start_time: str = None, 
                      end_time: str = None, duration_minutes: int = 60,
                      user_id: str = "default_user") -> Dict[str, Any]:
    """
    Check if user is available during specified time
    
    Args:
        date: Date to check (optional, defaults to today)
        start_time: Start time to check
        end_time: End time to check (optional)
        duration_minutes: Duration if end_time not provided
        user_id: User identifier
        
    Examples:
        "Am I free tomorrow at 2pm?"
        "Check my availability Thursday 9am-11am"
    """
    try:
        # Parse date and time
        if date and start_time:
            dt_str = f"{date} {start_time}"
        elif start_time:
            dt_str = start_time
        else:
            return {"status": "error", "error": "Please provide a time to check"}
        
        start_dt = dateparser.parse(dt_str)
        if not start_dt:
            return {"status": "error", "error": f"Could not parse time: {dt_str}"}
        
        # Calculate end time
        if end_time:
            end_dt = dateparser.parse(end_time)
            if not end_dt:
                end_dt = start_dt + timedelta(minutes=duration_minutes)
        else:
            end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Check availability
        result = calendar_block_mgr.check_availability(user_id, start_dt, end_dt)
        
        if result["available"]:
            return {
                "status": "success",
                "available": True,
                "message": f"You are available from {start_dt.strftime('%I:%M %p')} to {end_dt.strftime('%I:%M %p')}"
            }
        else:
            conflicts_str = "\n".join([
                f"  • {c['title']} ({datetime.fromisoformat(c['start']).strftime('%I:%M %p')} - {datetime.fromisoformat(c['end']).strftime('%I:%M %p')})"
                for c in result["conflicts"]
            ])
            return {
                "status": "success",
                "available": False,
                "message": f"You have conflicts during that time:\n{conflicts_str}",
                "conflicts": result["conflicts"]
            }
        
    except Exception as e:
        logger.error(f"check_availability failed: {e}")
        return {"status": "error", "error": str(e)}


def unblock_calendar(block_id: int, user_id: str = "default_user") -> Dict[str, Any]:
    """
    Remove a calendar block
    
    Args:
        block_id: ID of the block to remove
        user_id: User identifier
    """
    try:
        result = calendar_block_mgr.delete_block(user_id, block_id)
        return result
    except Exception as e:
        logger.error(f"unblock_calendar failed: {e}")
        return {"status": "error", "error": str(e)}


def get_calendar_blocks(start_date: str = None, end_date: str = None,
                       user_id: str = "default_user") -> Dict[str, Any]:
    """
    Get calendar blocks for a date range
    
    Args:
        start_date: Start date (defaults to today)
        end_date: End date (defaults to 7 days from start)
        user_id: User identifier
    """
    try:
        # Parse dates
        if start_date:
            start_dt = dateparser.parse(start_date)
        else:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if end_date:
            end_dt = dateparser.parse(end_date)
        else:
            end_dt = start_dt + timedelta(days=7)
        
        if not start_dt or not end_dt:
            return {"status": "error", "error": "Invalid date format"}
        
        blocks = calendar_block_mgr.get_blocks(user_id, start_dt, end_dt)
        
        return {
            "status": "success",
            "blocks": blocks,
            "count": len(blocks)
        }
        
    except Exception as e:
        logger.error(f"get_calendar_blocks failed: {e}")
        return {"status": "error", "error": str(e)}


# Function definitions for agent registration
CALENDAR_FUNCTIONS = [
    {
        "name": "block_calendar",
        "description": "Block time on user's calendar (lunch, meetings, out-of-office, personal time)",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Block title (e.g., 'Lunch', 'Out of Office', 'Gym')"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in natural language or ISO format"
                },
                "end_time": {
                    "type": "string",
                    "description": "End time (optional if duration provided)"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes (optional if end_time provided)"
                },
                "block_type": {
                    "type": "string",
                    "enum": ["busy", "out-of-office", "lunch", "meeting", "personal"],
                    "description": "Type of block"
                },
                "description": {
                    "type": "string",
                    "description": "Optional description"
                }
            },
            "required": ["title", "start_time"]
        }
    },
    {
        "name": "check_availability",
        "description": "Check if user is available during a specific time",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Date to check (optional, defaults to today)"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time to check"
                },
                "end_time": {
                    "type": "string",
                    "description": "End time to check (optional)"
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Duration in minutes if end_time not provided (default 60)"
                }
            },
            "required": ["start_time"]
        }
    },
    {
        "name": "get_calendar_blocks",
        "description": "Get all calendar blocks for a date range",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date (defaults to today)"
                },
                "end_date": {
                    "type": "string",
                    "description": "End date (defaults to 7 days from start)"
                }
            },
            "required": []
        }
    }
]
