"""MCP route mount contract tests."""

from fastapi import FastAPI

from mcp_server import mount_mcp_sse
from tests.route_utils import route_paths


def test_mcp_sse_routes_are_mounted():
    app = FastAPI()

    mount_mcp_sse(app)

    paths = route_paths(app)
    assert "/mcp/sse" in paths
    assert "/mcp/messages/" in paths
