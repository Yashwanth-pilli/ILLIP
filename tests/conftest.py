"""Shared pytest fixtures and configuration."""

import pathlib
import tempfile

import pytest
import pytest_asyncio


@pytest.fixture(scope="session", autouse=True)
def _isolate_local_auth():
    """Point local-login state at a throwaway path so the suite never reads a
    REAL data/auth.json. Without this, a user who has set a login password would
    make every authed endpoint return 401 during tests. Runs before test_client
    so the app's auth middleware sees auth as disabled."""
    from app.services import auth_local
    orig = auth_local._AUTH_PATH
    stub = pathlib.Path(tempfile.gettempdir()) / "illip_test_auth_absent.json"
    try:
        stub.unlink()
    except FileNotFoundError:
        pass
    auth_local._AUTH_PATH = stub
    yield
    auth_local._AUTH_PATH = orig


# asyncio mode is set in pytest.ini — just re-export for clarity
@pytest.fixture(scope="session")
def test_client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        yield client
