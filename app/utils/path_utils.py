"""
Path utilities for ILLIP AI
Handles all path operations and conversions
"""

from pathlib import Path
from app.config import settings


def get_data_path(subdir: str = "") -> Path:
    """Get data directory path"""
    path = settings.get_data_path()
    if subdir:
        path = path / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_memory_path() -> Path:
    """Get memory directory path"""
    path = settings.get_memory_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_path() -> Path:
    """Get logs directory path"""
    path = settings.get_logs_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_tasks_path() -> Path:
    """Get tasks directory path"""
    path = settings.get_tasks_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspaces_path() -> Path:
    """Get workspaces directory path"""
    path = settings.get_workspaces_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_snapshots_path() -> Path:
    """Get snapshots directory path"""
    path = settings.get_snapshots_path()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_root() -> Path:
    """Get project root directory"""
    return settings.project_root


def ensure_all_directories():
    """Ensure all directories exist"""
    settings.ensure_directories()
