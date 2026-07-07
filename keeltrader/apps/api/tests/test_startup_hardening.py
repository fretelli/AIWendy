"""Startup hardening regression tests."""

from types import SimpleNamespace

import pytest


def test_sync_db_url_preserves_password(monkeypatch):
    from core import database

    monkeypatch.setattr(
        database.settings,
        "database_url",
        "postgresql+asyncpg://user:secret-pass@db.example:5432/keeltrader",
    )

    assert (
        database.get_db_url()
        == "postgresql+psycopg2://user:secret-pass@db.example:5432/keeltrader"
    )


def test_auto_init_db_ignored_in_production(monkeypatch):
    from core import db_bootstrap
    from core.bootstrap import policy

    monkeypatch.setenv("KEELTRADER_AUTO_INIT_DB", "1")
    monkeypatch.setattr(
        policy,
        "get_settings",
        lambda: SimpleNamespace(environment="production"),
    )

    assert db_bootstrap.should_auto_init_db() is False


def test_auto_init_db_can_run_in_development(monkeypatch):
    from core import db_bootstrap
    from core.bootstrap import policy

    monkeypatch.setenv("KEELTRADER_AUTO_INIT_DB", "1")
    monkeypatch.setattr(
        policy,
        "get_settings",
        lambda: SimpleNamespace(environment="development"),
    )

    assert db_bootstrap.should_auto_init_db() is True


@pytest.mark.asyncio
async def test_dev_schema_skips_non_postgres_database(monkeypatch):
    from core.bootstrap import runner

    class FailingEngine:
        def begin(self):
            raise AssertionError("engine.begin should not be called for non-Postgres DBs")

    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: SimpleNamespace(database_url="sqlite+aiosqlite:///:memory:"),
    )
    monkeypatch.setattr(runner, "engine", FailingEngine())

    await runner.ensure_dev_schema()


@pytest.mark.asyncio
async def test_dev_schema_runs_sections_in_declared_order(monkeypatch):
    from core.bootstrap import runner

    calls: list[str] = []

    async def first(conn):
        calls.append(f"first:{conn}")

    async def second(conn):
        calls.append(f"second:{conn}")

    class FakeConnection:
        async def __aenter__(self):
            return "connection"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeConnection()

    monkeypatch.setattr(
        runner,
        "get_settings",
        lambda: SimpleNamespace(database_url="postgresql+asyncpg://user:pass@db/app"),
    )
    monkeypatch.setattr(runner, "engine", FakeEngine())
    monkeypatch.setattr(runner, "SECTION_RUNNERS", (first, second))

    await runner.ensure_dev_schema()

    assert calls == ["first:connection", "second:connection"]


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

