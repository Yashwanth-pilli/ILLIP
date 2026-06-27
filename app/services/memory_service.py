"""
Memory service — project-scoped key-value memory backed by JSON files.
Each project stores memory in data/projects/{project_id}/memory.json
"""

from typing import Optional, List, Dict, Any
from app.utils import logger
from app.services.project_service import (
    DEFAULT_PROJECT,
    memory_store,
    memory_get_all,
    memory_delete,
    memory_stats,
    ensure_default_project,
)


class MemoryService:
    """Project-scoped memory. Pass project_id on each call."""

    def __init__(self):
        ensure_default_project()

    def store(
        self,
        key: str,
        value: str,
        category: str = "general",
        project_id: str = DEFAULT_PROJECT,
    ) -> Dict[str, Any]:
        entry = memory_store(project_id, key, value, category)
        logger.info(f"Memory stored: {key} (project={project_id})")
        return entry

    def retrieve(self, key: str, project_id: str = DEFAULT_PROJECT) -> Optional[str]:
        for entry in memory_get_all(project_id):
            if entry["key"] == key:
                return entry["value"]
        return None

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        project_id: str = DEFAULT_PROJECT,
    ) -> List[Dict[str, Any]]:
        entries = memory_get_all(project_id, category)
        q = query.lower()
        matches = [
            e for e in entries
            if q in e.get("value", "").lower() or q in e.get("key", "").lower()
        ]
        return matches[:limit]

    def get_all(
        self,
        category: Optional[str] = None,
        project_id: str = DEFAULT_PROJECT,
    ) -> List[Dict[str, Any]]:
        return memory_get_all(project_id, category)

    def delete(self, entry_id: str, project_id: str = DEFAULT_PROJECT) -> bool:
        deleted = memory_delete(project_id, entry_id)
        if deleted:
            logger.info(f"Memory deleted: {entry_id} (project={project_id})")
        return deleted

    def clear(self, category: Optional[str] = None, project_id: str = DEFAULT_PROJECT):
        entries = memory_get_all(project_id, category)
        for e in entries:
            memory_delete(project_id, e["id"])
        logger.info(f"Memory cleared (project={project_id}, category={category or 'all'})")

    def get_stats(self, project_id: str = DEFAULT_PROJECT) -> Dict[str, Any]:
        return memory_stats(project_id)


_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
