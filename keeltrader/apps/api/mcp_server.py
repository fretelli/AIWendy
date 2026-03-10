"""KeelTrader MCP Server — exposes 15 tools as standard MCP tools.

Supports both stdio and SSE transports.
SSE transport is mounted at /mcp on the FastAPI app.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from core.database import get_db_context
from core.logging import get_logger
from services.tool_executor import TOOL_DEFINITIONS, execute_tool

logger = get_logger(__name__)

# Default user ID for MCP connections (guest mode)
# In production, this is resolved from the MCP session context
_GUEST_USER_ID = None


def create_mcp_server() -> Server:
    """Create and configure the MCP server with all KeelTrader tools."""
    server = Server("keeltrader")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools."""
        tools = []
        for td in TOOL_DEFINITIONS:
            tools.append(
                Tool(
                    name=td["name"],
                    description=td["description"],
                    inputSchema=td["parameters"],
                )
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        """Execute a tool and return the result."""
        arguments = arguments or {}

        # Resolve user_id from MCP session or use guest
        user_id = await _resolve_user_id()

        async with get_db_context() as session:
            result = await execute_tool(name, arguments, session, user_id)

        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

    return server


async def _resolve_user_id():
    """Resolve user ID for MCP connections."""
    global _GUEST_USER_ID

    if _GUEST_USER_ID:
        return _GUEST_USER_ID

    # Ensure guest user exists and cache the ID
    from sqlalchemy import select
    from core.auth import GUEST_EMAIL
    from domain.user.models import User

    async with get_db_context() as session:
        result = await session.execute(select(User).where(User.email == GUEST_EMAIL))
        user = result.scalar_one_or_none()
        if user:
            _GUEST_USER_ID = user.id
            return user.id

        # Create guest user if not exists
        from core.auth import _ensure_guest_user
        user = await _ensure_guest_user(session)
        _GUEST_USER_ID = user.id
        return user.id


def mount_mcp_sse(app):
    """Mount MCP SSE transport on the FastAPI app at /mcp."""
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.routing import Mount, Route

        server = create_mcp_server()
        sse_transport = SseServerTransport("/mcp/messages/")

        async def handle_sse(request):
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(
                    streams[0], streams[1], server.create_initialization_options()
                )

        async def handle_messages(request):
            await sse_transport.handle_post_message(
                request.scope, request.receive, request._send
            )

        # Mount SSE endpoints
        app.mount(
            "/mcp",
            app=Mount(
                "/mcp",
                routes=[
                    Route("/sse", endpoint=handle_sse),
                    Route("/messages/", endpoint=handle_messages, methods=["POST"]),
                ],
            ),
        )
        logger.info("MCP SSE transport mounted at /mcp/sse")
    except ImportError:
        logger.warning("mcp package not installed, MCP Server disabled")
    except Exception as e:
        logger.error("Failed to mount MCP SSE transport", error=str(e))
