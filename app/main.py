"""
Main FastAPI application
"""

import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.utils import logger, ensure_all_directories
from app.api import api_router
from app.db import init_database
import app.skills   # noqa: F401 — registers built-in skills on import
import app.plugins  # noqa: F401 — loads user-defined plugins from data/plugins/

# Ensure all directories exist
ensure_all_directories()

# Initialize database
try:
    init_database()
except Exception as e:
    logger.warning(f"Database initialization failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup and shutdown events"""
    import asyncio
    from app.hardware.speed_optimizer import warmup_on_startup
    logger.info("ILLIP AI starting up...")
    logger.info(f"Configuration: {settings.model_provider}")
    # Start GPU safety monitor
    from app.hardware.safety_monitor import start_monitor
    start_monitor()
    # Pre-warm default model in background so first user message is fast
    asyncio.create_task(warmup_on_startup(settings.ollama_model, settings.ollama_base_url))
    # Start Telegram bot if token is configured
    if settings.telegram_bot_token:
        from app.connectors.telegram_bot import start_bot
        asyncio.create_task(start_bot(settings.telegram_bot_token))
        logger.info("Telegram bot queued for startup")
    yield
    logger.info("ILLIP AI shutting down...")
    # Stop Telegram bot on shutdown
    if settings.telegram_bot_token:
        from app.connectors.telegram_bot import stop_bot
        await stop_bot()


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="ILLIP AI",
    description="Local-first portable AI assistant system",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS is open for the local static frontend. Tighten this before exposing the
# API outside your own machine.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Serve frontend static files
frontend_dir = settings.project_root / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info",
    )
