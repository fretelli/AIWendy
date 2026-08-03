"""Publication-aware cache keys and background warming for market snapshots."""

from __future__ import annotations

import asyncio
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy.exc import DBAPIError
from core.cache_service import CacheService, get_cache_service
from core.logging import get_logger
from services.agent_platform.capabilities import capability_version
from services.agent_platform.publication_status import publication_version
from services.agent_platform.tushare import TushareReadService

logger = get_logger(__name__)


def market_cache_key(key: str) -> str:
    return f"markets:v5:{publication_version()}:{capability_version()}:{key}"


def market_last_good_key(key: str) -> str:
    return f"markets:last-good:{key}"


async def prewarm_market_snapshots(cache: CacheService | None = None) -> dict[str, str]:
    cache = cache or get_cache_service()
    reader = TushareReadService(None)
    definitions = (
        ("valuation-board:v4", reader.valuation_snapshot, 600),
        ("correlations:v2:60", lambda: reader.correlation_snapshot(60), 600),
        ("factors:kt_factor_v1:materialized", reader.factor_snapshot, 900),
    )
    missing = []
    for key, loader, ttl in definitions:
        if not isinstance(await cache.get_async(market_cache_key(key)), dict):
            missing.append((key, loader, ttl))
    if not missing:
        return {key: "warm" for key, *_ in definitions}
    payloads = await asyncio.gather(*(loader() for _, loader, _ in missing))
    states: dict[str, str] = {}
    for (key, _loader, ttl), payload in zip(missing, payloads):
        await cache.set_async(market_cache_key(key), payload, ttl=ttl)
        metadata: Any = payload.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("status") != "unavailable":
            await cache.set_async(market_last_good_key(key), payload, ttl=604800)
        states[key] = str(metadata.get("status") if isinstance(metadata, dict) else "available")
    logger.info("market_snapshot_cache_prewarmed", states=states,
                publication=publication_version(), capabilities=capability_version())
    return states


async def market_snapshot_prewarm_loop(interval_seconds: int = 60) -> None:
    while True:
        try:
            await prewarm_market_snapshots()
        except (DBAPIError, RedisError, OSError, RuntimeError, TimeoutError) as exc:
            logger.warning("market_snapshot_cache_prewarm_failed", error=str(exc))
        await asyncio.sleep(interval_seconds)
