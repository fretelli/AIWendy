"""Bootstrap database: create enums with correct case, then all tables, then stamp alembic.

Workaround for:
1. Broken alembic migration chain (missing projects table in 007)
2. Enum case mismatch (SQLAlchemy creates_all uses NAME, seed data uses value)
"""
import asyncio
import os
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine


def bootstrap_sync(db_url):
    """Use sync engine for DDL operations."""
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    engine = create_engine(sync_url)

    with engine.begin() as conn:
        # Check if tables already exist
        result = conn.execute(text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
        ))
        if result.scalar():
            print("[bootstrap] Tables already exist, skipping")
            engine.dispose()
            return

    with engine.begin() as conn:
        # Extensions
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        try:
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        except Exception:
            pass

        # Pre-create enum types with lowercase values (matching seed data)
        # This prevents create_all from creating them with UPPERCASE names
        enums = {
            "subscriptiontier": "('free', 'pro', 'elite', 'enterprise')",
            "moodtype": "('very_negative', 'negative', 'neutral', 'positive', 'very_positive')",
            "coachstyle": "('empathetic', 'disciplined', 'analytical', 'motivational', 'socratic')",
            "exchangetype": "('binance', 'okx', 'bybit', 'coinbase', 'kraken')",
            "interventionaction": "('notify', 'warn', 'block', 'force_close', 'reduce_position', 'cooldown')",
            "interventionreason": "('max_loss', 'revenge_trading', 'overtrading', 'position_size', 'risk_limit', 'emotional_state', 'pattern_detected', 'manual')",
            "patterntype": "('revenge_trading', 'overtrading', 'fomo', 'loss_chasing', 'tilt', 'consistent_profit', 'disciplined_exit', 'risk_management')",
        }
        for name, values in enums.items():
            conn.execute(text(f"DO $$ BEGIN CREATE TYPE {name} AS ENUM {values}; EXCEPTION WHEN duplicate_object THEN NULL; END $$"))
        print("[bootstrap] Enum types created with lowercase values")

    # Import models and create all tables
    from core.database import Base
    try:
        from domain.analysis import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.coach import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.exchange import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.intervention import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.journal import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.knowledge import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.notification import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.project import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.report import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.tenant import models  # noqa: F401
    except Exception:
        pass
    try:
        from domain.user import models  # noqa: F401
    except Exception:
        pass

    Base.metadata.create_all(bind=engine)
    print("[bootstrap] All tables created")

    # Stamp alembic
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('011a')"))
    print("[bootstrap] Stamped alembic to 011a")

    engine.dispose()


if __name__ == "__main__":
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("[bootstrap] No DATABASE_URL, skipping")
        sys.exit(0)
    bootstrap_sync(db_url)
