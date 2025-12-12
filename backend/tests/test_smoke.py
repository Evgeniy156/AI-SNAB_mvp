"""
Smoke tests for AI-SNAB application.
These tests verify that basic endpoints are working without external dependencies.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    """Test GET /health returns 200 and status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_db_endpoint(client: TestClient):
    """Test GET /health/db returns 200 and status ok."""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok" or data.get("ok") is True


def test_health_storage_endpoint(client: TestClient):
    """Test GET /health/storage returns 200 and status ok."""
    response = client.get("/health/storage")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok" or data.get("ok") is True


def test_ui_endpoint(client: TestClient):
    """Test GET /ui returns 200 (UI page is accessible)."""
    response = client.get("/ui")
    assert response.status_code == 200
    # UI should return HTML
    assert "text/html" in response.headers.get("content-type", "")

