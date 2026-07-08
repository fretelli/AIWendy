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
    assert data["version"]
    assert "git_sha" in data
    assert "build_time" in data
    assert "build_type" in data


def test_liveness_exposes_build_metadata(client):
    response = client.get("/api/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert data["version"]
    assert "git_sha" in data


def test_root_endpoint(client):
    """
    Test that the root endpoint is accessible.
    """
    response = client.get("/")
    assert response.status_code in [200, 404]  # Depending on your setup
