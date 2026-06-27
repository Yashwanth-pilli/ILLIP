"""
Custom exception classes for ILLIP AI
"""


class IllipException(Exception):
    """Base exception for all ILLIP AI errors"""
    pass


class ConfigurationError(IllipException):
    """Raised when configuration is invalid"""
    pass


class ProviderError(IllipException):
    """Raised when model provider fails"""
    pass


class ProviderNotAvailableError(ProviderError):
    """Raised when selected provider is not available"""
    pass


class DatabaseError(IllipException):
    """Raised when database operation fails"""
    pass


class MemoryError(IllipException):
    """Raised when memory operation fails"""
    pass


class TaskError(IllipException):
    """Raised when task operation fails"""
    pass


class AgentError(IllipException):
    """Raised when agent operation fails"""
    pass


class ChatError(IllipException):
    """Raised when chat operation fails"""
    pass


class TimeoutError(IllipException):
    """Raised when operation times out"""
    pass
