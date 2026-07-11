"""Static contract tests for legacy API surfaces and maintenance scripts."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_database_scripts_have_production_guard():
    guarded_scripts = {
        "add_api_keys_columns.py",
        "add_journal_tables.py",
        "bootstrap_projects.py",
        "configure_oneapi.py",
        "create_user_sessions_table.py",
        "init_coaches.py",
        "init_database.py",
        "init_db_simple.py",
        "init_user.py",
        "init_user_simple.py",
        "migrate_to_multi_tenant.py",
        "save_api_key.py",
        "setup_custom_api.py",
    }

    for script_name in guarded_scripts:
        source = (API_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "require_non_production_script" in source, script_name


def test_legacy_scripts_use_shared_path_setup_only():
    for script_path in (API_ROOT / "scripts").glob("*.py"):
        if script_path.name == "_path_setup.py":
            continue

        source = script_path.read_text(encoding="utf-8")
        assert "sys.path" not in source, script_path.name


def test_legacy_routers_are_not_imported_by_main_app():
    source = (API_ROOT / "main.py").read_text(encoding="utf-8")
    legacy_router_names = {
        "agents",
        "analysis",
        "dashboard",
        "exchanges",
        "journals",
        "projects",
        "tasks",
    }

    for router_name in legacy_router_names:
        assert not re.search(rf"from\s+routers\s+import\s+.*\b{router_name}\b", source)
        assert not re.search(rf"from\s+routers\.{router_name}\b", source)
        assert f"include_router({router_name}.router" not in source
        assert f"include_router({router_name}_router" not in source


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
