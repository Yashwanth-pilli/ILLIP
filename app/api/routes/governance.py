from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.governance.manager import get_governance_manager
from app.governance.policy import PolicyLevel

router = APIRouter(prefix="/governance", tags=["governance"])


class PolicyUpdate(BaseModel):
    level: str  # "allow" | "require_approval" | "block"


@router.get("/policies")
async def list_policies():
    mgr = get_governance_manager()
    return {"policies": [p.to_dict() for p in mgr.policies.values()]}


@router.put("/policies/{name}")
async def update_policy(name: str, body: PolicyUpdate):
    try:
        level = PolicyLevel(body.level)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid level '{body.level}'")
    mgr = get_governance_manager()
    if not mgr.update_policy(name, level):
        raise HTTPException(status_code=404, detail=f"Policy '{name}' not found")
    return {"ok": True, "policy": name, "level": body.level}


@router.get("/pending")
async def get_pending():
    mgr = get_governance_manager()
    return {"pending": mgr.get_pending()}


@router.post("/approve/{request_id}")
async def approve_request(request_id: str):
    mgr = get_governance_manager()
    if not mgr.approve(request_id):
        raise HTTPException(status_code=404, detail="Request not found")
    return {"ok": True, "request_id": request_id, "status": "approved"}


@router.post("/deny/{request_id}")
async def deny_request(request_id: str):
    mgr = get_governance_manager()
    if not mgr.deny(request_id):
        raise HTTPException(status_code=404, detail="Request not found")
    return {"ok": True, "request_id": request_id, "status": "denied"}


@router.get("/audit")
async def get_audit(limit: int = 100):
    mgr = get_governance_manager()
    return {"audit": mgr.get_audit(limit=min(limit, 500))}


@router.post("/check")
async def check_action(resource_type: str, action: str, context: dict = None):
    mgr = get_governance_manager()
    return mgr.check(resource_type, action, context or {})
