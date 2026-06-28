"""
n8n workflow automation connector.

ILLIP → n8n: trigger workflows via n8n webhook URLs.
n8n → ILLIP: receive triggers at POST /n8n/receive, route to ILLIP chat/agent.

Config:
  N8N_BASE_URL  — default: http://localhost:5678
  N8N_API_KEY   — n8n REST API key (Settings → API in n8n)
"""

import os
import httpx
from app.utils import logger

_N8N_BASE = os.getenv("N8N_BASE_URL", "http://localhost:5678")
_N8N_KEY = os.getenv("N8N_API_KEY", "")


class N8nConnector:
    def __init__(self):
        self.base = _N8N_BASE.rstrip("/")
        self.headers = {"X-N8N-API-KEY": _N8N_KEY} if _N8N_KEY else {}

    async def trigger_workflow(self, workflow_id: str, data: dict) -> dict:
        """POST to n8n webhook trigger URL for a workflow."""
        url = f"{self.base}/webhook/{workflow_id}"
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(url, json=data, headers=self.headers)
                return {"ok": True, "status": r.status_code, "response": r.text[:500]}
        except Exception as e:
            logger.error(f"n8n trigger error: {e}")
            return {"ok": False, "error": str(e)}

    async def list_workflows(self) -> list:
        """List workflows via n8n REST API."""
        if not _N8N_KEY:
            return []
        url = f"{self.base}/api/v1/workflows"
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url, headers=self.headers)
                data = r.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"n8n list workflows error: {e}")
            return []

    async def get_executions(self, workflow_id: str) -> list:
        """Get recent executions for a workflow."""
        if not _N8N_KEY:
            return []
        url = f"{self.base}/api/v1/executions?workflowId={workflow_id}&limit=20"
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url, headers=self.headers)
                data = r.json()
                return data.get("data", [])
        except Exception as e:
            logger.error(f"n8n executions error: {e}")
            return []


_connector: N8nConnector | None = None


def get_n8n_connector() -> N8nConnector:
    global _connector
    if _connector is None:
        _connector = N8nConnector()
    return _connector


from app.connectors.base_connector import BaseConnector  # noqa: E402


class N8nRegistryConnector(BaseConnector):
    name = "n8n"
    description = "n8n workflow automation — trigger workflows, receive n8n → ILLIP calls"
    required_env_vars = []   # works without key (local n8n); key unlocks API features
    optional_env_vars = ["N8N_BASE_URL", "N8N_API_KEY"]

    async def start(self) -> bool:
        return True  # stateless HTTP connector

    async def stop(self) -> None:
        pass

    def is_active(self) -> bool:
        return True  # always available, just HTTP calls
