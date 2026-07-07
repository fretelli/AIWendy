"""Runner for development database schema bootstrap."""

from __future__ import annotations

from config import get_settings
from core.database import engine
from core.logging import get_logger

from .registry import SECTION_RUNNERS

logger = get_logger(__name__)


async def ensure_dev_schema() -> None:
    """Ensure required tables exist (idempotent)."""
    settings = get_settings()

    if not settings.database_url.lower().startswith("postgres"):
        logger.info(
            "Skipping dev DB bootstrap for non-Postgres database",
            database_url=settings.database_url,
        )
        return

    async with engine.begin() as conn:
        for run_section in SECTION_RUNNERS:
            await run_section(conn)
