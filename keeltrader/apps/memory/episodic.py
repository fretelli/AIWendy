"""L1 Episodic Memory — time-indexed event memories stored in Redis.

Episodic memory stores time-ordered records of agent actions, trades,
conversations, and notable events. Think of it as "what happened and when."

For MVP: Redis-backed with JSON serialization.
Future: PostgreSQL `agent_memories` table with time-range indexing.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Redis key prefixes
_PREFIX = "keeltrader:memory:episodic"
_INDEX_PREFIX = "keeltrader:memory:episodic_idx"
_TTL_DAYS = 90  # Episodic memories expire after 90 days


class EpisodicMemory:
    """L1 Episodic Memory — time-series event store."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

    async def store(
        self,
        key: str,
        value: Any,
        agent_id: str,
        user_id: str | None = None,
        importance: float = 0.5,
        expires_in_hours: int | None = None,
    ) -> dict[str, Any]:
        """Store an episodic memory entry.

        Args:
            key: Memory key (descriptive name)
            value: Memory value (JSON-serializable)
            agent_id: Agent storing the memory
            user_id: User context
            importance: 0.0–1.0 importance score
            expires_in_hours: Override default TTL

        Returns:
            The stored memory entry as dict
        """
        entry_id = str(uuid4())
        now = datetime.utcnow()

        entry = {
            "id": entry_id,
            "key": key,
            "value": json.dumps(value) if not isinstance(value, str) else value,
            "agent_id": agent_id,
            "user_id": user_id or "",
            "importance": str(importance),
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
        }

        ttl = (
            expires_in_hours * 3600
            if expires_in_hours
            else _TTL_DAYS * 86400
        )

        r = aioredis.from_url(self._redis_url)
        try:
            pipe = r.pipeline()
            # Store entry
            hash_key = f"{_PREFIX}:{entry_id}"
            pipe.hset(hash_key, mapping=entry)
            pipe.expire(hash_key, ttl)

            # Index by agent+user for retrieval
            scope = f"{agent_id}:{user_id or 'global'}"
            idx_key = f"{_INDEX_PREFIX}:{scope}"
            # Score = timestamp for time-ordered retrieval
            pipe.zadd(idx_key, {entry_id: now.timestamp()})
            pipe.expire(idx_key, _TTL_DAYS * 86400)

            # Index by key name for exact lookup
            key_idx = f"{_PREFIX}:by_key:{scope}:{key}"
            pipe.set(key_idx, entry_id, ex=ttl)

            await pipe.execute()

            logger.debug(
                "Episodic memory stored: %s key=%s agent=%s",
                entry_id, key, agent_id,
            )
            return {**entry, "value": value}

        finally:
            await r.aclose()

    async def search(
        self,
        query: str,
        agent_id: str,
        user_id: str | None = None,
        time_range_days: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search episodic memories by key pattern and time range.

        Args:
            query: Key pattern to search (substring match)
            agent_id: Agent context
            user_id: User context
            time_range_days: Limit to recent N days
            limit: Max results

        Returns:
            List of matching memory entries, newest first
        """
        scope = f"{agent_id}:{user_id or 'global'}"
        idx_key = f"{_INDEX_PREFIX}:{scope}"

        # Time range scoring
        max_score = "+inf"
        min_score = "-inf"
        if time_range_days:
            cutoff = datetime.utcnow() - timedelta(days=time_range_days)
            min_score = str(cutoff.timestamp())

        r = aioredis.from_url(self._redis_url)
        try:
            # Get entry IDs from time-sorted index (newest first)
            entry_ids = await r.zrevrangebyscore(
                idx_key, max_score, min_score, start=0, num=limit * 3
            )

            results: list[dict[str, Any]] = []
            query_lower = query.lower()

            for eid_raw in entry_ids:
                eid = eid_raw.decode() if isinstance(eid_raw, bytes) else eid_raw
                entry_data = await r.hgetall(f"{_PREFIX}:{eid}")
                if not entry_data:
                    continue

                entry = {
                    (k.decode() if isinstance(k, bytes) else k): (
                        v.decode() if isinstance(v, bytes) else v
                    )
                    for k, v in entry_data.items()
                }

                # Substring match on key and value
                if query_lower and query_lower not in entry.get("key", "").lower():
                    # Also check value
                    val_str = entry.get("value", "")
                    if query_lower not in val_str.lower():
                        continue

                # Parse value back from JSON
                try:
                    entry["value"] = json.loads(entry["value"])
                except (json.JSONDecodeError, TypeError):
                    pass

                results.append(entry)
                if len(results) >= limit:
                    break

            # Update last_accessed for returned entries
            if results:
                now = datetime.utcnow().isoformat()
                pipe = r.pipeline()
                for entry in results:
                    pipe.hset(f"{_PREFIX}:{entry['id']}", "last_accessed", now)
                await pipe.execute()

            return results

        finally:
            await r.aclose()

    async def get_by_key(
        self,
        key: str,
        agent_id: str,
        user_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Get a specific episodic memory by exact key."""
        scope = f"{agent_id}:{user_id or 'global'}"
        key_idx = f"{_PREFIX}:by_key:{scope}:{key}"

        r = aioredis.from_url(self._redis_url)
        try:
            entry_id = await r.get(key_idx)
            if not entry_id:
                return None

            eid = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
            entry_data = await r.hgetall(f"{_PREFIX}:{eid}")
            if not entry_data:
                return None

            entry = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in entry_data.items()
            }

            try:
                entry["value"] = json.loads(entry["value"])
            except (json.JSONDecodeError, TypeError):
                pass

            # Update last_accessed
            await r.hset(
                f"{_PREFIX}:{eid}",
                "last_accessed",
                datetime.utcnow().isoformat(),
            )

            return entry

        finally:
            await r.aclose()

    async def forget(
        self,
        key: str,
        agent_id: str,
        user_id: str | None = None,
    ) -> bool:
        """Delete an episodic memory by key.

        Returns True if found and deleted.
        """
        scope = f"{agent_id}:{user_id or 'global'}"
        key_idx = f"{_PREFIX}:by_key:{scope}:{key}"

        r = aioredis.from_url(self._redis_url)
        try:
            entry_id = await r.get(key_idx)
            if not entry_id:
                return False

            eid = entry_id.decode() if isinstance(entry_id, bytes) else entry_id

            pipe = r.pipeline()
            pipe.delete(f"{_PREFIX}:{eid}")
            pipe.delete(key_idx)
            pipe.zrem(f"{_INDEX_PREFIX}:{scope}", eid)
            await pipe.execute()

            logger.debug("Episodic memory forgotten: key=%s agent=%s", key, agent_id)
            return True

        finally:
            await r.aclose()
