"""WhatsApp connector endpoints (Twilio)."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from app.connectors.whatsapp_connector import send_whatsapp, verify_twilio_signature, is_configured
from app.utils import logger

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


class SendRequest(BaseModel):
    to: str
    message: str


@router.post("/receive")
async def receive_whatsapp(request: Request):
    """Twilio inbound webhook."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp not configured")

    form = await request.form()
    params = dict(form)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    if signature and not verify_twilio_signature(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    body = params.get("Body", "").strip()
    sender = params.get("From", "")

    if not body:
        return {"ok": True}

    logger.info(f"WhatsApp from {sender}: {body[:100]}")

    try:
        from app.services.chat_service import ChatService
        svc = ChatService()
        reply = await svc.chat(body, stream=False)
        reply_text = reply if isinstance(reply, str) else str(reply)
        await send_whatsapp(sender, reply_text[:1600])
    except Exception as e:
        logger.error(f"WhatsApp process error: {e}")
        await send_whatsapp(sender, "Sorry, I ran into an error. Please try again.")

    return {"ok": True}


@router.post("/send")
async def send_message(body: SendRequest):
    if not is_configured():
        raise HTTPException(status_code=503, detail="WhatsApp not configured")
    ok = await send_whatsapp(body.to, body.message)
    return {"ok": ok}


@router.get("/status")
async def status():
    return {"configured": is_configured()}
