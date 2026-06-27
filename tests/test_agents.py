"""Agent endpoint tests."""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_list_agents():
    """The list endpoint returns beginner-friendly status for each agent."""
    response = client.get("/api/agents/")
    assert response.status_code == 200
    
    data = response.json()
    assert "agents" in data
    assert "total_available" in data
    assert len(data["agents"]) > 0
    assert {"agent_type", "name", "is_available", "task_count"}.issubset(
        data["agents"][0].keys()
    )


def test_get_agent_status():
    """A known agent exposes its type, display name, and availability."""
    response = client.get("/api/agents/planner")
    assert response.status_code == 200
    
    data = response.json()
    assert data["agent_type"] == "planner"
    assert data["name"] == "Planner Agent"
    assert "is_available" in data


def test_execute_agent_task():
    """Agent execution accepts a simple query-string task input."""
    response = client.post(
        "/api/agents/planner/execute?task_input=Create a plan for building a feature"
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "output" in data or "error" in data
