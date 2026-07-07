"""Route contract tests for the active production API surface."""


def test_active_route_prefixes_are_mounted(client):
    paths = {route.path for route in client.app.routes}

    expected_paths = {
        "/api/health",
        "/api/health/ready",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/users/me",
        "/api/v1/chat/send",
        "/api/v1/settings/risk",
        "/api/v1/webhook/confirm",
        "/api/v1/rpg/character",
        "/api/v1/agentos/health",
        "/api/v1/market-data/historical/{symbol}",
    }

    assert expected_paths <= paths


def test_legacy_routers_are_not_accidentally_exposed(client):
    paths = {route.path for route in client.app.routes}

    legacy_paths = {
        "/api/v1/tasks",
        "/api/v1/tasks/",
        "/api/v1/journals",
        "/api/v1/journals/",
        "/api/v1/projects",
        "/api/v1/projects/",
        "/api/v1/files",
        "/api/v1/files/",
        "/api/v1/agents",
        "/api/v1/agents/",
        "/api/v1/analysis",
        "/api/v1/analysis/",
        "/api/v1/dashboard",
        "/api/v1/user/exchanges",
        "/api/exchanges",
    }

    assert paths.isdisjoint(legacy_paths)
