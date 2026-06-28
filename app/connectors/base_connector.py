"""
BaseConnector — protocol every connector must follow.

Drop a .py file in data/connectors/ that subclasses this and ILLIP
auto-discovers and starts it. Zero code changes required.
"""

import os
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    # Override in subclass
    name: str = "unnamed"
    description: str = ""
    required_env_vars: list[str] = []   # connector only starts if ALL are set
    optional_env_vars: list[str] = []   # shown in status but not blocking

    @abstractmethod
    async def start(self) -> bool:
        """Start the connector. Return True on success."""

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stop the connector."""

    @abstractmethod
    def is_active(self) -> bool:
        """Return True if currently running."""

    def is_configured(self) -> bool:
        return all(os.getenv(v, "").strip() for v in self.required_env_vars)

    def missing_vars(self) -> list[str]:
        return [v for v in self.required_env_vars if not os.getenv(v, "").strip()]

    def to_status(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "active": self.is_active(),
            "configured": self.is_configured(),
            "required_env_vars": self.required_env_vars,
            "optional_env_vars": self.optional_env_vars,
            "missing_vars": self.missing_vars(),
        }
