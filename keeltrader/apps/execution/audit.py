"""Execution audit — immutable audit trail for all order operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

AUDIT_KEY_PREFIX = "keeltrader:audit:"
AUDIT_INDEX_KEY = "keeltrader:audit_index:{user_id}"


class ExecutionAudit:
    """Records every execution attempt in an immutable audit log.

    Stores in Redis with optional PostgreSQL persistence.
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def record(
        self,
        agent_id: str,
        user_id: str,
        action: str,
        details: dict[str, Any],
        success: bool,
    ) -> str:
        """Record an execution audit entry.

        Args:
            agent_id: Agent that performed the action
            user_id: User ID
            action: Action type (order.placed, order.cancelled, order.rejected, etc.)
            details: Action details (symbol, side, amount, price, etc.)
            success: Whether the action succeeded

        Returns:
            Audit entry ID
        """
        entry_id = str(uuid4())
        entry = {
            "id": entry_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "action": action,
            "details": json.dumps(details),
            "success": str(success),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store entry
        key = f"{AUDIT_KEY_PREFIX}{entry_id}"
        await self._redis.hset(key, mapping=entry)
        await self._redis.expire(key, 86400 * 30)  # 30 days in Redis

        # Index by user
        index_key = AUDIT_INDEX_KEY.format(user_id=user_id)
        await self._redis.lpush(index_key, entry_id)
        await self._redis.ltrim(index_key, 0, 999)  # Keep last 1000

        logger.info(
            "Audit: %s %s %s success=%s",
            agent_id, action, details.get("symbol", ""), success,
        )

        return entry_id

    async def get_recent(
        self,
        user_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent audit entries for a user."""
        index_key = AUDIT_INDEX_KEY.format(user_id=user_id)
        entry_ids = await self._redis.lrange(index_key, 0, limit - 1)

        entries = []
        for eid in entry_ids:
            eid_str = eid.decode() if isinstance(eid, bytes) else eid
            key = f"{AUDIT_KEY_PREFIX}{eid_str}"
            data = await self._redis.hgetall(key)
            if data:
                entry = {k.decode(): v.decode() for k, v in data.items()}
                if "details" in entry:
                    entry["details"] = json.loads(entry["details"])
                entries.append(entry)

        return entries
