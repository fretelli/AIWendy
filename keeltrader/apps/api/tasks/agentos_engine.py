"""Durable Agent Platform worker and compatibility heartbeat."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime

import redis.asyncio as aioredis


async def main() -> None:
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        from services.agent_platform.runtime import worker_loop

        worker = asyncio.create_task(worker_loop())
        while True:
            payload = {
                "status": "running",
                "service": "agentos-engine",
                "mode": "durable-agent-platform-v1",
                "timestamp": datetime.utcnow().isoformat(),
                "tushare_token_required": False,
            }
            await r.set("keeltrader:agentos:heartbeat", json.dumps(payload), ex=75)
            await asyncio.sleep(30)
    finally:
        if "worker" in locals():
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
