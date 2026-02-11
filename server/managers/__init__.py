"""
Managers module initialization
Location: server/managers/__init__.py
"""
from server.managers.email_manager import EmailManager
from server.managers.calendar_manager import CalendarManager
from server.managers.contact_manager import ContactManager
from server.managers.note_manager import NoteManager
from server.managers.meeting_orchestrator import MeetingOrchestrator
from server.managers.document_generator import DocumentGenerator

__all__ = [
    'EmailManager',
    'CalendarManager',
    'ContactManager',
    'NoteManager',
    'MeetingOrchestrator',
    'DocumentGenerator'
]