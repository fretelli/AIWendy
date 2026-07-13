from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from domain.research_cloud.models import ResearchCloudConnection
from domain.user.models import User

router = APIRouter()
settings = get_settings()
encryption = get_encryption_service()


class ResearchSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    broker: str | None = Field(default=None, max_length=100)
    companies: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None


class ResearchCloudPreferences(BaseModel):
    cloud_auto_context: bool


def _cloud_base_url() -> str:
    if not settings.research_cloud_enabled:
        raise HTTPException(status_code=503, detail="Research Cloud is disabled")
    base = str(settings.research_cloud_base_url or "").strip().rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="Research Cloud is not configured")
    return base


async def _get_connection(session: AsyncSession, user_id) -> ResearchCloudConnection | None:
    result = await session.execute(
        select(ResearchCloudConnection).where(ResearchCloudConnection.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _serialize(connection: ResearchCloudConnection | None) -> dict[str, Any]:
    if connection is None:
        return {"status": "disconnected", "connected": False}
    return {
        "status": connection.status,
        "connected": connection.status == "active" and bool(connection.api_key_encrypted),
        "base_url": connection.base_url,
        "client_id": connection.client_id,
        "key_prefix": connection.key_prefix,
        "scopes": connection.scopes or [],
        "plan_code": connection.plan_code,
        "user_code": connection.user_code,
        "verification_uri": connection.verification_uri,
        "device_expires_at": connection.device_expires_at.isoformat() if connection.device_expires_at else None,
        "cloud_auto_context": bool(connection.cloud_auto_context),
        "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
        "last_checked_at": connection.last_checked_at.isoformat() if connection.last_checked_at else None,
        "last_error": connection.last_error,
    }


async def _cloud_request(method: str, path: str, **kwargs) -> httpx.Response:
    timeout = max(3.0, float(settings.research_cloud_timeout_seconds or 12.0))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, f"{_cloud_base_url()}{path}", **kwargs)
    return response


@router.post("/connection/start")
async def start_connection(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    response = await _cloud_request(
        "POST",
        "/api/agent/device-authorizations",
        json={
            "client_name": "KeelTrader",
            "platform": "generic",
            "metadata": {"client": "keeltrader", "deployment_mode": settings.deployment_mode},
        },
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Unable to start Research Cloud authorization")
    payload = response.json()
    device_code = str(payload.get("device_code") or "")
    if not device_code:
        raise HTTPException(status_code=502, detail="Research Cloud returned an invalid authorization")

    connection = await _get_connection(session, current_user.id)
    if connection is None:
        connection = ResearchCloudConnection(user_id=current_user.id, base_url=_cloud_base_url())
        session.add(connection)
    connection.base_url = _cloud_base_url()
    connection.status = "pending"
    connection.api_key_encrypted = None
    connection.pending_device_code_encrypted = encryption.encrypt(device_code)
    connection.user_code = str(payload.get("user_code") or "")
    connection.verification_uri = str(payload.get("verification_uri") or "")
    connection.device_expires_at = datetime.now(UTC) + timedelta(seconds=int(payload.get("expires_in") or 600))
    connection.last_error = None
    connection.last_checked_at = datetime.now(UTC)
    await session.flush()
    return _serialize(connection)


@router.get("/connection/status")
async def connection_status(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    connection = await _get_connection(session, current_user.id)
    if connection is None or connection.status != "pending":
        return _serialize(connection)
    if connection.device_expires_at and connection.device_expires_at <= datetime.now(UTC):
        connection.status = "expired"
        connection.pending_device_code_encrypted = None
        connection.last_error = "Device authorization expired"
        return _serialize(connection)

    device_code = encryption.decrypt(connection.pending_device_code_encrypted or "")
    if not device_code:
        connection.status = "error"
        connection.last_error = "Pending authorization could not be decrypted"
        return _serialize(connection)

    response = await _cloud_request(
        "POST",
        "/api/agent/device-authorizations/token",
        json={"device_code": device_code},
    )
    connection.last_checked_at = datetime.now(UTC)
    if response.status_code == 428:
        return _serialize(connection)
    if response.status_code >= 400:
        detail = response.json().get("detail", {}) if "application/json" in response.headers.get("content-type", "") else {}
        error = detail.get("error") if isinstance(detail, dict) else None
        connection.status = "expired" if error == "authorization_expired" else "error"
        connection.last_error = str(detail.get("message") or error or "Authorization failed") if isinstance(detail, dict) else "Authorization failed"
        connection.pending_device_code_encrypted = None
        return _serialize(connection)

    payload = response.json()
    api_key = str(payload.get("api_key") or "")
    if not api_key.startswith("ragent_"):
        connection.status = "error"
        connection.last_error = "Research Cloud returned an invalid API key"
        return _serialize(connection)
    connection.status = "active"
    connection.api_key_encrypted = encryption.encrypt(api_key)
    connection.pending_device_code_encrypted = None
    connection.client_id = str(payload.get("id") or "")
    connection.key_prefix = str((payload.get("key") or {}).get("key_prefix") or api_key[:12])
    connection.scopes = list((payload.get("metadata") or {}).get("scopes") or payload.get("scopes") or [])
    connection.plan_code = str(payload.get("plan_code") or "")
    connection.connected_at = datetime.now(UTC)
    connection.last_error = None
    return _serialize(connection)


@router.get("/connection")
async def get_connection(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return _serialize(await _get_connection(session, current_user.id))


@router.put("/connection/preferences")
async def update_connection_preferences(
    request: ResearchCloudPreferences,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    connection = await _get_connection(session, current_user.id)
    if connection is None or connection.status != "active":
        raise HTTPException(status_code=409, detail="Research Cloud is not connected")
    connection.cloud_auto_context = request.cloud_auto_context
    return _serialize(connection)


async def _active_key(session: AsyncSession, user_id) -> tuple[ResearchCloudConnection, str]:
    connection = await _get_connection(session, user_id)
    if connection is None or connection.status != "active" or not connection.api_key_encrypted:
        raise HTTPException(status_code=409, detail="Research Cloud is not connected")
    api_key = encryption.decrypt(connection.api_key_encrypted)
    if not api_key.startswith("ragent_"):
        raise HTTPException(status_code=500, detail="Research Cloud credential is unavailable")
    return connection, api_key


async def _mcp_call(session: AsyncSession, user_id, tool_name: str, arguments: dict[str, Any]):
    connection, api_key = await _active_key(session, user_id)
    response = await _cloud_request(
        "POST",
        "/api/agent/mcp",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )
    connection.last_checked_at = datetime.now(UTC)
    if response.status_code in {401, 403}:
        connection.status = "error"
        connection.last_error = "Research Cloud credential was rejected"
        raise HTTPException(status_code=401, detail=connection.last_error)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Research Cloud request failed")
    payload = response.json()
    if payload.get("error"):
        error = payload["error"]
        data = error.get("data") if isinstance(error, dict) else None
        if isinstance(data, dict) and data.get("error") == "quota_exceeded":
            raise HTTPException(status_code=429, detail=data)
        raise HTTPException(status_code=502, detail=error)
    result = payload.get("result") or {}
    return result.get("structuredContent") or {}


@router.delete("/connection")
async def disconnect(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    connection = await _get_connection(session, current_user.id)
    if connection is None:
        return {"status": "disconnected", "connected": False}
    if connection.api_key_encrypted:
        api_key = encryption.decrypt(connection.api_key_encrypted)
        if api_key:
            try:
                await _cloud_request(
                    "DELETE",
                    "/api/agent/connection",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            except httpx.HTTPError:
                pass
    connection.status = "revoked"
    connection.api_key_encrypted = None
    connection.pending_device_code_encrypted = None
    connection.last_error = None
    return _serialize(connection)


@router.post("/search")
async def search_reports(
    request: ResearchSearchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    arguments = request.model_dump(exclude_none=True)
    if arguments.get("companies"):
        arguments["companies"] = [str(item)[:100] for item in arguments["companies"][:10]]
    return await _mcp_call(session, current_user.id, "search_reports", arguments)


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _mcp_call(session, current_user.id, "get_report", {"report_id": report_id})


@router.post("/reports/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _mcp_call(session, current_user.id, "get_report_pdf_link", {"report_id": report_id})


@router.get("/quota")
async def get_quota(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _mcp_call(session, current_user.id, "get_agent_quota", {})
