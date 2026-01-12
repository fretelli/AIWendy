"""
Test health check endpoint.
"""

import pytest


def test_health_check(client):
    """
    Test that the health check endpoint returns 200 OK.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"


def test_root_endpoint(client):
    """
    Test that the root endpoint is accessible.
    """
    response = client.get("/")
    assert response.status_code in [200, 404]  # Depending on your setup
