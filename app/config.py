"""
Configuration management for ILLIP AI
Centralizes all environment variables and path configuration
"""

import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    debug: bool = True
    
    # Model Provider Configuration
    model_provider: str = "ollama"  # mock or ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    # Telegram bridge (optional — set token to enable)
    telegram_bot_token: str = ""
    telegram_allowed_users: str = ""   # comma-separated Telegram user IDs; empty = owner only (first /start)

    # Search
    brave_api_key: str = ""        # https://api.search.brave.com (free 2000/month)
    searxng_url: str = "http://localhost:8888"  # docker run -d -p 8888:8080 searxng/searxng
    # Database
    database_url: str = "sqlite:///./data/illip.db"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./data/logs/illip.log"
    
    # Paths (relative to project root, will be converted to absolute)
    data_dir: str = "./data"
    memory_dir: str = "./data/memory"
    logs_dir: str = "./data/logs"
    tasks_dir: str = "./data/tasks"
    workspaces_dir: str = "./data/workspaces"
    snapshots_dir: str = "./data/snapshots"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Accept release/debug mode strings in addition to booleans."""
        if isinstance(value, str) and value.lower() == "release":
            return False
        return value
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
        protected_namespaces=()
    )
    
    @property
    def project_root(self) -> Path:
        """Get the project root directory"""
        return Path(__file__).parent.parent
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert a relative path to absolute, relative to project root"""
        if Path(relative_path).is_absolute():
            return Path(relative_path)
        return self.project_root / relative_path
    
    def get_data_path(self) -> Path:
        """Get absolute data directory path"""
        return self.get_absolute_path(self.data_dir)
    
    def get_memory_path(self) -> Path:
        """Get absolute memory directory path"""
        return self.get_absolute_path(self.memory_dir)
    
    def get_logs_path(self) -> Path:
        """Get absolute logs directory path"""
        return self.get_absolute_path(self.logs_dir)
    
    def get_tasks_path(self) -> Path:
        """Get absolute tasks directory path"""
        return self.get_absolute_path(self.tasks_dir)
    
    def get_workspaces_path(self) -> Path:
        """Get absolute workspaces directory path"""
        return self.get_absolute_path(self.workspaces_dir)
    
    def get_snapshots_path(self) -> Path:
        """Get absolute snapshots directory path"""
        return self.get_absolute_path(self.snapshots_dir)
    
    def ensure_directories(self):
        """Create all necessary directories if they don't exist"""
        for path in [
            self.get_data_path(),
            self.get_memory_path(),
            self.get_logs_path(),
            self.get_tasks_path(),
            self.get_workspaces_path(),
            self.get_snapshots_path(),
        ]:
            path.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
