"""
BaseSKill — all skills inherit from this.
"""

from abc import ABC, abstractmethod


class BaseSKill(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema object for the function's arguments

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Run the skill. Must return a plain string result."""
        ...

    def to_tool_spec(self) -> dict:
        """Ollama/OpenAI-compatible tool specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
