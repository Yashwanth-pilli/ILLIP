"""
Request context middleware — request ID, timing log, security headers.

Every response gets an X-Request-ID (client-supplied one is echoed back, so
external callers can correlate) plus baseline security headers. Every /api
and /v1 call is logged with method, path, status and duration under that ID,
which the global error handler in app.main also includes in 500 responses.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils import logger

# SAMEORIGIN (not DENY): the UI previews its own generated artifacts.
# HSTS/CSP intentionally omitted — ILLIP serves plain http on localhost/LAN,
# and the Vite bundle uses inline styles a strict CSP would break.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "no-referrer",
}


from starlette.responses import JSONResponse

# Paths reachable WITHOUT a session even when login is enabled: the login
# endpoints themselves, health, and the static UI shell (so the login screen
# can load). Everything else under /api and /v1 needs a valid token.
_AUTH_EXEMPT_PREFIXES = ("/api/auth", "/api/health")


class LocalAuthMiddleware(BaseHTTPMiddleware):
    """Gate /api and /v1 behind the local password — but ONLY once the user has
    set one. With no password set, auth_local.is_enabled() is False and this is a
    complete pass-through, so the open-localhost default is untouched."""

    async def dispatch(self, request: Request, call_next):
        from app.services import auth_local
        path = request.url.path
        if (
            auth_local.is_enabled()
            and path.startswith(("/api", "/v1"))
            and not path.startswith(_AUTH_EXEMPT_PREFIXES)
        ):
            token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
            if not token:
                token = request.query_params.get("token", "").strip()  # SSE/EventSource can't set headers
            if not auth_local.validate_token(token or None):
                return JSONResponse(
                    {"detail": "Login required.", "auth": "required"}, status_code=401
                )
        return await call_next(request)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID", "").strip()[:64] or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        if request.url.path.startswith(("/api", "/v1")):
            ms = (time.perf_counter() - start) * 1000
            logger.info(
                f"[{rid}] {request.method} {request.url.path} -> {response.status_code} {ms:.0f}ms"
            )
        return response
