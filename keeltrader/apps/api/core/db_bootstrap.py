"""Database bootstrap utilities for local development.

The API currently avoids `Base.metadata.create_all()` at startup due to model
import/metadata issues. For day-to-day local/dev usage we still want a
zero-touch experience, so this module provides an idempotent, Postgres-focused
schema bootstrap for the minimal tables needed by auth + trading journal.
"""

from __future__ import annotations

from core.bootstrap.policy import should_auto_init_db
from core.bootstrap.runner import ensure_dev_schema
from core.logging import get_logger

logger = get_logger(__name__)


async def maybe_auto_init_db() -> None:
    """Auto-bootstrap DB schema when enabled."""
    if not should_auto_init_db():
        return

    logger.info("Auto-initializing DB schema (development)")
    await ensure_dev_schema()
    logger.info("DB schema ready")
