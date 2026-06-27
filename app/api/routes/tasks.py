"""
Task endpoints
"""

from fastapi import APIRouter, HTTPException
from app.core import TaskCreate, TaskUpdate, Task
from app.services import get_task_service
from app.utils import logger

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=Task)
async def create_task(request: TaskCreate):
    """Create a new task"""
    try:
        task_service = get_task_service()
        task = task_service.create_task(
            title=request.title,
            description=request.description,
            agent_type=request.agent_type,
            priority=request.priority,
        )
        return task
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_tasks(status: str = None, agent_type: str = None, limit: int = 100):
    """List tasks with optional filtering"""
    try:
        task_service = get_task_service()
        tasks = task_service.list_tasks(
            status=status,
            agent_type=agent_type,
            limit=limit
        )
        return {
            "tasks": tasks,
            "count": len(tasks),
        }
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a specific task"""
    try:
        task_service = get_task_service()
        task = task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{task_id}", response_model=Task)
async def update_task(task_id: str, request: TaskUpdate):
    """Update a task"""
    try:
        task_service = get_task_service()
        updates = request.dict(exclude_unset=True)
        task = task_service.update_task(task_id, updates)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    try:
        task_service = get_task_service()
        success = task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_task_stats():
    """Get task statistics"""
    try:
        task_service = get_task_service()
        stats = task_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting task stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
