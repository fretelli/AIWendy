from pathlib import Path
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers.agent_platform import BUILTIN_TOOLS, DEFAULT_AGENT_NAME, DEFAULT_AGENT_ROLE, dump
from services.agent_platform import network
from services.agent_platform.runtime import default_plan, redact_sensitive
from services.agent_platform.learning import LearningBridge
from services.agent_platform.knowledge import search_snapshot


def test_agent_platform_exposes_no_execution_or_trading_tools():
    forbidden = {"place_order", "cancel_order", "execute_trade", "ghost_trade", "run_code", "bash"}
    assert BUILTIN_TOOLS.isdisjoint(forbidden)
    assert all("order" not in name and "trade" not in name for name in BUILTIN_TOOLS)


def test_default_plan_is_research_only():
    plan = default_plan("analyze ACME", ["query_research_reports"])
    assert plan[0]["tool"] == "query_research_reports"
    assert {step["role"] for step in plan} >= {"red_team", "risk_reviewer", "coordinator"}


def test_keeltrader_is_the_single_product_level_agent():
    router = Path(__file__).resolve().parents[1] / "routers/agent_platform.py"
    source = router.read_text(encoding="utf-8")
    assert DEFAULT_AGENT_NAME == "KeelTrader"
    assert DEFAULT_AGENT_ROLE == "workspace_assistant"
    assert "AgentDefinition.is_default.is_(True)" in source
    assert "_ensure_default_agent(session, user, preferred_profile=item)" in source
    assert 'name="基本面研究员"' not in source


def test_session_creation_commits_before_returning():
    router = Path(__file__).resolve().parents[1] / "routers/agent_platform.py"
    source = router.read_text(encoding="utf-8")
    start = source.index('@router.post("/sessions")')
    end = source.index('@router.patch("/sessions/{session_id}")')
    create_session_source = source[start:end]
    assert "await session.commit()" in create_session_source
    assert create_session_source.index("await session.commit()") < create_session_source.index("return dump(item)")


def test_session_deletion_is_owned_safe_and_committed():
    router = Path(__file__).resolve().parents[1] / "routers/agent_platform.py"
    source = router.read_text(encoding="utf-8")
    start = source.index('@router.delete("/sessions/{session_id}")')
    end = source.index('@router.post("/sessions/{session_id}/messages")')
    delete_source = source[start:end]
    assert "item.user_id != user.id" in delete_source
    assert "AgentRun.status.not_in(TERMINAL)" in delete_source
    assert "await session.delete(item)" in delete_source
    assert "await session.commit()" in delete_source


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


def test_learning_bridge_uses_sanitized_snapshot_and_one_file_per_feedback(tmp_path):
    bridge = LearningBridge(tmp_path)
    assert bridge.snapshot()["state"] == "not_configured"
    (tmp_path / "snapshot.json").write_text(
        '{"generated_at":"2026-07-25T00:00:00Z","memories":[{"memory_id":"m1","content":"偏好具体证据"}]}',
        encoding="utf-8",
    )
    snapshot = bridge.snapshot()
    assert snapshot["available"] is True
    assert snapshot["memories"][0]["content"] == "偏好具体证据"
    result = bridge.record_feedback({
        "event_type": "preference", "summary": "以后都给出反例", "conversation_id": "c1",
        "task_id": "r1", "message_id": "m1", "user_id": "u1",
    })
    event = json.loads(next((tmp_path / "inbox").glob("*.json")).read_text(encoding="utf-8"))
    assert result["accepted"] is True
    assert event["entry_type"] == "keeltrader"
    assert "assistant_content" not in event


def test_general_knowledge_search_is_read_only_and_source_bounded(tmp_path):
    snapshot = tmp_path / "knowledge.json"
    snapshot.write_text(json.dumps({"document_count": 1, "chunks": [{
        "title": "服务入口", "source": "docs/services.md", "content": "KeelTrader 通过 Traefik 提供网页入口。",
    }]}), encoding="utf-8")
    result = search_snapshot(snapshot, "KeelTrader 网页入口")
    assert result["items"][0]["source"] == "docs/services.md"
    assert set(result["items"][0]) == {"title", "source", "content", "score"}


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


def test_workspace_scope_is_additive_and_cannot_grant_execution():
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/039_agent_workspace_scope.py"
    source = migration.read_text(encoding="utf-8")
    runtime = (Path(__file__).resolve().parents[1] / "services/agent_platform/runtime.py").read_text(encoding="utf-8")
    assert 'revision = "039"' in source and 'down_revision = "038"' in source
    assert "'general','research','content','ops'" in source
    assert 'chat.workspace_scope != "research"' in runtime
    assert "do not execute shell commands, deployments, restarts, secret changes, or remote writes" in runtime


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
    assert 'status.in_({"queued", "retry", "running"})' in dossier
    report_kb = (Path(__file__).resolve().parents[1] / "services/agent_platform/report_kb.py").read_text(encoding="utf-8")
    assert "return await self.recent_reports(limit=limit)" not in report_kb


def test_company_memory_attachments_and_self_host_privacy_contracts():
    runtime = (Path(__file__).resolve().parents[1] / "services/agent_platform/runtime.py").read_text(encoding="utf-8")
    router = (Path(__file__).resolve().parents[1] / "routers/agent_platform.py").read_text(encoding="utf-8")
    assert "_company_memory_context" in runtime
    assert 'key = f"company:{chat.company_code}:thesis"' in runtime
    assert "attachment_ids" in router and "UploadedFile.user_id == user.id" in router


def test_worker_registers_all_models_and_runtime_reliability_migration_exists():
    worker = (Path(__file__).resolve().parents[1] / "tasks/agent_platform_worker.py").read_text(encoding="utf-8")
    assert "register_domain_models()" in worker
    assert "asyncio.TaskGroup()" in worker
    migration = Path(__file__).resolve().parents[3] / "migrations/versions/027_agent_runtime_reliability.py"
    source = migration.read_text(encoding="utf-8")
    assert 'revision = "027"' in source
    assert "agent_background_jobs" in source
    assert "uq_agent_platform_run_idempotency" in source


def test_model_registry_configures_all_mappers():
    from core.model_registry import register_domain_models

    register_domain_models()
