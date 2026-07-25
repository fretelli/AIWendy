"""Async database configuration and session management."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

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
        pool_timeout=settings.database_pool_timeout_seconds,
        pool_recycle=1800,
        pool_pre_ping=True,  # Check connection health
        connect_args={"server_settings": {
            "application_name": settings.database_application_name,
            "idle_in_transaction_session_timeout": "60000",
        }} if "+asyncpg" in settings.database_url else {},
    )

# Create session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Create declarative base
Base = declarative_base()


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for worker and service database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


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
