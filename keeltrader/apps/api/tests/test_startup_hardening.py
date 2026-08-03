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
            auth_required=True,
            exposure_host="0.0.0.0",
            web_exposure_host="0.0.0.0",
        ),
    )

    with pytest.raises(RuntimeError, match="Security validation failed"):
        main._validate_security_config()


def test_auth_disabled_requires_loopback_exposure(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            environment="production",
            jwt_secret="x" * 64,
            encryption_key="y" * 64,
            auth_required=False,
            exposure_host="0.0.0.0",
            web_exposure_host="127.0.0.1",
        ),
    )

    with pytest.raises(RuntimeError, match="Security validation failed"):
        main._validate_security_config()


def test_auth_disabled_allows_loopback_exposure(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            environment="production",
            jwt_secret="x" * 64,
            encryption_key="y" * 64,
            auth_required=False,
            exposure_host="127.0.0.1",
            web_exposure_host="127.0.0.1",
        ),
    )

    main._validate_security_config()


def test_auth_disabled_rejects_public_web_exposure(monkeypatch):
    import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(
            environment="production",
            jwt_secret="x" * 64,
            encryption_key="y" * 64,
            auth_required=False,
            exposure_host="127.0.0.1",
            web_exposure_host="0.0.0.0",
        ),
    )

    with pytest.raises(RuntimeError, match="Security validation failed"):
        main._validate_security_config()
