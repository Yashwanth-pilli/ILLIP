"""
Local login endpoints. Auth is OFF until a password is set (open-localhost
default), so these are safe to expose. Enforcement happens in the auth gate
middleware, which exempts this router.
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.services import auth_local

router = APIRouter(prefix="/auth", tags=["auth"])


class SetupRequest(BaseModel):
    password: str
    current_password: str | None = None


class LoginRequest(BaseModel):
    password: str


@router.get("/status")
async def status(authorization: str = Header(default="")):
    """Is a password set, and is this caller authenticated?"""
    token = authorization.removeprefix("Bearer ").strip() or None
    return {
        "enabled": auth_local.is_enabled(),
        "authenticated": auth_local.validate_token(token),
    }


@router.post("/setup")
async def setup(req: SetupRequest):
    """Set the password the first time, or change it (needs current_password)."""
    ok, msg = auth_local.set_password(req.password, req.current_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    # Setting a password enables auth; hand back a token so the caller stays in.
    token = auth_local.login(req.password)
    return {"status": "ok", "message": msg, "token": token}


@router.post("/login")
async def login(req: LoginRequest):
    token = auth_local.login(req.password)
    if not token:
        raise HTTPException(status_code=401, detail="Wrong password.")
    return {"status": "ok", "token": token}


@router.post("/logout")
async def logout(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip() or None
    auth_local.logout(token)
    return {"status": "ok"}
