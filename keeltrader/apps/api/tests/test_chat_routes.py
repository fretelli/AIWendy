"""Regression tests for the active chat router surface."""

from tests.route_utils import route_paths


def test_chat_v2_routes_are_mounted_without_legacy_root(client):
    paths = route_paths(client.app)

    assert "/api/v1/chat/send" in paths
    assert "/api/v1/chat/quick" in paths
    assert "/api/v1/chat/sessions" in paths
    assert "/api/v1/chat/sessions/{session_id}/messages" in paths
    assert "/api/v1/chat" not in paths
    assert "/api/v1/chat/" not in paths
