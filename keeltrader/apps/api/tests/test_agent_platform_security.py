from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers.agent_platform import BUILTIN_TOOLS, dump
from services.agent_platform import network
from services.agent_platform.runtime import default_plan, redact_sensitive


def test_agent_platform_exposes_no_execution_or_trading_tools():
    forbidden = {"place_order", "cancel_order", "execute_trade", "ghost_trade", "run_code", "bash"}
    assert BUILTIN_TOOLS.isdisjoint(forbidden)
    assert all("order" not in name and "trade" not in name for name in BUILTIN_TOOLS)


def test_default_plan_is_research_only():
    plan = default_plan("analyze ACME", ["query_research_reports"])
    assert plan[0]["tool"] == "query_research_reports"
    assert {step["role"] for step in plan} >= {"red_team", "risk_reviewer", "coordinator"}


def test_secret_fields_are_never_serialized():
    table = SimpleNamespace(columns=[SimpleNamespace(name="name"), SimpleNamespace(name="api_key_encrypted")])
    model = SimpleNamespace(__table__=table, name="demo", api_key_encrypted="ciphertext")
    assert dump(model, secret_fields={"api_key_encrypted"}) == {"name": "demo"}


def test_private_mcp_destinations_are_blocked(monkeypatch):
    monkeypatch.setattr(network.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(HTTPException) as exc:
        network.validate_external_https_url("https://mcp.example.com")
    assert exc.value.status_code == 400


def test_mcp_rejects_credentials_in_url():
    with pytest.raises(HTTPException):
        network.validate_external_https_url("https://user:secret@example.com")


def test_sensitive_tool_results_are_redacted_before_persistence():
    assert redact_sensitive({"api_key": "secret", "nested": {"Authorization": "Bearer x"}, "ok": 1}) == {
        "api_key": "<redacted>", "nested": {"Authorization": "<redacted>"}, "ok": 1,
    }


def test_agent_platform_migration_splits_asyncpg_ddl_commands():
    from pathlib import Path

    migration = Path(__file__).resolve().parents[3] / "migrations/versions/020_agent_platform.py"
    source = migration.read_text(encoding="utf-8")
    assert 'for statement in ddl.split(";")' in source


def test_agent_worker_bootstrap_adds_api_root_to_sys_path():
    from pathlib import Path

    worker = Path(__file__).resolve().parents[1] / "tasks/agentos_engine.py"
    source = worker.read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[1]" in source
    assert "sys.path.insert(0, API_ROOT)" in source
