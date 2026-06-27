"""Basic health endpoint tests."""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_check():
    """The health endpoint returns a simple machine-readable status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert data["status"] in ["ok", "degraded", "error"]


def test_api_docs_available():
    """FastAPI documentation is available for manual exploration."""
    response = client.get("/docs")
    assert response.status_code == 200
    
    response = client.get("/redoc")
    assert response.status_code == 200
