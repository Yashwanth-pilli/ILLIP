"""Webhook management endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.connectors.webhook_connector import get_webhook_manager

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookRegister(BaseModel):
    name: str
    secret: str
    target_agent: str = "planner"


@router.post("/register")
async def register_webhook(body: WebhookRegister):
    mgr = get_webhook_manager()
    return mgr.register_webhook(body.name, body.secret, body.target_agent)


@router.delete("/{name}")
async def delete_webhook(name: str):
    mgr = get_webhook_manager()
    if not mgr.delete_webhook(name):
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deleted": name}


@router.get("/")
async def list_webhooks():
    mgr = get_webhook_manager()
    return {"webhooks": mgr.list_webhooks()}


@router.post("/receive/{name}")
async def receive_webhook(name: str, request: Request):
    raw = await request.body()
    payload = await request.json()
    signature = request.headers.get("X-Hub-Signature-256", request.headers.get("X-Signature", ""))
    mgr = get_webhook_manager()
    result = await mgr.process_webhook(name, payload, signature, raw)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "failed"))
    return result
