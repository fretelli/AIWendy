"""Redis Streams based event bus for the KeelTrader event engine."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator
from uuid import UUID

import redis.asyncio as aioredis

from .event_types import Event, EventType

logger = logging.getLogger(__name__)

# Redis Stream key
STREAM_KEY = "keeltrader:events"
# Consumer group for agent processing
CONSUMER_GROUP = "agent-processors"
# Max stream length (auto-trim)
MAX_STREAM_LENGTH = 10000


class EventBus:
    """Redis Streams based event bus.

    Provides pub/sub semantics with persistence and consumer groups
    for reliable event delivery to agents.
    """

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        self._redis = aioredis.from_url(
            self._redis_url,
            decode_responses=True,
        )
        # Create consumer group if not exists
        try:
            await self._redis.xgroup_create(
                STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True
            )
            logger.info("Created consumer group: %s", CONSUMER_GROUP)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                pass  # Group already exists
            else:
                raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    @property
    def redis(self) -> aioredis.Redis:
        if self._redis is None:
            raise RuntimeError("EventBus not connected. Call connect() first.")
        return self._redis

    async def emit(self, event: Event) -> str:
        """Emit an event to the stream.

        Returns the Redis stream message ID.
        """
        data = {
            "id": str(event.id),
            "type": event.type.value,
            "source": event.source,
            "user_id": str(event.user_id) if event.user_id else "",
            "agent_id": event.agent_id or "",
            "payload": json.dumps(event.payload, default=str),
            "timestamp": event.timestamp.isoformat(),
            "correlation_id": str(event.correlation_id),
            "causation_id": str(event.causation_id) if event.causation_id else "",
        }

        msg_id = await self.redis.xadd(
            STREAM_KEY, data, maxlen=MAX_STREAM_LENGTH, approximate=True
        )
        logger.debug("Event emitted: %s [%s] -> %s", event.type.value, event.source, msg_id)
        return msg_id

    async def read_new(
        self,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, Event]]:
        """Read new events from the stream using consumer group.

        Returns list of (message_id, Event) tuples.
        """
        results = await self.redis.xreadgroup(
            CONSUMER_GROUP,
            consumer_name,
            {STREAM_KEY: ">"},
            count=count,
            block=block_ms,
        )

        events = []
        if results:
            for stream_name, messages in results:
                for msg_id, data in messages:
                    try:
                        event = Event(
                            id=UUID(data["id"]),
                            type=EventType(data["type"]),
                            source=data["source"],
                            user_id=UUID(data["user_id"]) if data.get("user_id") else None,
                            agent_id=data.get("agent_id") or None,
                            payload=json.loads(data.get("payload", "{}")),
                            timestamp=data["timestamp"],
                            correlation_id=UUID(data["correlation_id"]),
                            causation_id=UUID(data["causation_id"]) if data.get("causation_id") else None,
                        )
                        events.append((msg_id, event))
                    except Exception as e:
                        logger.error("Failed to parse event %s: %s", msg_id, e)
                        # Ack bad messages to prevent reprocessing
                        await self.ack(msg_id)

        return events

    async def ack(self, message_id: str) -> None:
        """Acknowledge a processed event."""
        await self.redis.xack(STREAM_KEY, CONSUMER_GROUP, message_id)

    async def get_pending(
        self, consumer_name: str, count: int = 10
    ) -> list[dict[str, Any]]:
        """Get pending (unacknowledged) events for a consumer."""
        pending = await self.redis.xpending_range(
            STREAM_KEY, CONSUMER_GROUP, "-", "+", count, consumername=consumer_name
        )
        return pending

    async def get_stream_info(self) -> dict[str, Any]:
        """Get stream info for monitoring."""
        try:
            info = await self.redis.xinfo_stream(STREAM_KEY)
            groups = await self.redis.xinfo_groups(STREAM_KEY)
            return {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": len(groups),
            }
        except aioredis.ResponseError:
            return {"length": 0, "groups": 0}
