"""
Task endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_create_task():
    """Test creating a task"""
    response = client.post(
        "/api/tasks/",
        json={
            "title": "Test Task",
            "description": "Test task description",
            "agent_type": "builder",
            "priority": 1,
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["status"] == "pending"
    assert "id" in data


def test_list_tasks():
    """Test listing tasks"""
    # Create a task first
    client.post(
        "/api/tasks/",
        json={"title": "Test Task", "description": "Test"}
    )
    
    response = client.get("/api/tasks/?limit=10")
    assert response.status_code == 200
    
    data = response.json()
    assert "tasks" in data
    assert "count" in data


def test_get_task_stats():
    """Test getting task statistics"""
    response = client.get("/api/tasks/stats/overview")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert "pending" in data
    assert "completed" in data
