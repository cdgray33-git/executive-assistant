#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from server.database.connection import get_db_session
from sqlalchemy import text

with get_db_session() as db:
    result = db.execute(text("""
        SELECT title, date, time, created_at 
        FROM meetings 
        ORDER BY date DESC
        LIMIT 5
    """))
    
    print("\nMeetings in database:")
    print("-" * 60)
    for row in result:
        print(f"{row.title}")
        print(f"  Date: {row.date}")
        print(f"  Time: {row.time}")
        print(f"  Created: {row.created_at}")
        print()
