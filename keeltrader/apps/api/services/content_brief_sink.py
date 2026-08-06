from __future__ import annotations

import hashlib
import json
from typing import Any, Callable
from uuid import UUID

import httpx

from config import Settings, get_settings


class ContentBriefSinkError(RuntimeError):
    pass


class ContentBriefRejectedError(ContentBriefSinkError):
    pass


def build_content_brief(
    hypothesis: dict[str, Any],
    request: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    hypothesis_id = str(hypothesis["id"])
    version = int(hypothesis["current_version"])
    prefix = str(settings.content_brief_sink_source_ref_prefix or "").rstrip(":")
    source_resource_ref = f"{prefix}:{hypothesis_id}@{version}" if prefix else None
    payload = {
        "workspace_id": settings.content_brief_sink_workspace_id,
        "brand_profile_id": settings.content_brief_sink_brand_profile_id,
        "title": hypothesis["title"],
        "project_type": request["project_type"],
        "audience": request["audience"],
        "objective": request["objective"],
        "thesis": hypothesis["thesis"],
        "requested_channels": request.get("requested_channels", []),
        "evidence_refs": [],
        "constraints": {
            "external_write_allowed": False,
            "requires_evidence_enrichment": True,
            "source_snapshot": {
                "hypothesis_id": hypothesis_id,
                "version": version,
                "status": hypothesis["status"],
                "falsification": hypothesis["falsification"],
                "evidence": hypothesis.get("evidence", []),
            },
        },
    }
    if source_resource_ref:
        payload["source_resource_ref"] = source_resource_ref
    return payload


def content_brief_idempotency_key(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "keeltrader-content-brief-" + hashlib.sha256(canonical.encode()).hexdigest()


async def submit_content_brief(
    *,
    hypothesis: dict[str, Any],
    request: dict[str, Any],
    user_id: UUID,
    settings: Settings | None = None,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
) -> dict[str, Any]:
    config = settings or get_settings()
    if hypothesis.get("status") in {"invalidated", "archived"}:
        raise ContentBriefRejectedError("Inactive hypotheses cannot be submitted")
    required = (
        config.content_brief_sink_url,
        config.content_brief_sink_token,
        config.content_brief_sink_workspace_id,
        config.content_brief_sink_brand_profile_id,
    )
    if not config.content_brief_sink_enabled or not all(required):
        raise ContentBriefSinkError("Content brief sink is not configured")
    actor_header = config.content_brief_sink_actor_header.strip()
    if actor_header.lower() in {"authorization", "content-type", "idempotency-key"}:
        raise ContentBriefSinkError("Content brief sink actor header is invalid")
    payload = build_content_brief(hypothesis, request, config)
    headers = {
        "Authorization": f"Bearer {config.content_brief_sink_token}",
        "Idempotency-Key": content_brief_idempotency_key(payload),
        actor_header: f"{config.content_brief_sink_actor_prefix}:{user_id}",
    }
    factory = client_factory or (
        lambda: httpx.AsyncClient(timeout=config.content_brief_sink_timeout_seconds)
    )
    try:
        async with factory() as client:
            response = await client.post(config.content_brief_sink_url, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ContentBriefSinkError("Content brief sink request failed") from exc
    if not isinstance(body, dict):
        raise ContentBriefSinkError("Content brief sink returned an invalid response")
    return body
