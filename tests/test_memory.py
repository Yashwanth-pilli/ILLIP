"""
Memory endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_store_memory():
    """Test storing memory"""
    response = client.post(
        "/api/memory/store?key=test_key&value=test_value&category=test"
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["key"] == "test_key"
    assert data["value"] == "test_value"
    assert "id" in data


def test_search_memory():
    """Test searching memory"""
    # Store something first
    client.post("/api/memory/store?key=query_test&value=find me&category=test")
    
    response = client.get("/api/memory/search?query=find&limit=10")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "count" in data


def test_get_memory_stats():
    """Test getting memory statistics"""
    response = client.get("/api/memory/stats/overview")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_entries" in data
    assert "categories" in data
