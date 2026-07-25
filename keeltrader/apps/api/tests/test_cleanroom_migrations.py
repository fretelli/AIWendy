from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations" / "versions"


def test_exchange_enum_is_not_created_twice_on_a_clean_database() -> None:
    source = (MIGRATIONS / "010_create_exchange_connections.py").read_text(
        encoding="utf-8"
    )

    assert "from sqlalchemy.dialects.postgresql import ENUM, UUID" in source
    assert "create_type=False" in source
    assert 'sa.Enum("binance"' not in source


def test_bootstrap_migration_imports_only_current_model_packages() -> None:
    source = (MIGRATIONS / "011a_bootstrap_core_tables.py").read_text(
        encoding="utf-8"
    )

    for retired_package in (
        "domain.intervention",
        "domain.knowledge",
        "domain.notification",
        "domain.report",
        "domain.tenant",
    ):
        assert retired_package not in source
    assert "domain.exchange" not in source
    assert "bootstrap_table_names" in source
    assert "Base.metadata.create_all" not in source
    assert "Base.metadata.tables[table_name].create" in source


def test_intervention_enums_reuse_explicit_postgres_types() -> None:
    source = (
        MIGRATIONS / "011_add_exchange_trades_and_interventions.py"
    ).read_text(encoding="utf-8")

    assert source.count("postgresql.ENUM(") == 3
    assert "sa.Enum(" not in source


def test_trading_mode_column_reuses_explicit_postgres_type() -> None:
    source = (MIGRATIONS / "013_add_trading_mode.py").read_text(encoding="utf-8")

    assert "create_type=False" in source
    assert "sa.Enum(" not in source


def test_sensitive_column_comments_tolerate_retired_optional_tables() -> None:
    source = (MIGRATIONS / "033_document_sensitive_columns.py").read_text(
        encoding="utf-8"
    )

    assert "inspector.has_table(table_name)" in source
    assert "inspector.get_columns(table_name)" in source
