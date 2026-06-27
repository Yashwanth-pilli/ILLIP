"""
Task service - manages tasks
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from app.utils import logger, get_current_timestamp, get_tasks_path, write_json_file, read_json_file
from pathlib import Path
import uuid
import json


class TaskService:
    """Service for managing tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.data_dir = get_tasks_path()
        self._load_tasks()
    
    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        agent_type: Optional[str] = None,
        priority: int = 0
    ) -> Dict[str, Any]:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "status": "pending",
            "agent_type": agent_type,
            "priority": priority,
            "created_at": get_current_timestamp().isoformat(),
            "updated_at": get_current_timestamp().isoformat(),
        }
        
        self.tasks[task_id] = task
        self._save_task(task)
        logger.info(f"Task created: {task_id}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a task"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        task.update(updates)
        task["updated_at"] = get_current_timestamp().isoformat()
        
        self._save_task(task)
        logger.info(f"Task updated: {task_id}")
        return task
    
    def list_tasks(
        self,
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if agent_type:
            tasks = [t for t in tasks if t["agent_type"] == agent_type]
        
        # Sort by priority (descending) then by creation date
        tasks.sort(
            key=lambda x: (-x.get("priority", 0), x.get("created_at", "")),
            reverse=False
        )
        
        return tasks[:limit]
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            task_file = self.data_dir / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()
            logger.info(f"Task deleted: {task_id}")
            return True
        return False
    
    def _save_task(self, task: Dict[str, Any]):
        """Save task to file"""
        try:
            task_file = self.data_dir / f"{task['id']}.json"
            write_json_file(task_file, task)
        except Exception as e:
            logger.error(f"Error saving task: {e}")
    
    def _load_tasks(self):
        """Load all tasks from disk"""
        try:
            for file_path in self.data_dir.glob("*.json"):
                task = read_json_file(file_path)
                if "id" in task:
                    self.tasks[task["id"]] = task
            logger.info(f"Loaded {len(self.tasks)} tasks")
        except Exception as e:
            logger.warning(f"Error loading tasks: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics"""
        return {
            "total": len(self.tasks),
            "pending": len([t for t in self.tasks.values() if t["status"] == "pending"]),
            "in_progress": len([t for t in self.tasks.values() if t["status"] == "in_progress"]),
            "completed": len([t for t in self.tasks.values() if t["status"] == "completed"]),
            "failed": len([t for t in self.tasks.values() if t["status"] == "failed"]),
        }


# Global task service
_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """Get or create global task service"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
