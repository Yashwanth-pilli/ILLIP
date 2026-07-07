"""Request-context middleware + data-dir lockdown regression tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_id_and_security_headers():
    r = client.get("/api/health")
    assert r.headers.get("x-request-id")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "SAMEORIGIN"


def test_client_request_id_echoed():
    r = client.get("/api/health", headers={"X-Request-ID": "trace-me-123"})
    assert r.headers.get("x-request-id") == "trace-me-123"


def test_sensitive_data_files_not_web_readable():
    # Only /data/images and /data/terminal are mounted — the DB, chat
    # history and memories must never be reachable over HTTP.
    for path in ("/data/illip.db", "/data/memories.json", "/data/projects/default.json"):
        assert client.get(path).status_code == 404, path
