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
        "/api/v1/files/upload",
        "/api/v1/agent/health",
        "/api/v1/agent/runs",
        "/api/v1/agent/definitions",
        "/api/v1/agent/mcp-servers",
        "/api/v1/agent/model-credentials",
        "/api/v1/agent/sessions",
        "/api/v1/agent/sessions/{session_id}",
        "/api/v1/agent/sessions/{session_id}/messages",
        "/api/v1/agent/sessions/{session_id}/timeline",
        "/api/v1/agent/sessions/{session_id}/compact",
        "/api/v1/agent/sessions/{session_id}/stop",
        "/api/v1/agent/companies",
        "/api/v1/agent/watchlist",
        "/api/v1/agent/watchlist/{company_code}",
        "/api/v1/agent/holders/search",
        "/api/v1/agent/holder-watchlist",
        "/api/v1/agent/holder-watchlist/{watch_id}",
        "/api/v1/agent/holder-watchlist/{watch_id}/refresh",
        "/api/v1/agent/holders/{watch_id}/positions",
        "/api/v1/agent/holder-events",
        "/api/v1/agent/holder-events/read",
        "/api/v1/agent/context-snapshots",
        "/api/v1/agent/search",
        "/api/v1/agent/knowledge/search",
        "/api/v1/agent/dossiers/{company_code}",
        "/api/v1/agent/dossiers/{company_code}/refresh",
        "/api/v1/research-cloud/connection",
        "/api/v1/research-cloud/search",
        "/api/v1/markets/macro/series",
        "/api/v1/markets/data-status",
        "/api/v1/markets/capabilities",
        "/api/v1/markets/capital",
        "/api/v1/markets/valuation-board",
        "/api/v1/markets/valuation/history",
        "/api/v1/markets/valuation/held-industries",
        "/api/v1/markets/correlations",
        "/api/v1/markets/correlations/history",
        "/api/v1/markets/factors",
        "/api/v1/markets/factors/history",
        "/api/v1/markets/macro/series/{key}",
        "/api/v1/markets/futures/{code}/underlying",
        "/api/v1/markets/options/{code}/underlying",
        "/api/v1/markets/underlyings/{relationship}/{code}/series",
    }

    assert expected_paths <= paths


def test_macro_history_position_window_is_an_explicit_api_contract(client):
    operation = client.app.openapi()["paths"]["/api/v1/markets/macro/series/{key}"]["get"]
    parameter = next(item for item in operation["parameters"] if item["name"] == "history_window")

    assert parameter["schema"]["default"] == "10Y"
    assert parameter["schema"]["enum"] == ["5Y", "10Y", "20Y", "ALL"]


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
        "/api/v1/settings/exchanges",
        "/api/v1/settings/risk",
        "/api/v1/settings/push",
        "/api/exchanges",
        "/api/v1/chat/send",
        "/api/v1/webhook/confirm",
        "/api/v1/agentos/health",
        "/api/v1/agent/theses",
        "/api/v1/agent/theses/{thesis_id}",
        "/api/v1/agent/theses/{thesis_id}/evidence",
        "/api/v1/agent/events",
        "/api/v1/agent/events/read",
        "/api/v1/agent/calendar",
        "/api/v1/market-data/historical/{symbol}",
        "/api/v1/market-data/real-time/{symbol}",
        "/api/v1/market-data/ws/{symbol}",
        "/api/v1/users/me/api-keys",
        "/api/v1/users/me/api-keys/{provider}",
    }

    assert paths.isdisjoint(legacy_paths)
