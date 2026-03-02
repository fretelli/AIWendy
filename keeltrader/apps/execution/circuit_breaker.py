"""Global circuit breaker — Redis-backed kill switch."""

from __future__ import annotations

import logging
from datetime import datetime

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

CB_KEY = "keeltrader:circuit_breaker"
CB_REASON_KEY = "keeltrader:circuit_breaker:reason"
CB_ACTIVATED_BY_KEY = "keeltrader:circuit_breaker:activated_by"
CB_ACTIVATED_AT_KEY = "keeltrader:circuit_breaker:activated_at"


class CircuitBreaker:
    """Global circuit breaker backed by Redis.

    When active, all execution agents are blocked from placing orders.
    Activated by /kill command or automatic risk triggers.
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def is_active(self) -> bool:
        """Check if circuit breaker is currently active."""
        value = await self._redis.get(CB_KEY)
        return value == "1"

    async def activate(self, reason: str, activated_by: str) -> None:
        """Activate the circuit breaker."""
        pipe = self._redis.pipeline()
        pipe.set(CB_KEY, "1")
        pipe.set(CB_REASON_KEY, reason)
        pipe.set(CB_ACTIVATED_BY_KEY, activated_by)
        pipe.set(CB_ACTIVATED_AT_KEY, datetime.utcnow().isoformat())
        await pipe.execute()
        logger.warning(
            "Circuit breaker ACTIVATED by %s: %s", activated_by, reason
        )

    async def deactivate(self, deactivated_by: str) -> None:
        """Deactivate the circuit breaker."""
        pipe = self._redis.pipeline()
        pipe.delete(CB_KEY, CB_REASON_KEY, CB_ACTIVATED_BY_KEY, CB_ACTIVATED_AT_KEY)
        await pipe.execute()
        logger.info("Circuit breaker DEACTIVATED by %s", deactivated_by)

    async def get_status(self) -> dict:
        """Get full circuit breaker status."""
        pipe = self._redis.pipeline()
        pipe.get(CB_KEY)
        pipe.get(CB_REASON_KEY)
        pipe.get(CB_ACTIVATED_BY_KEY)
        pipe.get(CB_ACTIVATED_AT_KEY)
        active, reason, by, at = await pipe.execute()
        return {
            "active": active == "1",
            "reason": reason or "",
            "activated_by": by or "",
            "activated_at": at or "",
        }
