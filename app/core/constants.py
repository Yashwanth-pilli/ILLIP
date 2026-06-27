"""
Application-wide constants
"""

# Agent Types
AGENT_PLANNER = "planner"
AGENT_BUILDER = "builder"
AGENT_REVIEWER = "reviewer"
AGENT_TESTER = "tester"
AGENT_MEMORY = "memory"

AGENT_TYPES = [
    AGENT_PLANNER,
    AGENT_BUILDER,
    AGENT_REVIEWER,
    AGENT_TESTER,
    AGENT_MEMORY,
]

# Model Providers
PROVIDER_MOCK = "mock"
PROVIDER_OLLAMA = "ollama"

# Task Status
TASK_PENDING = "pending"
TASK_IN_PROGRESS = "in_progress"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"

TASK_STATUSES = [
    TASK_PENDING,
    TASK_IN_PROGRESS,
    TASK_COMPLETED,
    TASK_FAILED,
]

# Chat Roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"

# Default Values
DEFAULT_MODEL_CONTEXT_LENGTH = 4096
DEFAULT_RESPONSE_TIMEOUT = 30  # seconds
MAX_CHAT_HISTORY = 100  # Max messages to keep in memory
