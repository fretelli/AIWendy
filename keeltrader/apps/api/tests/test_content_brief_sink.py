from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest

from config import Settings
from services.content_brief_sink import (
    ContentBriefRejectedError,
    ContentBriefSinkError,
    build_content_brief,
    content_brief_idempotency_key,
    submit_content_brief,
)


def configured_settings() -> Settings:
    return Settings(
        content_brief_sink_enabled=True,
        content_brief_sink_url="https://editorial.example.test/v1/content-briefs",
        content_brief_sink_token="deployment-secret",
        content_brief_sink_workspace_id="11111111-1111-4111-8111-111111111111",
        content_brief_sink_brand_profile_id="22222222-2222-4222-8222-222222222222",
        content_brief_sink_source_ref_prefix="urn:example:keeltrader:hypothesis",
        content_brief_sink_actor_header="X-Editorial-Actor",
    )


def hypothesis() -> dict:
    return {
        "id": "33333333-3333-4333-8333-333333333333",
        "title": "Versioned investment hypothesis",
        "status": "active",
        "current_version": 4,
        "thesis": "The thesis is testable.",
        "falsification": "A specified observation invalidates it.",
        "evidence": [{"report_id": "report-1", "quote": "Source quote"}],
    }


def request() -> dict:
    return {
        "project_type": "article",
        "audience": "Professional readers",
        "objective": "Explain the hypothesis and its falsifiers",
        "requested_channels": ["wechat"],
    }


def test_payload_binds_exact_hypothesis_and_cannot_enable_delivery() -> None:
    payload = build_content_brief(hypothesis(), request(), configured_settings())
    assert payload["source_resource_ref"].endswith(":33333333-3333-4333-8333-333333333333@4")
    assert payload["constraints"]["external_write_allowed"] is False
    assert payload["constraints"]["requires_evidence_enrichment"] is True
    assert payload["constraints"]["source_snapshot"]["falsification"]
    assert payload["evidence_refs"] == []
    assert content_brief_idempotency_key(payload) == content_brief_idempotency_key(dict(payload))


def test_submission_uses_deployment_owned_sink_identity() -> None:
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["authorization"] = req.headers.get("authorization")
        captured["actor"] = req.headers.get("x-editorial-actor")
        captured["idempotency"] = req.headers.get("idempotency-key")
        return httpx.Response(201, json={"project_id": "project-1", "brief_id": "brief-1"})

    transport = httpx.MockTransport(handler)
    user_id = uuid4()
    result = asyncio.run(submit_content_brief(
        hypothesis=hypothesis(),
        request=request(),
        user_id=user_id,
        settings=configured_settings(),
        client_factory=lambda: httpx.AsyncClient(transport=transport),
    ))
    assert result["brief_id"] == "brief-1"
    assert captured["url"] == "https://editorial.example.test/v1/content-briefs"
    assert captured["authorization"] == "Bearer deployment-secret"
    assert captured["actor"] == f"service:keeltrader:{user_id}"
    assert captured["idempotency"].startswith("keeltrader-content-brief-")


def test_disabled_sink_fails_closed_without_request() -> None:
    called = False

    def factory():
        nonlocal called
        called = True
        return httpx.AsyncClient()

    with pytest.raises(ContentBriefSinkError, match="not configured"):
        asyncio.run(submit_content_brief(
            hypothesis=hypothesis(), request=request(), user_id=uuid4(),
            settings=Settings(content_brief_sink_enabled=False), client_factory=factory,
        ))
    assert called is False


@pytest.mark.parametrize("status", ["invalidated", "archived"])
def test_inactive_hypothesis_cannot_be_submitted(status: str) -> None:
    item = hypothesis()
    item["status"] = status
    with pytest.raises(ContentBriefRejectedError, match="Inactive hypotheses"):
        asyncio.run(submit_content_brief(
            hypothesis=item,
            request=request(),
            user_id=uuid4(),
            settings=configured_settings(),
        ))


def test_actor_header_cannot_override_protocol_headers() -> None:
    config = configured_settings()
    config.content_brief_sink_actor_header = "Authorization"
    with pytest.raises(ContentBriefSinkError, match="actor header is invalid"):
        asyncio.run(submit_content_brief(
            hypothesis=hypothesis(),
            request=request(),
            user_id=uuid4(),
            settings=config,
        ))
