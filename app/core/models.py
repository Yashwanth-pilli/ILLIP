"""
Core data models (not database models, but domain objects)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Message:
    """Represents a chat message"""
    role: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }


@dataclass
class TaskItem:
    """Represents a task"""
    id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed, failed
    agent_type: Optional[str]
    priority: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "agent_type": self.agent_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class MemoryRecord:
    """Represents a memory entry"""
    id: str
    key: str
    value: str
    category: str
    created_at: datetime
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentCapability:
    """Represents an agent's capability"""
    agent_type: str
    is_available: bool
    last_activity: Optional[datetime]
    task_count: int
    
    def to_dict(self) -> Dict:
        return {
            "agent_type": self.agent_type,
            "is_available": self.is_available,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "task_count": self.task_count,
        }
