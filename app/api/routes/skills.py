"""
Skills / plugin endpoints.
"""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.skills.registry import get_registry

router = APIRouter(prefix="/skills", tags=["skills"])


class RunRequest(BaseModel):
    args: Dict[str, Any] = {}


@router.get("/")
async def list_skills():
    """List all registered skills."""
    return {"skills": get_registry().list_skills(), "count": len(get_registry().list_skills())}


@router.get("/specs")
async def list_tool_specs():
    """Return full Ollama-compatible tool specs for all skills."""
    return {"tools": get_registry().to_tool_specs()}


@router.post("/{name}/run")
async def run_skill(name: str, request: RunRequest):
    """Run a named skill with the given args dict."""
    skill = get_registry().get(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill '{name}' not found.")
    result = await get_registry().run(name, request.args)
    return {"skill": name, "result": result}
