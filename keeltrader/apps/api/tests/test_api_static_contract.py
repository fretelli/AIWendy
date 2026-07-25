"""Static contract tests for legacy API surfaces and maintenance scripts."""

from __future__ import annotations

import re
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_contains_no_schema_bootstrap_modules():
    assert not list((API_ROOT / "core" / "bootstrap").glob("**/*.py"))
    assert not (API_ROOT / "core" / "db_bootstrap.py").exists()
    assert sorted(path.name for path in (API_ROOT / "scripts").iterdir()) == [
        "docker_start.sh"
    ]


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


def test_legacy_runtime_directories_are_removed():
    for name in ("analysis", "coach", "exchange", "journal", "project", "rpg"):
        assert not list((API_ROOT / "domain" / name).glob("**/*.py"))
