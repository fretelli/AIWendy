"""Durable Agent Platform worker."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# The Compose command executes this file directly (not with ``python -m``),
# so Python otherwise exposes only /app/tasks on sys.path.
API_ROOT = str(Path(__file__).resolve().parents[1])
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        from core.model_registry import register_domain_models
        register_domain_models()
        from services.agent_platform.runtime import worker_loop
        from services.agent_platform.dossier import dossier_scheduler_loop, dossier_worker_loop

        async def heartbeat_loop() -> None:
            while True:
                payload = {
                    "status": "running",
                    "service": "agent-platform-worker",
                    "mode": "durable-agent-platform-v2",
                    "timestamp": datetime.utcnow().isoformat(),
                    "tushare_token_required": False,
                }
                await r.set("keeltrader:agent-platform:heartbeat", json.dumps(payload), ex=75)
                await asyncio.sleep(30)

        async with asyncio.TaskGroup() as group:
            group.create_task(worker_loop(), name="run-worker")
            group.create_task(dossier_worker_loop(), name="dossier-worker")
            group.create_task(dossier_scheduler_loop(), name="dossier-scheduler")
            group.create_task(heartbeat_loop(), name="heartbeat")
    except* Exception as errors:
        logger.exception("agent_worker_taskgroup_failed", errors=[str(error) for error in errors.exceptions])
        raise
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
