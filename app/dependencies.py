"""
Dependency injection for FastAPI
"""

from app.services import (
    get_chat_service,
    get_task_service,
    get_memory_service,
    get_log_service,
    get_model_service,
    get_agent_service,
)


def get_dependencies():
    """Get all service dependencies"""
    return {
        "chat_service": get_chat_service(),
        "task_service": get_task_service(),
        "memory_service": get_memory_service(),
        "log_service": get_log_service(),
        "model_service": get_model_service(),
        "agent_service": get_agent_service(),
    }
