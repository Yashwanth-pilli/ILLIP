"""Workspace endpoint tests."""

from fastapi.testclient import TestClient
from app.main import app
import os
import tempfile
from pathlib import Path

client = TestClient(app)


def test_workspace_status():
    """Verify workspace status endpoint is online."""
    response = client.get("/api/workspace/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"


def test_workspace_list():
    """Verify listing workspace files."""
    response = client.get("/api/workspace/list")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert "count" in data


def test_workspace_tree():
    """Verify workspace tree retrieval."""
    response = client.get("/api/workspace/tree")
    assert response.status_code == 200
    data = response.json()
    assert "workspace" in data
    assert "items" in data


def test_workspace_health():
    """Verify workspace health diagnostic reporting."""
    response = client.get("/api/workspace/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "total_files" in data
    assert "warnings" in data


def test_workspace_dependencies():
    """Verify extracting workspace dependencies."""
    response = client.get("/api/workspace/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert "manifests" in data
    assert "python_dependencies" in data
    assert "node_dependencies" in data


def test_workspace_search():
    """Verify search workspace functionality."""
    response = client.get("/api/workspace/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "count" in data
    assert "results" in data
