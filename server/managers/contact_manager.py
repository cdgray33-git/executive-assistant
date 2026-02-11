"""
Contact Manager - Contact information management
Location: server/managers/contact_manager.py
"""
import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("contact_manager")

# Data paths
DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
CONTACTS_FILE = DATA_DIR / "contacts" / "contacts.json"


class ContactManager:
    """Manages contact information with learning capabilities"""
    
    def __init__(self):
        self.contacts = self._load_contacts()
        
    def _load_contacts(self) -> List[Dict]:
        """Load contacts from local storage"""
        try:
            if CONTACTS_FILE.exists():
                with open(CONTACTS_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading contacts: {e}")
            return []
    
    def _save_contacts(self):
        """Save contacts to local storage"""
        try:
            CONTACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONTACTS_FILE, 'w') as f:
                json.dump(self.contacts, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving contacts: {e}")
    
    def _generate_contact_id(self) -> str:
        """Generate unique contact ID"""
        import uuid
        return str(uuid.uuid4())
    
    def add_contact(self, name: str, email: Optional[str] = None, 
                    phone: Optional[str] = None, notes: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Add a new contact
        
        Args:
            name: Contact name
            email: Email address (can be list or string)
            phone: Phone number (can be list or string)
            notes: Optional notes
            
        Returns:
            Created contact dict
        """
        try:
            # Check for duplicate
            existing = self.search_contacts(query=name)
            if existing.get("contacts"):
                for contact in existing["contacts"]:
                    if contact["name"].lower() == name.lower():
                        return {
                            "status": "error",
                            "error": f"Contact '{name}' already exists",
                            "existing_contact": contact
                        }
            
            # Handle multiple emails/phones
            emails = [email] if isinstance(email, str) else (email or [])
            phones = [phone] if isinstance(phone, str) else (phone or [])
            
            contact = {
                "id": self._generate_contact_id(),
                "name": name,
                "emails": [e for e in emails if e],
                "phones": [p for p in phones if p],
                "notes": notes,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "interaction_count": 0,
                "last_interaction": None,
                "tags": []
            }
            
            self.contacts.append(contact)
            self._save_contacts()
            
            logger.info(f"Added contact: {name}")
            
            return {
                "status": "success",
                "contact": contact
            }
            
        except Exception as e:
            logger.error(f"Error adding contact: {e}")
            return {"status": "error", "error": str(e)}
    
    def search_contacts(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search contacts by name, email, or phone
        
        Args:
            query: Search term
            
        Returns:
            Matching contacts
        """
        try:
            query = query.lower()
            matches = []
            
            for contact in self.contacts:
                # Search in name
                if query in contact["name"].lower():
                    matches.append(contact)
                    continue
                
                # Search in emails
                if any(query in email.lower() for email in contact.get("emails", [])):
                    matches.append(contact)
                    continue
                
                # Search in phones
                if any(query in phone for phone in contact.get("phones", [])):
                    matches.append(contact)
                    continue
                
                # Search in notes
                if contact.get("notes") and query in contact["notes"].lower():
                    matches.append(contact)
            
            return {
                "status": "success",
                "contacts": matches,
                "count": len(matches),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Error searching contacts: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_contact(self, identifier: str, **kwargs) -> Dict[str, Any]:
        """
        Get contact by name, email, or ID
        
        Args:
            identifier: Name, email, or ID
            
        Returns:
            Contact dict
        """
        try:
            identifier = identifier.lower()
            
            # Try exact name match first
            for contact in self.contacts:
                if contact["name"].lower() == identifier:
                    return {
                        "status": "success",
                        "contact": contact
                    }
            
            # Try email match
            for contact in self.contacts:
                if any(identifier in email.lower() for email in contact.get("emails", [])):
                    return {
                        "status": "success",
                        "contact": contact
                    }
            
            # Try ID match
            for contact in self.contacts:
                if contact["id"] == identifier:
                    return {
                        "status": "success",
                        "contact": contact
                    }
            
            return {
                "status": "error",
                "error": f"Contact '{identifier}' not found"
            }
            
        except Exception as e:
            logger.error(f"Error getting contact: {e}")
            return {"status": "error", "error": str(e)}
    
    def update_contact(self, identifier: str, updates: Dict, **kwargs) -> Dict[str, Any]:
        """
        Update contact information
        
        Args:
            identifier: Name, email, or ID
            updates: Dict of fields to update
            
        Returns:
            Updated contact
        """
        try:
            # Find contact
            result = self.get_contact(identifier)
            if result["status"] != "success":
                return result
            
            contact = result["contact"]
            
            # Update fields
            for key, value in updates.items():
                if key in ["emails", "phones"]:
                    # Handle adding to lists
                    if isinstance(value, list):
                        contact[key] = value
                    else:
                        if value not in contact[key]:
                            contact[key].append(value)
                elif key != "id":  # Don't allow ID changes
                    contact[key] = value
            
            contact["updated_at"] = datetime.now().isoformat()
            self._save_contacts()
            
            return {
                "status": "success",
                "contact": contact
            }
            
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return {"status": "error", "error": str(e)}
    
    def record_interaction(self, identifier: str):
        """Record an interaction with a contact (for learning)"""
        try:
            result = self.get_contact(identifier)
            if result["status"] == "success":
                contact = result["contact"]
                contact["interaction_count"] = contact.get("interaction_count", 0) + 1
                contact["last_interaction"] = datetime.now().isoformat()
                self._save_contacts()
        except Exception as e:
            logger.error(f"Error recording interaction: {e}")
    
    def get_contact_by_email(self, email: str) -> Optional[Dict]:
        """Get contact by email address"""
        email = email.lower()
        for contact in self.contacts:
            if any(email in e.lower() for e in contact.get("emails", [])):
                return contact
        return None
    
    def get_all_contacts(self) -> List[Dict]:
        """Get all contacts"""
        return self.contacts