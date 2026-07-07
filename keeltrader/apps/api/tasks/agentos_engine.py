"""Lightweight AgentOS engine heartbeat.

The v1 workflows are executed through API/chat tools. This process provides a
separate supervised service slot and heartbeat so future event-stream agents can
be enabled without changing deployment topology.
"""

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
        while True:
            payload = {
                "status": "running",
                "service": "agentos-engine",
                "mode": "workflow-heartbeat-v1",
                "timestamp": datetime.utcnow().isoformat(),
                "tushare_token_required": False,
            }
            await r.set("keeltrader:agentos:heartbeat", json.dumps(payload), ex=75)
            await asyncio.sleep(30)
    finally:
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
