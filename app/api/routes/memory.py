"""
Memory endpoints
"""

from fastapi import APIRouter, HTTPException
from app.services import get_memory_service
from app.utils import logger

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/store")
async def store_memory(key: str, value: str, category: str = "general"):
    """Store a memory entry"""
    try:
        memory_service = get_memory_service()
        entry = memory_service.store(key, value, category)
        return entry
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve/{key}")
async def retrieve_memory(key: str):
    """Retrieve a memory entry by key"""
    try:
        memory_service = get_memory_service()
        value = memory_service.retrieve(key)
        if value is None:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        return {"key": key, "value": value}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_memory(query: str, category: str = None, limit: int = 10):
    """Search memory entries"""
    try:
        memory_service = get_memory_service()
        results = memory_service.search(query, category, limit)
        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_memory(category: str = None):
    """Get all memory entries"""
    try:
        memory_service = get_memory_service()
        entries = memory_service.get_all(category)
        return {
            "entries": entries,
            "count": len(entries),
        }
    except Exception as e:
        logger.error(f"Error getting all memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
async def delete_memory(entry_id: str):
    """Delete a memory entry"""
    try:
        memory_service = get_memory_service()
        success = memory_service.delete(entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_memory_stats():
    """Get memory statistics"""
    try:
        memory_service = get_memory_service()
        stats = memory_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
