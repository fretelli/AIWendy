"""Startup hardening regression tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_application_startup_never_mutates_schema() -> None:
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert "create_all" not in source
    assert "maybe_auto_init_db" not in source


def test_container_startup_uses_alembic_only() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "docker_start.sh"
    ).read_text(encoding="utf-8")
    assert "alembic" in source
    assert "KEELTRADER_RUN_MIGRATIONS" in source
    assert "init_db_simple" not in source
    assert "bootstrap_projects" not in source


def test_production_requires_encryption_key(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            environment="production",
            jwt_secret="x" * 64,
            encryption_key=None,
        ),
    )

    with pytest.raises(RuntimeError, match="Security validation failed"):
        main._validate_security_config()
