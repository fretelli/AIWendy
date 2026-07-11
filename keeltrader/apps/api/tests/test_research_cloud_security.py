from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers import research_cloud


def test_research_cloud_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(research_cloud.settings, "research_cloud_enabled", False)

    with pytest.raises(HTTPException) as exc:
        research_cloud._cloud_base_url()

    assert exc.value.status_code == 503


def test_connection_serialization_never_returns_secrets():
    connection = SimpleNamespace(
        status="active",
        api_key_encrypted="encrypted-secret",
        pending_device_code_encrypted="encrypted-device-code",
        base_url="https://research.example.com",
        client_id="12",
        key_prefix="ragent_abc...",
        scopes=["reports:search"],
        plan_code="personal_default",
        user_code=None,
        verification_uri=None,
        device_expires_at=None,
        cloud_auto_context=False,
        connected_at=None,
        last_checked_at=None,
        last_error=None,
    )

    payload = research_cloud._serialize(connection)

    assert payload["connected"] is True
    assert "api_key_encrypted" not in payload
    assert "pending_device_code_encrypted" not in payload


@pytest.mark.asyncio
async def test_mcp_call_uses_only_research_agent_key(monkeypatch):
    connection = SimpleNamespace(last_checked_at=None, status="active", last_error=None)
    captured = {}

    async def fake_active_key(session, user_id):
        return connection, "ragent_test-key"

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"result": {"structuredContent": {"ok": True}}}

    async def fake_request(method, path, **kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(research_cloud, "_active_key", fake_active_key)
    monkeypatch.setattr(research_cloud, "_cloud_request", fake_request)

    result = await research_cloud._mcp_call(object(), "local-user", "search_reports", {"query": "test"})

    assert result == {"ok": True}
    assert captured["headers"] == {"Authorization": "Bearer ragent_test-key"}
