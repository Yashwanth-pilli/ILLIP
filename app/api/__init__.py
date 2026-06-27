"""
API routes module
"""

from fastapi import APIRouter
from app.api.routes import (
    health,
    chat,
    tasks,
    memory,
    agents,
    system,
    workspace,
    search,
    skills,
    learning,
    projects,
    self_dev,
    voice,
    plugins,
    telegram,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router)
api_router.include_router(chat.router)
api_router.include_router(tasks.router)
api_router.include_router(memory.router)
api_router.include_router(agents.router)
api_router.include_router(system.router)
api_router.include_router(workspace.router)
api_router.include_router(search.router)
api_router.include_router(skills.router)
api_router.include_router(learning.router)
api_router.include_router(projects.router)
api_router.include_router(self_dev.router)
api_router.include_router(voice.router)
api_router.include_router(plugins.router)
api_router.include_router(telegram.router)
