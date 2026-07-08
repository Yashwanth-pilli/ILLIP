"""
Mock provider for testing and development
Returns hardcoded responses for testing
"""

from typing import Optional, List
from app.core import Message
from app.providers.base_provider import BaseProvider
from app.utils import logger


class MockProvider(BaseProvider):
    """Mock model provider for development and testing"""
    
    def __init__(self):
        super().__init__("mock")
        self.is_available = True
        self.call_count = 0
        
        # Hardcoded responses for testing
        self.responses = [
            "Hello! I'm a mock AI assistant. This response comes from the mock provider.",
            "I can help you with tasks, planning, and more. What would you like to do?",
            "That's an interesting question! In a real scenario, I would use a language model to respond.",
            "The mock provider simulates AI responses for testing purposes.",
            "Each message goes through the system and gets logged in memory.",
        ]
    
    async def health_check(self) -> bool:
        """Mock provider is always healthy"""
        return True
    
    async def generate_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate a mock response
        Returns a response from the predefined list, rotating through them
        """
        self.call_count += 1
        response = self.responses[self.call_count % len(self.responses)]
        
        # Log the call
        logger.info(f"MockProvider.generate_response called (count: {self.call_count})")
        logger.debug(f"Received {len(messages)} messages for processing")
        
        return response

    async def generate_with_tools(
        self,
        messages: List[Message],
        tools: list[dict],
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 8192,
    ) -> tuple[str, list[dict]]:
        """Mock never calls tools — answers directly, empty tool_calls."""
        return await self.generate_response(messages, temperature), []

    async def stream_response(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        model: Optional[str] = None,
        num_ctx: int = 4096,
    ):
        """Yield the mock response word-by-word so callers expecting a streaming
        generator (chat.py) work the same as with a real provider."""
        response = await self.generate_response(messages, temperature)
        for word in response.split(" "):
            yield word + " "
