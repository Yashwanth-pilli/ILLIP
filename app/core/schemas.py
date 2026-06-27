"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# Chat Schemas
class ChatMessage(BaseModel):
    """A single chat message"""
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request to send a chat message"""
    message: str
    include_memory: bool = True
    model: Optional[str] = None
    force_search: bool = False
    force_tools: bool = False  # bypass simple-path tool-skip (Telegram, agent callers)
    project_id: str = "default"


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    user_message: str
    assistant_message: str
    memory_context: Optional[str] = None
    timestamp: datetime


# Task Schemas
class TaskCreate(BaseModel):
    """Request to create a task"""
    title: str
    description: Optional[str] = None
    agent_type: Optional[str] = None  # planner, builder, reviewer, tester
    priority: int = 0


class TaskUpdate(BaseModel):
    """Request to update a task"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None


class Task(BaseModel):
    """Full task object"""
    id: str
    title: str
    description: Optional[str]
    status: str  # pending, in_progress, completed, failed
    agent_type: Optional[str]
    priority: int
    created_at: datetime
    updated_at: datetime


# Memory Schemas
class MemoryEntry(BaseModel):
    """A memory entry"""
    id: str
    key: str
    value: str
    category: str  # chat, task, log, etc.
    created_at: datetime


class MemoryQuery(BaseModel):
    """Query for memory search"""
    query: str
    category: Optional[str] = None
    limit: int = 10


# Agent Schemas
class AgentStatus(BaseModel):
    """Status of an agent"""
    agent_type: str
    name: str
    is_available: bool
    last_activity: Optional[datetime]
    task_count: int


class AgentListResponse(BaseModel):
    """List of available agents"""
    agents: List[AgentStatus]
    total_available: int


# System Schemas
class SystemStatus(BaseModel):
    """System status information"""
    model_config = {
        "protected_namespaces": ()
    }
    
    status: str  # "running", "error"
    model_provider: str
    active_model: str = "unknown"
    database_connected: bool
    memory_count: int
    task_count: int
    agent_count: int
    uptime_seconds: float
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str  # "ok", "degraded", "error"
    message: str
    timestamp: datetime


# Workspace Schemas
class WorkspaceUploadResponse(BaseModel):
    """Response after uploading a workspace"""
    filename: str
    saved_path: str
    uploaded_at: datetime
    status: str


class WorkspaceChatRequest(BaseModel):
    """Request for workspace chat"""
    question: str = Field(
        ...,
        min_length=1,
        description="User question about the workspace"
    )