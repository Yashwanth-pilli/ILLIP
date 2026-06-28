"""
WhatsApp connector via Twilio API.

Config (env vars):
  TWILIO_ACCOUNT_SID    — Twilio account SID
  TWILIO_AUTH_TOKEN     — Twilio auth token
  TWILIO_WHATSAPP_FROM  — e.g. "whatsapp:+14155238886"

Inbound: Twilio posts to POST /whatsapp/receive
Outbound: send_whatsapp(to, message)
"""

import hashlib
import hmac
import os
import httpx
from app.utils import logger

_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "")


def is_configured() -> bool:
    return bool(_SID and _TOKEN and _FROM)


def verify_twilio_signature(url: str, params: dict, signature: str) -> bool:
    """Verify Twilio webhook signature."""
    if not _TOKEN:
        return False
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    s = url + sorted_params
    expected = hmac.new(_TOKEN.encode(), s.encode(), hashlib.sha1).digest()
    import base64
    expected_b64 = base64.b64encode(expected).decode()
    return hmac.compare_digest(expected_b64, signature)


from app.connectors.base_connector import BaseConnector


class WhatsAppConnector(BaseConnector):
    name = "whatsapp"
    description = "WhatsApp via Twilio — inbound webhook + outbound send"
    required_env_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"]

    async def start(self) -> bool:
        return is_configured()

    async def stop(self) -> None:
        pass  # stateless HTTP connector, nothing to stop

    def is_active(self) -> bool:
        return is_configured()


async def send_whatsapp(to: str, message: str) -> bool:
    """Send WhatsApp message via Twilio REST API."""
    if not is_configured():
        logger.warning("WhatsApp: Twilio credentials not configured")
        return False
    # Ensure whatsapp: prefix
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"
    url = f"https://api.twilio.com/2010-04-01/Accounts/{_SID}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                url,
                data={"From": _FROM, "To": to, "Body": message[:1600]},
                auth=(_SID, _TOKEN),
            )
            if r.status_code in (200, 201):
                logger.info(f"WhatsApp sent to {to}")
                return True
            logger.error(f"WhatsApp send failed: {r.status_code} {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False
