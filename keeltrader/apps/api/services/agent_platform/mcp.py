from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx

from core.encryption import get_encryption_service
from domain.agent_platform.models import AgentMCPServer
from services.agent_platform.network import validate_external_https_url

MAX_MCP_RESPONSE_BYTES = 2 * 1024 * 1024


def schema_digest(tools: list[dict[str, Any]]) -> str:
    payload = json.dumps(tools, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


async def _rpc(server: AgentMCPServer, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    url = validate_external_https_url(server.url, allow_private=bool(server.allow_private_network))
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    token = get_encryption_service().decrypt(server.auth_encrypted or "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.post(url, headers=headers, json=body)
    if len(response.content) > MAX_MCP_RESPONSE_BYTES:
        raise ValueError("MCP response exceeded size limit")
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise ValueError(str(data["error"]))
    return data.get("result") or {}


async def discover_tools(server: AgentMCPServer) -> list[dict[str, Any]]:
    await _rpc(server, "initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "keeltrader", "version": "2"},
    })
    result = await _rpc(server, "tools/list")
    tools = result.get("tools") or []
    return [
        {"name": str(item.get("name") or ""), "description": str(item.get("description") or ""),
         "inputSchema": item.get("inputSchema") or {"type": "object"}}
        for item in tools if item.get("name")
    ]


async def call_tool(server: AgentMCPServer, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return await _rpc(server, "tools/call", {"name": name, "arguments": arguments})

