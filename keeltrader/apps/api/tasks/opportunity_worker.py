"""Isolated materializer for the unified opportunity center."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

API_ROOT = str(Path(__file__).resolve().parents[1])
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    redis = aioredis.from_url(redis_url)
    from core.model_registry import register_domain_models

    register_domain_models()
    from services.agent_platform.opportunities import opportunity_worker_loop

    async def heartbeat_loop() -> None:
        while True:
            payload = {
                "status": "running",
                "service": "opportunity-worker",
                "mode": "deterministic-snapshot-materializer-v1",
                "timestamp": datetime.now(UTC).isoformat(),
                "refresh_seconds": int(os.environ.get("OPPORTUNITY_REFRESH_SECONDS", "300")),
            }
            await redis.set("keeltrader:opportunity:heartbeat", json.dumps(payload), ex=75)
            await asyncio.sleep(30)

    try:
        async with asyncio.TaskGroup() as group:
            group.create_task(opportunity_worker_loop(), name="opportunity-materializer")
            group.create_task(heartbeat_loop(), name="opportunity-heartbeat")
    except* Exception as errors:
        logger.exception("opportunity_worker_taskgroup_failed", errors=[str(error) for error in errors.exceptions])
        raise
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
