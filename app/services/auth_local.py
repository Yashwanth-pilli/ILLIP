"""
Local single-user login — protects ILLIP when it's reachable beyond localhost
(LAN, tunnel, shared machine) without any cloud account.

Design goals:
  - OFF by default. Until the user sets a password, ILLIP behaves exactly as
    before (open on localhost). Setting a password turns enforcement ON. This
    means the feature can never lock an existing user out unexpectedly.
  - No new dependency. Password hashing = PBKDF2-HMAC-SHA256 (stdlib hashlib),
    200k iterations, per-user random salt, constant-time compare.
  - Server-side opaque sessions (secrets.token_urlsafe). No secret leaves the
    box. Sessions persist across restarts so a reload doesn't force re-login.
  - Personal data stays local: this only gates access. It never sends anything
    anywhere. See PRIVACY note in readers.py / search_service for the outbound side.

State lives in data/auth.json (0600-ish; local disk only), which is gitignored
like the rest of data/.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

_AUTH_PATH = Path("data/auth.json")
_ITERATIONS = 200_000
_SESSION_TTL = 60 * 60 * 24 * 30  # 30 days


def _load() -> dict:
    if _AUTH_PATH.exists():
        try:
            return json.loads(_AUTH_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    _AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    _AUTH_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_enabled() -> bool:
    """True once a password has been set. Until then, auth is off."""
    return bool(_load().get("password_hash"))


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS
    ).hex()


def set_password(new_password: str, current_password: str | None = None) -> tuple[bool, str]:
    """Set (first time) or change the password.

    Returns (ok, message). On change, `current_password` must verify.
    """
    if not new_password or len(new_password) < 4:
        return False, "Password must be at least 4 characters."
    data = _load()
    if data.get("password_hash"):
        # changing → require the current password
        if not current_password or not _verify_password(current_password, data):
            return False, "Current password is wrong."
    salt = secrets.token_hex(16)
    data["password_hash"] = _hash(new_password, salt)
    data["salt"] = salt
    data["iterations"] = _ITERATIONS
    data.setdefault("sessions", {})
    # Changing the password invalidates all existing sessions.
    data["sessions"] = {}
    _save(data)
    return True, "Password set."


def _verify_password(password: str, data: dict | None = None) -> bool:
    data = data or _load()
    salt = data.get("salt")
    stored = data.get("password_hash")
    if not salt or not stored:
        return False
    return hmac.compare_digest(_hash(password, salt), stored)


def _prune_sessions(data: dict) -> None:
    now = time.time()
    data["sessions"] = {t: e for t, e in data.get("sessions", {}).items() if e > now}


def login(password: str) -> str | None:
    """Verify password, return a fresh session token, or None on failure."""
    data = _load()
    if not _verify_password(password, data):
        return None
    _prune_sessions(data)
    token = secrets.token_urlsafe(32)
    data.setdefault("sessions", {})[token] = time.time() + _SESSION_TTL
    _save(data)
    return token


def validate_token(token: str | None) -> bool:
    """True if the token is a live session. Also true for everyone when auth is
    disabled (no password set) — that's the open-localhost default."""
    if not is_enabled():
        return True
    if not token:
        return False
    data = _load()
    _prune_sessions(data)
    exp = data.get("sessions", {}).get(token)
    if exp:
        return True
    return False


def logout(token: str | None) -> None:
    if not token:
        return
    data = _load()
    if token in data.get("sessions", {}):
        del data["sessions"][token]
        _save(data)
