"""Route contract tests for the active production API surface."""

from tests.route_utils import route_paths


def test_active_route_prefixes_are_mounted(client):
    paths = route_paths(client.app)

    expected_paths = {
        "/api/health",
        "/api/health/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/users/me",
        "/api/v1/chat/send",
        "/api/v1/files/upload",
        "/api/v1/settings/risk",
        "/api/v1/webhook/confirm",
        "/api/v1/agentos/health",
        "/api/v1/agent/health",
        "/api/v1/agent/runs",
        "/api/v1/agent/definitions",
        "/api/v1/agent/mcp-servers",
        "/api/v1/agent/model-credentials",
        "/api/v1/market-data/historical/{symbol}",
    }

    assert expected_paths <= paths


def test_legacy_routers_are_not_accidentally_exposed(client):
    paths = route_paths(client.app)

    legacy_paths = {
        "/api/v1/tasks",
        "/api/v1/tasks/",
        "/api/v1/journals",
        "/api/v1/journals/",
        "/api/v1/projects",
        "/api/v1/projects/",
        "/api/v1/agents",
        "/api/v1/agents/",
        "/api/v1/analysis",
        "/api/v1/analysis/",
        "/api/v1/rpg/character",
        "/api/v1/dashboard",
        "/api/v1/user/exchanges",
        "/api/exchanges",
    }

    assert paths.isdisjoint(legacy_paths)
