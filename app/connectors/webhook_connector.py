"""
Generic inbound webhook system.

Register named webhooks with a secret. Inbound POST verified via HMAC-SHA256.
Payload routed to specified agent.
"""

import hashlib
import hmac
import json
from pathlib import Path
from app.utils import logger
from app.config import settings

_WEBHOOKS_FILE = settings.get_data_path() / "webhooks" / "webhooks.json"


def _load() -> dict:
    _WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _WEBHOOKS_FILE.exists():
        try:
            return json.loads(_WEBHOOKS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save(data: dict):
    _WEBHOOKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WEBHOOKS_FILE.write_text(json.dumps(data, indent=2))


class WebhookManager:
    def __init__(self):
        self._hooks = _load()

    def register_webhook(self, name: str, secret: str, target_agent: str = "planner") -> dict:
        self._hooks[name] = {"secret": secret, "target_agent": target_agent}
        _save(self._hooks)
        return {"name": name, "target_agent": target_agent, "registered": True}

    def delete_webhook(self, name: str) -> bool:
        if name in self._hooks:
            del self._hooks[name]
            _save(self._hooks)
            return True
        return False

    def list_webhooks(self) -> list:
        return [
            {"name": k, "target_agent": v.get("target_agent")}
            for k, v in self._hooks.items()
        ]

    def verify_signature(self, name: str, payload: bytes, signature: str) -> bool:
        hook = self._hooks.get(name)
        if not hook:
            return False
        secret = hook.get("secret", "").encode()
        expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
        # Support "sha256=<hex>" or raw hex
        sig = signature.replace("sha256=", "")
        return hmac.compare_digest(expected, sig)

    async def process_webhook(self, name: str, payload: dict, signature: str, raw_body: bytes) -> dict:
        if not self.verify_signature(name, raw_body, signature):
            return {"ok": False, "error": "invalid signature"}
        hook = self._hooks.get(name)
        if not hook:
            return {"ok": False, "error": "webhook not found"}
        target = hook.get("target_agent", "planner")
        try:
            from app.agents import get_agent_registry
            reg = get_agent_registry()
            agent = reg.get_agent(target)
            if not agent:
                return {"ok": False, "error": f"agent {target!r} not found"}
            task_input = json.dumps(payload)
            result = await agent.process(task_input)
            return {"ok": True, "agent": target, "result": result}
        except Exception as e:
            logger.error(f"Webhook process error: {e}")
            return {"ok": False, "error": str(e)}


_manager: WebhookManager | None = None


def get_webhook_manager() -> WebhookManager:
    global _manager
    if _manager is None:
        _manager = WebhookManager()
    return _manager
