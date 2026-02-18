"""
Calendar Block Manager - User availability management
Allows users to block time on their calendar
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from server.database.connection import get_db_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class CalendarBlockManager:
    def __init__(self):
        pass
    
    def block_calendar(self, user_id: str, title: str, start_time: datetime, 
                      end_time: datetime, block_type: str = "busy", 
                      description: str = None) -> Dict[str, Any]:
        """
        Block time on user's calendar
        
        Args:
            user_id: User identifier
            title: Block title (e.g., "Lunch", "Out of Office")
            start_time: Start datetime
            end_time: End datetime
            block_type: busy, out-of-office, lunch, meeting, personal
            description: Optional description
            
        Returns:
            {"status": "success", "block_id": 123}
        """
        try:
            with get_db_session() as db:
                result = db.execute(text("""
                    INSERT INTO calendar_blocks 
                    (user_id, title, start_time, end_time, block_type, description)
                    VALUES (:uid, :t, :st, :et, :bt, :desc)
                    RETURNING id
                """), {
                    "uid": user_id,
                    "t": title,
                    "st": start_time,
                    "et": end_time,
                    "bt": block_type,
                    "desc": description
                })
                db.commit()
                block_id = result.fetchone()[0]
                
            logger.info(f"Calendar blocked: {title} from {start_time} to {end_time}")
            return {
                "status": "success",
                "block_id": block_id,
                "message": f"Blocked: {title} from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')}"
            }
            
        except Exception as e:
            logger.error(f"Failed to block calendar: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_availability(self, user_id: str, start_time: datetime, 
                          end_time: datetime) -> Dict[str, Any]:
        """
        Check if user is available during specified time
        
        Returns:
            {
                "available": true/false,
                "conflicts": [list of conflicting blocks/meetings]
            }
        """
        try:
            conflicts = []
            
            with get_db_session() as db:
                # Check calendar blocks
                blocks = db.execute(text("""
                    SELECT title, start_time, end_time, block_type
                    FROM calendar_blocks
                    WHERE user_id = :uid
                    AND (
                        (start_time <= :st AND end_time > :st)
                        OR (start_time < :et AND end_time >= :et)
                        OR (start_time >= :st AND end_time <= :et)
                    )
                """), {"uid": user_id, "st": start_time, "et": end_time}).fetchall()
                
                for block in blocks:
                    conflicts.append({
                        "type": "block",
                        "title": block[0],
                        "start": block[1].isoformat(),
                        "end": block[2].isoformat(),
                        "reason": block[3]
                    })
                
                # Check scheduled meetings
                meetings = db.execute(text("""
                    SELECT title, date, time, duration
                    FROM meetings
                    WHERE user_id = :uid
                    AND status = 'scheduled'
                    AND date = :d
                """), {"uid": user_id, "d": start_time.date()}).fetchall()
                
                for mtg in meetings:
                    mtg_start = datetime.combine(mtg[1], mtg[2])
                    mtg_end = mtg_start + timedelta(minutes=mtg[3])
                    
                    # Check overlap
                    if (mtg_start <= start_time < mtg_end) or \
                       (mtg_start < end_time <= mtg_end) or \
                       (start_time <= mtg_start and end_time >= mtg_end):
                        conflicts.append({
                            "type": "meeting",
                            "title": mtg[0],
                            "start": mtg_start.isoformat(),
                            "end": mtg_end.isoformat()
                        })
            
            return {
                "available": len(conflicts) == 0,
                "conflicts": conflicts
            }
            
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            return {"available": True, "conflicts": [], "error": str(e)}
    
    def get_blocks(self, user_id: str, start_date: datetime, 
                   end_date: datetime) -> List[Dict]:
        """Get all calendar blocks for user in date range"""
        try:
            with get_db_session() as db:
                blocks = db.execute(text("""
                    SELECT id, title, start_time, end_time, block_type, description
                    FROM calendar_blocks
                    WHERE user_id = :uid
                    AND start_time >= :sd
                    AND end_time <= :ed
                    ORDER BY start_time
                """), {"uid": user_id, "sd": start_date, "ed": end_date}).fetchall()
                
                return [{
                    "id": b[0],
                    "title": b[1],
                    "start": b[2].isoformat(),
                    "end": b[3].isoformat(),
                    "type": b[4],
                    "description": b[5]
                } for b in blocks]
                
        except Exception as e:
            logger.error(f"Get blocks failed: {e}")
            return []
    
    def delete_block(self, user_id: str, block_id: int) -> Dict[str, Any]:
        """Delete a calendar block"""
        try:
            with get_db_session() as db:
                db.execute(text("""
                    DELETE FROM calendar_blocks
                    WHERE id = :bid AND user_id = :uid
                """), {"bid": block_id, "uid": user_id})
                db.commit()
            
            return {"status": "success", "message": "Block removed"}
            
        except Exception as e:
            logger.error(f"Delete block failed: {e}")
            return {"status": "error", "error": str(e)}
