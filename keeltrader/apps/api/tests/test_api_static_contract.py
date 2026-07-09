"""Static contract tests for legacy API surfaces and maintenance scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_agent_routes_do_not_default_to_shared_user_id():
    source = (API_ROOT / "routers" / "agents.py").read_text(encoding="utf-8")

    assert 'user_id: str = "default"' not in source


def test_legacy_database_scripts_have_production_guard():
    guarded_scripts = {
        "bootstrap_projects.py",
        "init_database.py",
        "init_db_simple.py",
        "migrate_to_multi_tenant.py",
        "create_user_sessions_table.py",
        "add_api_keys_columns.py",
        "add_journal_tables.py",
    }

    for script_name in guarded_scripts:
        source = (API_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "require_non_production_script" in source, script_name


def _load_script_guard():
    guard_path = API_ROOT / "scripts" / "_script_guard.py"
    spec = importlib.util.spec_from_file_location("script_guard_for_test", guard_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_legacy_script_guard_blocks_production_without_explicit_override(monkeypatch):
    guard = _load_script_guard()

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("KEELTRADER_ALLOW_LEGACY_SCRIPT", raising=False)

    with pytest.raises(SystemExit) as exc:
        guard.require_non_production_script("init_database.py")

    assert exc.value.code == 2


def test_legacy_script_guard_allows_explicit_production_override(monkeypatch):
    guard = _load_script_guard()

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("KEELTRADER_ALLOW_LEGACY_SCRIPT", "1")

    guard.require_non_production_script("init_database.py")
