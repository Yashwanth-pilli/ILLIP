"""
Qdrant vector memory — semantic long-term memory for ILLIP.
Gracefully degrades to no-op when Qdrant is not running.

To install Qdrant locally:
  docker run -d -p 6333:6333 --name qdrant qdrant/qdrant
Then set QDRANT_URL=http://localhost:6333 in .env

Embedding: uses Ollama's nomic-embed-text model (free, local).
Install: ollama pull nomic-embed-text
"""

import asyncio
import hashlib
from typing import Optional
import aiohttp
from app.utils import logger

_QDRANT_URL   = "http://localhost:6333"
_OLLAMA_URL   = "http://localhost:11434"
_EMBED_MODEL  = "nomic-embed-text"
_VECTOR_SIZE  = 768  # nomic-embed-text output size

_available: Optional[bool] = None  # cached availability
_DEFAULT_PROJECT = "default"


def _collection(project_id: str = _DEFAULT_PROJECT) -> str:
    from app.services.project_service import qdrant_collection
    return qdrant_collection(project_id)


async def _check_qdrant() -> bool:
    global _available
    if _available is not None:
        return _available
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{_QDRANT_URL}/healthz", timeout=aiohttp.ClientTimeout(total=2)) as r:
                _available = r.status == 200
    except Exception:
        _available = False
    if not _available:
        logger.debug("Qdrant not available — vector memory disabled")
    return _available


async def _embed(text: str) -> Optional[list[float]]:
    """Get embedding from Ollama nomic-embed-text."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{_OLLAMA_URL}/api/embed",
                json={"model": _EMBED_MODEL, "input": text},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    embeddings = data.get("embeddings", [])
                    return embeddings[0] if embeddings else None
    except Exception as e:
        logger.debug(f"Embedding failed: {e}")
    return None


async def _ensure_collection(col: str) -> bool:
    """Create Qdrant collection if it doesn't exist."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{_QDRANT_URL}/collections/{col}") as r:
                if r.status == 200:
                    return True
            async with s.put(
                f"{_QDRANT_URL}/collections/{col}",
                json={"vectors": {"size": _VECTOR_SIZE, "distance": "Cosine"}},
            ) as r:
                return r.status in (200, 201)
    except Exception:
        return False


async def store_memory(
    text: str,
    metadata: dict = None,
    project_id: str = _DEFAULT_PROJECT,
) -> bool:
    """Store text as a vector in the project's Qdrant collection."""
    if not await _check_qdrant():
        return False
    embedding = await _embed(text)
    if not embedding:
        return False
    col = _collection(project_id)
    if not await _ensure_collection(col):
        return False

    point_id = int(hashlib.md5(f"{project_id}:{text}".encode()).hexdigest()[:8], 16)
    payload = {"text": text, "project_id": project_id, **(metadata or {})}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.put(
                f"{_QDRANT_URL}/collections/{col}/points",
                json={"points": [{"id": point_id, "vector": embedding, "payload": payload}]},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                return r.status in (200, 201)
    except Exception as e:
        logger.debug(f"Qdrant store failed: {e}")
        return False


async def retrieve_memory(
    query: str,
    top_k: int = 3,
    score_threshold: float = 0.65,
    project_id: str = _DEFAULT_PROJECT,
) -> list[dict]:
    """Semantic search within a project's memory collection."""
    if not await _check_qdrant():
        return []
    embedding = await _embed(query)
    if not embedding:
        return []
    col = _collection(project_id)
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(
                f"{_QDRANT_URL}/collections/{col}/points/search",
                json={
                    "vector": embedding,
                    "limit": top_k,
                    "score_threshold": score_threshold,
                    "with_payload": True,
                },
                timeout=aiohttp.ClientTimeout(total=5),
            ) as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return [
                    {"text": h["payload"].get("text", ""), "score": h["score"],
                     **{k: v for k, v in h["payload"].items() if k != "text"}}
                    for h in data.get("result", [])
                ]
    except Exception as e:
        logger.debug(f"Qdrant search failed: {e}")
        return []


def format_memories_for_prompt(memories: list[dict]) -> str:
    """Format retrieved memories as LLM context block."""
    if not memories:
        return ""
    lines = ["**Relevant memories:**"]
    for m in memories:
        lines.append(f"- {m['text']}")
    return "\n".join(lines)
