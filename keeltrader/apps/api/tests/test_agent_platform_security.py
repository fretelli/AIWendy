from pathlib import Path
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
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/020_agent_platform.py"
    source = migration.read_text(encoding="utf-8")
    assert 'for statement in ddl.split(";")' in source


def test_agent_worker_bootstrap_adds_api_root_to_sys_path():
    worker = Path(__file__).resolve().parents[1] / "tasks/agent_platform_worker.py"
    source = worker.read_text(encoding="utf-8")
    assert "Path(__file__).resolve().parents[1]" in source
    assert "sys.path.insert(0, API_ROOT)" in source


def test_conversational_migration_uses_split_asyncpg_statements():
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/023_conversational_agent_workspace.py"
    source = migration.read_text(encoding="utf-8")
    assert 'revision = "023"' in source
    assert "for statement in statements" in source


def test_interaction_mode_migration_is_additive_and_research_safe():
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/024_agent_interaction_modes.py"
    source = migration.read_text(encoding="utf-8")
    assert 'revision = "024"' in source
    assert 'down_revision = "023"' in source
    assert "interaction_mode" in source
    assert "'ask', 'research', 'plan'" in source


def test_ask_and_plan_modes_use_the_no_tool_runtime_path():
    runtime = Path(__file__).resolve().parents[1] / "services/agent_platform/runtime.py"
    source = runtime.read_text(encoding="utf-8")
    assert 'run.interaction_mode in {"ask", "plan"}' in source
    assert "await _execute_direct_mode" in source
    assert "Do not call or imply use of tools" in source


def test_managed_model_and_watchlist_migration_is_private_by_default():
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/025_fundamental_watchlist_foundation.py"
    source = migration.read_text(encoding="utf-8")
    assert 'revision = "025"' in source
    assert 'down_revision = "024"' in source
    assert "agent_company_watchlist" in source
    config = (Path(__file__).resolve().parents[1] / "config.py").read_text(encoding="utf-8")
    assert 'agent_managed_api_key: Optional[str] = None' in config
    assert "joyeeassets.com" not in config


def test_dossier_engine_is_watchlist_only_and_does_not_use_unrelated_reports():
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/026_fundamental_dossiers.py"
    assert 'revision = "026"' in migration.read_text(encoding="utf-8")
    dossier = (Path(__file__).resolve().parents[1] / "services/agent_platform/dossier.py").read_text(encoding="utf-8")
    assert "Only companies in 我的自选 can be refreshed" in dossier
    assert "refresh_enabled.is_(True)" in dossier
    report_kb = (Path(__file__).resolve().parents[1] / "services/agent_platform/report_kb.py").read_text(encoding="utf-8")
    assert "return await self.recent_reports(limit=limit)" not in report_kb


def test_company_memory_attachments_and_self_host_privacy_contracts():
    runtime = (Path(__file__).resolve().parents[1] / "services/agent_platform/runtime.py").read_text(encoding="utf-8")
    router = (Path(__file__).resolve().parents[1] / "routers/agent_platform.py").read_text(encoding="utf-8")
    assert "_company_memory_context" in runtime
    assert 'key = f"company:{chat.company_code}:thesis"' in runtime
    assert "attachment_ids" in router and "UploadedFile.user_id == user.id" in router
