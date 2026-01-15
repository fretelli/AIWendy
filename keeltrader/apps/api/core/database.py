"""Database configuration and session management."""

from __future__ import annotations

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Determine if we're using SQLite (which doesn't support pool_size/max_overflow)
_is_sqlite = "sqlite" in settings.database_url.lower()

# Create async engine (for async endpoints)
if _is_sqlite:
    # SQLite doesn't support pool_size and max_overflow
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        connect_args={"check_same_thread": False},  # Allow SQLite to be used across threads
    )
else:
    # PostgreSQL and other databases support connection pooling
    engine = create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # Check connection health
    )

# Create session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ---------- Sync engine/session (for legacy sync endpoints & scripts) ----------


def get_db_url() -> str:
    """Return a synchronous SQLAlchemy DB URL derived from settings.database_url."""
    url = make_url(settings.database_url)

    # Convert common async drivers to their sync equivalents
    if url.drivername.endswith("+asyncpg"):
        url = url.set(drivername=url.drivername.replace("+asyncpg", "+psycopg2"))
    elif url.drivername.endswith("+aiosqlite"):
        url = url.set(drivername=url.drivername.replace("+aiosqlite", ""))

    return str(url)


_sync_db_url = get_db_url()
_sync_engine_kwargs: dict = {
    "echo": settings.database_echo,
    "pool_pre_ping": True,
}
if not _sync_db_url.startswith("sqlite"):
    _sync_engine_kwargs.update(
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )

sync_engine = create_engine(_sync_db_url, **_sync_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: get a synchronous DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create declarative base
Base = declarative_base()


async def init_database() -> None:
    """Initialize database (create tables if needed)."""
    try:
        # Import all models to register them with Base
        from sqlalchemy import text

        from domain.analysis import models as analysis_models  # noqa
        from domain.coach import models as coach_models  # noqa
        from domain.journal import models as journal_models  # noqa
        from domain.user import models as user_models  # noqa

        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")

            # Run migrations for existing tables (add missing columns)
            logger.info("Running database migrations...")
            migrations = [
                # Add missing columns to chat_messages table
                "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS message_metadata JSON;",
                "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS detected_emotions JSON;",
                "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS detected_patterns JSON;",
            ]

            for migration_sql in migrations:
                try:
                    await conn.execute(text(migration_sql))
                except Exception as migration_error:
                    logger.warning(f"Migration warning: {str(migration_error)}")
                    # Continue with other migrations even if one fails

            logger.info("Database migrations completed")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class DatabaseMixin:
    """Mixin to add database session to classes."""

    def __init__(self, session: AsyncSession):
        self.session = session
