"""Integration status dashboard — which connectors are live."""

import os
from fastapi import APIRouter
from app.utils import logger

router = APIRouter(prefix="/integrations", tags=["integrations"])

_CONNECTORS = {
    "telegram": {
        "requires": ["TELEGRAM_BOT_TOKEN"],
        "description": "Chat + voice via Telegram bot",
    },
    "discord": {
        "requires": ["DISCORD_BOT_TOKEN"],
        "description": "!illip commands in Discord",
    },
    "slack": {
        "requires": ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN"],
        "description": "@mentions and /illip slash command in Slack",
    },
    "email": {
        "requires": ["EMAIL_ADDRESS", "EMAIL_PASSWORD"],
        "description": "SMTP send + IMAP receive polling",
    },
    "whatsapp": {
        "requires": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"],
        "description": "WhatsApp via Twilio",
    },
    "n8n": {
        "requires": ["N8N_BASE_URL"],
        "description": "n8n workflow automation (trigger + receive)",
    },
    "webhooks": {
        "requires": [],
        "description": "Generic HMAC-signed inbound webhooks — always available",
    },
}


@router.get("/status")
async def integration_status():
    result = {}
    for name, meta in _CONNECTORS.items():
        required = meta["requires"]
        active = all(os.getenv(k, "") for k in required) if required else True
        result[name] = {
            "active": active,
            "requires": required,
            "description": meta["description"],
            "missing": [k for k in required if not os.getenv(k, "")],
        }
    return {"integrations": result}


@router.post("/test/{connector_name}")
async def test_connector(connector_name: str):
    """Send a test ping through a connector."""
    msg = "ILLIP integration test ping"
    if connector_name == "telegram":
        return {"ok": False, "note": "Telegram test: send /status from bot directly"}

    if connector_name == "discord":
        return {"ok": False, "note": "Discord test: type !status in a Discord channel"}

    if connector_name == "email":
        from app.connectors.email_connector import send_email, _EMAIL
        if not _EMAIL:
            return {"ok": False, "error": "EMAIL_ADDRESS not set"}
        ok = await send_email(_EMAIL, "ILLIP Test", msg)
        return {"ok": ok}

    if connector_name == "whatsapp":
        return {"ok": False, "note": "Set TWILIO_WHATSAPP_FROM and use /whatsapp/send endpoint"}

    if connector_name == "n8n":
        from app.connectors.n8n_connector import get_n8n_connector
        workflows = await get_n8n_connector().list_workflows()
        return {"ok": True, "workflows_found": len(workflows)}

    if connector_name == "webhooks":
        from app.connectors.webhook_connector import get_webhook_manager
        hooks = get_webhook_manager().list_webhooks()
        return {"ok": True, "webhooks_registered": len(hooks)}

    return {"ok": False, "error": f"Unknown connector: {connector_name}"}
