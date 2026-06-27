"""
Telegram bot control endpoints.

GET  /api/telegram/status  — is bot running, who is owner
POST /api/telegram/start   — start bot (if token configured)
POST /api/telegram/stop    — stop bot
POST /api/telegram/send    — push a message to owner from ILLIP itself
"""

from fastapi import APIRouter, HTTPException
from app.config import settings
from app.utils import logger

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/status")
async def telegram_status():
    from app.connectors.telegram_bot import _running, _allowed_users, _owner_file
    f = _owner_file()
    owner = None
    if f.exists():
        lines = f.read_text().splitlines()
        owner = lines[0] if lines else None
    return {
        "enabled": bool(settings.telegram_bot_token),
        "running": _running,
        "owner_id": owner,
        "allowed_users": list(_allowed_users),
        "token_set": bool(settings.telegram_bot_token),
        "setup_hint": "Set TELEGRAM_BOT_TOKEN in .env to enable" if not settings.telegram_bot_token else None,
    }


@router.post("/start")
async def start_telegram():
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=400, detail="TELEGRAM_BOT_TOKEN not set in .env")
    from app.connectors.telegram_bot import start_bot, _running
    if _running:
        return {"status": "already_running"}
    import asyncio
    asyncio.create_task(start_bot(settings.telegram_bot_token))
    return {"status": "starting"}


@router.post("/stop")
async def stop_telegram():
    from app.connectors.telegram_bot import stop_bot, _running
    if not _running:
        return {"status": "not_running"}
    await stop_bot()
    return {"status": "stopped"}


@router.post("/send")
async def send_to_owner(body: dict):
    """Push a message from ILLIP to the owner's Telegram (e.g. from autonomy daemon)."""
    from app.connectors.telegram_bot import _app, _running, _owner_file
    if not _running or not _app:
        raise HTTPException(status_code=503, detail="Telegram bot not running")
    f = _owner_file()
    if not f.exists():
        raise HTTPException(status_code=404, detail="No owner registered yet — send /start to the bot first")
    owner_id = int(f.read_text().splitlines()[0])
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    await _app.bot.send_message(chat_id=owner_id, text=text)
    return {"status": "sent", "to": owner_id}
