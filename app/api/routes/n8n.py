"""n8n workflow automation endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
from app.connectors.n8n_connector import get_n8n_connector

router = APIRouter(prefix="/n8n", tags=["n8n"])


class N8nTrigger(BaseModel):
    data: dict = {}


class N8nReceive(BaseModel):
    message: str = ""
    agent: str = "planner"
    data: dict = {}


@router.post("/trigger/{workflow_id}")
async def trigger_workflow(workflow_id: str, body: N8nTrigger):
    conn = get_n8n_connector()
    return await conn.trigger_workflow(workflow_id, body.data)


@router.get("/workflows")
async def list_workflows():
    conn = get_n8n_connector()
    return {"workflows": await conn.list_workflows()}


@router.get("/executions/{workflow_id}")
async def get_executions(workflow_id: str):
    conn = get_n8n_connector()
    return {"executions": await conn.get_executions(workflow_id)}


@router.post("/receive")
async def receive_from_n8n(body: N8nReceive):
    """n8n triggers ILLIP — route to chat or specific agent."""
    try:
        if body.message:
            from app.services.chat_service import ChatService
            svc = ChatService()
            reply = await svc.chat(body.message, stream=False)
            return {"ok": True, "reply": reply}
        elif body.data and body.agent:
            from app.agents import get_agent_registry
            reg = get_agent_registry()
            agent = reg.get_agent(body.agent)
            if not agent:
                return {"ok": False, "error": f"agent {body.agent!r} not found"}
            import json
            result = await agent.process(json.dumps(body.data))
            return {"ok": True, "result": result}
        return {"ok": False, "error": "provide message or data+agent"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
