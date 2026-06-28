from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.twin.tracker import get_twin_tracker

router = APIRouter(prefix="/twin", tags=["digital-twin"])


class PreferenceUpdate(BaseModel):
    key: str
    value: Any


class EventRecord(BaseModel):
    event_type: str  # "agent_use" | "skill_use" | "decision" | "style_sample"
    data: dict


@router.get("/summary")
async def get_summary():
    return get_twin_tracker().get_summary()


@router.get("/model")
async def get_model():
    return get_twin_tracker().get_model().to_dict()


@router.put("/preference")
async def update_preference(body: PreferenceUpdate):
    get_twin_tracker().update_preference(body.key, body.value)
    return {"ok": True, "key": body.key, "value": body.value}


@router.post("/reset")
async def reset_twin():
    get_twin_tracker().reset()
    return {"ok": True, "message": "Digital twin reset"}


@router.post("/record")
async def record_event(body: EventRecord):
    tracker = get_twin_tracker()
    et = body.event_type
    d = body.data

    if et == "agent_use":
        agent_type = d.get("agent_type")
        if not agent_type:
            raise HTTPException(status_code=400, detail="agent_type required")
        tracker.record_agent_use(agent_type)

    elif et == "skill_use":
        skill_name = d.get("skill_name")
        if not skill_name:
            raise HTTPException(status_code=400, detail="skill_name required")
        tracker.record_skill_use(skill_name)

    elif et == "decision":
        context = d.get("context", "")
        choice = d.get("choice", "")
        tracker.record_decision(context, choice)

    elif et == "style_sample":
        messages = d.get("messages", [])
        style = tracker.infer_style(messages)
        return {"ok": True, "inferred_style": style}

    elif et == "project_activity":
        project_id = d.get("project_id")
        if not project_id:
            raise HTTPException(status_code=400, detail="project_id required")
        tracker.update_project_habit(project_id, d.get("session_minutes", 0))

    else:
        raise HTTPException(status_code=400, detail=f"Unknown event_type '{et}'")

    return {"ok": True, "event_type": et}
