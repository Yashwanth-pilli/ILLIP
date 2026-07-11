"""
Tests for local login. CRITICAL: every test that touches password state
monkeypatches auth_local._AUTH_PATH to a temp file, so a real data/auth.json is
never created — otherwise the whole app (and suite) would demand a login.
"""

import pytest

from app.services import auth_local


@pytest.fixture
def tmp_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_local, "_AUTH_PATH", tmp_path / "auth.json")
    return tmp_path


def test_disabled_by_default(tmp_auth):
    assert auth_local.is_enabled() is False
    # When disabled, everyone validates (open-localhost default)
    assert auth_local.validate_token(None) is True
    assert auth_local.validate_token("anything") is True


def test_set_password_enables_and_login(tmp_auth):
    ok, _ = auth_local.set_password("hunter2")
    assert ok
    assert auth_local.is_enabled() is True
    # Now a token is required
    assert auth_local.validate_token(None) is False
    token = auth_local.login("hunter2")
    assert token
    assert auth_local.validate_token(token) is True


def test_wrong_password_rejected(tmp_auth):
    auth_local.set_password("correct-horse")
    assert auth_local.login("wrong") is None


def test_too_short_password_refused(tmp_auth):
    ok, msg = auth_local.set_password("ab")
    assert not ok
    assert "4 characters" in msg


def test_change_requires_current(tmp_auth):
    auth_local.set_password("first-pass")
    # Wrong current → refused
    ok, _ = auth_local.set_password("new-pass", current_password="nope")
    assert not ok
    # Correct current → allowed
    ok, _ = auth_local.set_password("new-pass", current_password="first-pass")
    assert ok
    assert auth_local.login("new-pass")


def test_password_change_invalidates_sessions(tmp_auth):
    auth_local.set_password("first-pass")
    token = auth_local.login("first-pass")
    assert auth_local.validate_token(token)
    auth_local.set_password("second-pass", current_password="first-pass")
    # Old session must be dead after a password change
    assert auth_local.validate_token(token) is False


def test_logout_kills_token(tmp_auth):
    auth_local.set_password("pw-secret")
    token = auth_local.login("pw-secret")
    assert auth_local.validate_token(token)
    auth_local.logout(token)
    assert auth_local.validate_token(token) is False


def test_auth_status_route_default_disabled(test_client):
    # No password set in the real data/auth.json → auth off, everyone authed.
    r = test_client.get("/api/auth/status")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert body["authenticated"] is True
