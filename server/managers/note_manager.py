"""
Note Manager - Notes and task management
Location: server/managers/note_manager.py
"""
import logging
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("note_manager")

# Data paths
DATA_DIR = Path(os.path.expanduser("~/Library/Application Support/ExecutiveAssistant/data"))
NOTES_DIR = DATA_DIR / "notes"
TASKS_FILE = DATA_DIR / "notes" / "tasks.json"


class NoteManager:
    """Manages notes and tasks"""
    
    def __init__(self):
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        self.tasks = self._load_tasks()
        
    def _load_tasks(self) -> List[Dict]:
        """Load tasks from storage"""
        try:
            if TASKS_FILE.exists():
                with open(TASKS_FILE, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            return []
    
    def _save_tasks(self):
        """Save tasks to storage"""
        try:
            with open(TASKS_FILE, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tasks: {e}")
    
    def _sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        safe = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in title)
        return safe.strip().replace(' ', '_')[:100]  # Limit length
    
    def save_note(self, content: str, title: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Save a note
        
        Args:
            content: Note content
            title: Optional title (generated if not provided)
            
        Returns:
            Saved note info
        """
        try:
            if not title:
                # Generate title from timestamp
                title = f"note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            filename = self._sanitize_filename(title) + ".txt"
            filepath = NOTES_DIR / filename
            
            # Add metadata header
            note_content = f"""# {title}
Created: {datetime.now().isoformat()}

{content}
"""
            
            with open(filepath, 'w') as f:
                f.write(note_content)
            
            logger.info(f"Saved note: {title}")
            
            return {
                "status": "success",
                "title": title,
                "filename": filename,
                "path": str(filepath),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error saving note: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_notes(self, query: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Retrieve notes
        
        Args:
            query: Optional search query
            
        Returns:
            List of notes
        """
        try:
            notes = []
            
            for filepath in NOTES_DIR.glob("*.txt"):
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    
                    # Skip if query provided and doesn't match
                    if query:
                        query_lower = query.lower()
                        if (query_lower not in filepath.stem.lower() and 
                            query_lower not in content.lower()):
                            continue
                    
                    # Extract title from first line if available
                    lines = content.split('\n')
                    title = lines[0].replace('# ', '') if lines else filepath.stem
                    
                    notes.append({
                        "title": title,
                        "filename": filepath.name,
                        "preview": content[:200] + "..." if len(content) > 200 else content,
                        "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error reading note {filepath}: {e}")
                    continue
            
            # Sort by modification time (newest first)
            notes.sort(key=lambda n: n["modified"], reverse=True)
            
            return {
                "status": "success",
                "notes": notes,
                "count": len(notes)
            }
            
        except Exception as e:
            logger.error(f"Error getting notes: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_note_content(self, title: str) -> Dict[str, Any]:
        """Get full content of a specific note"""
        try:
            filename = self._sanitize_filename(title) + ".txt"
            filepath = NOTES_DIR / filename
            
            if not filepath.exists():
                return {
                    "status": "error",
                    "error": f"Note '{title}' not found"
                }
            
            with open(filepath, 'r') as f:
                content = f.read()
            
            return {
                "status": "success",
                "title": title,
                "content": content
            }
            
        except Exception as e:
            logger.error(f"Error getting note content: {e}")
            return {"status": "error", "error": str(e)}
    
    def create_task(self, task: str, due_date: Optional[str] = None, 
                    priority: str = "medium", **kwargs) -> Dict[str, Any]:
        """
        Create a task/reminder
        
        Args:
            task: Task description
            due_date: Optional due date (YYYY-MM-DD)
            priority: Priority level (high/medium/low)
            
        Returns:
            Created task dict
        """
        try:
            import uuid
            
            task_obj = {
                "id": str(uuid.uuid4()),
                "task": task,
                "due_date": due_date,
                "priority": priority.lower(),
                "completed": False,
                "created_at": datetime.now().isoformat(),
                "completed_at": None
            }
            
            self.tasks.append(task_obj)
            self._save_tasks()
            
            logger.info(f"Created task: {task}")
            
            return {
                "status": "success",
                "task": task_obj
            }
            
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_tasks(self, completed: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Get tasks
        
        Args:
            completed: If True, return completed tasks; if False, return active
            
        Returns:
            List of tasks
        """
        try:
            filtered = [t for t in self.tasks if t["completed"] == completed]
            
            # Sort by priority and due date
            priority_order = {"high": 0, "medium": 1, "low": 2}
            filtered.sort(key=lambda t: (
                priority_order.get(t["priority"], 1),
                t["due_date"] or "9999-12-31"
            ))
            
            return {
                "status": "success",
                "tasks": filtered,
                "count": len(filtered)
            }
            
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return {"status": "error", "error": str(e)}
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed"""
        try:
            task = next((t for t in self.tasks if t["id"] == task_id), None)
            
            if not task:
                return {"status": "error", "error": f"Task {task_id} not found"}
            
            task["completed"] = True
            task["completed_at"] = datetime.now().isoformat()
            self._save_tasks()
            
            return {
                "status": "success",
                "message": f"Task completed: {task['task']}"
            }
            
        except Exception as e:
            logger.error(f"Error completing task: {e}")
            return {"status": "error", "error": str(e)}
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        try:
            task = next((t for t in self.tasks if t["id"] == task_id), None)
            
            if not task:
                return {"status": "error", "error": f"Task {task_id} not found"}
            
            self.tasks.remove(task)
            self._save_tasks()
            
            return {
                "status": "success",
                "message": f"Task deleted: {task['task']}"
            }
            
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return {"status": "error", "error": str(e)}