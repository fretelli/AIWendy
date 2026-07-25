"""
Test health check endpoint.
"""

import pytest
from fastapi import Response

from routers import health as health_router


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


@pytest.mark.asyncio
async def test_readiness_returns_stable_codes_without_exception_text(monkeypatch):
    class FailingSession:
        async def execute(self, _statement):
            raise RuntimeError("postgresql://user:secret@internal-db/private")

    class FailingRedis:
        async def ping(self):
            raise RuntimeError("redis://:secret@internal-redis/0")

        async def close(self):
            return None

    monkeypatch.setattr(health_router.redis, "from_url", lambda _url: FailingRedis())
    response = Response()

    data = await health_router.readiness_check(response, FailingSession())

    assert response.status_code == 503
    assert data["status"] == "not_ready"
    assert data["checks"]["database"] == {
        "status": "error",
        "code": "database_unavailable",
    }
    assert data["checks"]["redis"] == {
        "status": "error",
        "code": "redis_unavailable",
    }
    assert "secret" not in str(data)


def test_root_endpoint(client):
    """
    Test that the root endpoint is accessible.
    """
    response = client.get("/")
    assert response.status_code in [200, 404]  # Depending on your setup
