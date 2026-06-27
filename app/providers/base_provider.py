"""
Base provider interface for LLM models
All concrete providers must implement this interface
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.core import Message
from app.utils import logger


class BaseProvider(ABC):
    """Abstract base class for model providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_available = False
        self.last_error: Optional[str] = None
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is available
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a response from the model
        
        Args:
            messages: List of Message objects containing conversation history
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated response text
        """
        pass
    
    async def validate_health(self) -> None:
        """Validate and update health status"""
        try:
            self.is_available = await self.health_check()
            if self.is_available:
                self.last_error = None
            else:
                self.last_error = "Health check failed"
        except Exception as e:
            self.is_available = False
            self.last_error = str(e)
            logger.warning(f"Provider {self.name} health check failed: {e}")
    
    async def safe_generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Safely generate a response with error handling
        
        Returns:
            Generated response or error message
        """
        try:
            await self.validate_health()
            
            if not self.is_available:
                error_msg = self.last_error or "Provider not available"
                logger.error(f"Provider {self.name} not available: {error_msg}")
                return f"Error: {error_msg}"
            
            response = await self.generate_response(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(f"Provider {self.name} error: {error_msg}")
            return error_msg
