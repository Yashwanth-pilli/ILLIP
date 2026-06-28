"""Observability endpoints — system metrics, runtime counters, history."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from app.monitoring.collector import get_metrics_collector

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


class RecordEvent(BaseModel):
    type: Literal["agent", "skill", "chat", "error"]
    name: str = ""


@router.get("/current")
async def get_current():
    """Latest system + runtime snapshot."""
    return get_metrics_collector().get_current()


@router.get("/history")
async def get_history():
    """Last 60 snapshots (10-min rolling window at 10s interval)."""
    return {"history": get_metrics_collector().get_history()}


@router.get("/summary")
async def get_summary():
    """Uptime, totals, averages."""
    return get_metrics_collector().get_summary()


@router.post("/record")
async def record_event(event: RecordEvent):
    """Manually record an event counter."""
    mc = get_metrics_collector()
    if event.type == "agent":
        mc.record_agent_call(event.name)
    elif event.type == "skill":
        mc.record_skill_call(event.name)
    elif event.type == "chat":
        mc.record_chat()
    elif event.type == "error":
        mc.record_error()
    return {"recorded": True, "type": event.type, "name": event.name}
