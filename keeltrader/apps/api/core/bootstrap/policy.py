"""Policy for development database auto-initialization."""

from __future__ import annotations

import os

from config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)

_TRUTHY = {"1", "true", "yes", "y", "on"}


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUTHY


def should_auto_init_db() -> bool:
    """Return True when we should auto-bootstrap the DB schema."""
    settings = get_settings()
    environment = settings.environment.lower()

    if environment in {"production", "prod"}:
        if _is_truthy(os.getenv("KEELTRADER_AUTO_INIT_DB")):
            logger.warning("Ignoring KEELTRADER_AUTO_INIT_DB in production")
        return False

    env_value = os.getenv("KEELTRADER_AUTO_INIT_DB")
    if env_value is not None:
        return _is_truthy(env_value)

    # Safety: only auto-init in development by default.
    return environment == "development"
