#!/bin/bash
# test_phase2.sh - Test Phase 2 implementation

echo "?? Testing Phase 2: Core Managers"
echo "=================================="

cd /home/cody/cody-v3/executive-assistant

# Test 1: Import all modules
echo ""
echo "Test 1: Module imports..."
python3 << 'EOF'
try:
    from server.managers.email_manager import EmailManager
    from server.managers.calendar_manager import CalendarManager
    from server.managers.contact_manager import ContactManager
    from server.managers.note_manager import NoteManager
    from server.managers.meeting_orchestrator import MeetingOrchestrator
    from server.managers.document_generator import DocumentGenerator
    from server import assistant_functions
    print("? All modules imported successfully")
except Exception as e:
    print(f"? Import error: {e}")
    exit(1)
EOF

# Test 2: Check function registry
echo ""
echo "Test 2: Function registry..."
python3 << 'EOF'
from server import assistant_functions

functions = assistant_functions.get_function_names()
print(f"? {len(functions)} functions registered:")
for func in sorted(functions):
    print(f"   - {func}")
EOF

# Test 3: Test calendar operations
echo ""
echo "Test 3: Calendar operations..."
python3 << 'EOF'
import asyncio
from server.managers.calendar_manager import CalendarManager

async def test_calendar():
    cal = CalendarManager()
    
    # Add event
    result = cal.add_event(
        title="Test Meeting",
        date="2026-02-15",
        time="14:00",
        duration=60,
        description="Testing calendar functionality"
    )
    
    if result["status"] == "success":
        print("? Calendar: Add event - SUCCESS")
        event_id = result["event"]["id"]
        
        # Get events
        events = cal.get_events(days=30)
        print(f"? Calendar: Get events - Found {events['count']} events")
        
        # Check availability
        avail = cal.check_availability(date="2026-02-15", time="14:00", duration=60)
        if not avail["available"]:
            print("? Calendar: Availability check - Correctly detected conflict")
        
        # Delete event
        cal.delete_event(event_id)
        print("? Calendar: Delete event - SUCCESS")
    else:
        print(f"? Calendar test failed: {result}")

asyncio.run(test_calendar())
EOF

# Test 4: Test contact management
echo ""
echo "Test 4: Contact management..."
python3 << 'EOF'
from server.managers.contact_manager import ContactManager

contact_mgr = ContactManager()

# Add contact
result = contact_mgr.add_contact(
    name="John Doe",
    email="john.doe@example.com",
    phone="555-1234",
    notes="Test contact"
)

if result["status"] == "success":
    print("? Contacts: Add contact - SUCCESS")
    
    # Search contact
    search = contact_mgr.search_contacts("john")
    if search["count"] > 0:
        print(f"? Contacts: Search - Found {search['count']} contacts")
    
    # Get contact
    get_result = contact_mgr.get_contact("john doe")
    if get_result["status"] == "success":
        print("? Contacts: Get contact - SUCCESS")
else:
    print(f"? Contact test failed: {result}")
EOF

# Test 5: Test note management
echo ""
echo "Test 5: Note management..."
python3 << 'EOF'
from server.managers.note_manager import NoteManager

note_mgr = NoteManager()

# Save note
result = note_mgr.save_note(
    title="Test Note",
    content="This is a test note for Phase 2 validation."
)

if result["status"] == "success":
    print("? Notes: Save note - SUCCESS")
    
    # Get notes
    notes = note_mgr.get_notes()
    print(f"? Notes: Get notes - Found {notes['count']} notes")
    
    # Create task
    task = note_mgr.create_task(
        task="Test Phase 2 implementation",
        priority="high"
    )
    if task["status"] == "success":
        print("? Notes: Create task - SUCCESS")
else:
    print(f"? Note test failed: {result}")
EOF

# Test 6: Test document generation
echo ""
echo "Test 6: Document generation..."
python3 << 'EOF'
from server.managers.document_generator import DocumentGenerator

doc_gen = DocumentGenerator()

# Test PowerPoint
ppt_result = doc_gen.create_powerpoint(
    title="Test Presentation",
    slides=[
        {"title": "Introduction", "bullets": ["Point 1", "Point 2", "Point 3"]},
        {"title": "Details", "content": "This is detailed content for the second slide."}
    ]
)

if ppt_result["status"] == "success":
    print(f"? Documents: PowerPoint created - {ppt_result['filename']}")
else:
    print(f"? PowerPoint failed: {ppt_result}")

# Test Memo
memo_result = doc_gen.create_memo(
    to="Team",
    from_="Executive Assistant",
    subject="Phase 2 Testing",
    content="This memo confirms that Phase 2 document generation is working correctly.\n\nAll systems operational."
)

if memo_result["status"] == "success":
    print(f"? Documents: Memo created - {memo_result['filename']}")
else:
    print(f"? Memo failed: {memo_result}")

# Test Drawing
drawing_result = doc_gen.create_drawing(
    description="circle and arrow",
    format="png"
)

if drawing_result["status"] == "success":
    print(f"? Documents: Drawing created - {drawing_result['filename']}")
else:
    print(f"? Drawing failed: {drawing_result}")
EOF

# Test 7: Test meeting orchestration
echo ""
echo "Test 7: Meeting orchestration..."
python3 << 'EOF'
import asyncio
from server.managers.email_manager import EmailManager
from server.managers.calendar_manager import CalendarManager
from server.managers.contact_manager import ContactManager
from server.managers.meeting_orchestrator import MeetingOrchestrator

async def test_meeting():
    email_mgr = EmailManager()
    cal_mgr = CalendarManager()
    contact_mgr = ContactManager()
    
    # Add test contacts
    contact_mgr.add_contact(name="Alice", email="alice@example.com")
    contact_mgr.add_contact(name="Bob", email="bob@example.com")
    
    meeting_mgr = MeetingOrchestrator(email_mgr, cal_mgr, contact_mgr)
    
    # Schedule meeting
    result = meeting_mgr.schedule_meeting(
        attendees=["Alice", "Bob"],
        title="Test Meeting",
        date="2026-02-20",
        time="10:00",
        duration=60
    )
    
    if result["status"] == "success":
        print("? Meeting: Schedule - SUCCESS")
        print(f"   Event ID: {result['meeting']['event_id']}")
        print(f"   Attendees: {len(result['meeting']['attendees'])}")
    else:
        print(f"? Meeting test failed: {result}")

asyncio.run(test_meeting())
EOF

echo ""
echo "=================================="
echo "? Phase 2 Testing Complete!"
echo ""
echo "Generated files are in:"
echo "  ~/Library/Application Support/ExecutiveAssistant/data/"
echo ""