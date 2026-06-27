"""Chat endpoint tests."""

from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_send_message():
    """A valid chat request returns both sides of the exchange."""
    response = client.post(
        "/api/chat/",
        json={
            "message": "Hello, how are you?",
            "include_memory": True,
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "user_message" in data
    assert "assistant_message" in data
    assert data["user_message"] == "Hello, how are you?"
    assert len(data["assistant_message"]) > 0


def test_empty_message():
    """Empty chat messages are rejected before provider execution."""
    response = client.post(
        "/api/chat/",
        json={
            "message": "",
            "include_memory": True,
        }
    )
    assert response.status_code == 400


def test_get_chat_history():
    """Chat history returns a list wrapper and count."""
    # Send a message first
    client.post(
        "/api/chat/",
        json={"message": "Test message", "include_memory": True}
    )
    
    # Get history
    response = client.get("/api/chat/history?limit=10")
    assert response.status_code == 200
    
    data = response.json()
    assert "messages" in data
    assert "count" in data


def test_clear_chat_history():
    """Chat history can be cleared for local development resets."""
    response = client.delete("/api/chat/history")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "cleared"
