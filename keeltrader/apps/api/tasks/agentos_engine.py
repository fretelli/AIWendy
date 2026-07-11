"""Durable Agent Platform worker and compatibility heartbeat."""

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
