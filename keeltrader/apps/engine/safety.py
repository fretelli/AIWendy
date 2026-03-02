"""Anti-cascade safety mechanisms for the event engine."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from uuid import UUID

import redis.asyncio as aioredis

from .event_types import Event

logger = logging.getLogger(__name__)

# Limits
MAX_EVENTS_PER_USER_PER_MINUTE = 20
MAX_CAUSATION_DEPTH = 5
AGENT_COOLDOWN_SECONDS = 60  # For executor-type agents


class EventSafety:
    """Safety checks to prevent event cascades and infinite loops."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._prefix = "keeltrader:safety"

    async def check_rate_limit(self, user_id: UUID | None) -> bool:
        """Check if user is within event rate limit.

        Returns True if event is allowed, False if rate-limited.
        """
        if user_id is None:
            return True  # System events not rate-limited

        key = f"{self._prefix}:rate:{user_id}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 60)

        if count > MAX_EVENTS_PER_USER_PER_MINUTE:
            logger.warning(
                "Rate limit exceeded for user %s: %d events/min", user_id, count
            )
            return False
        return True

    async def check_causation_depth(self, event: Event) -> bool:
        """Check if event causation chain is within depth limit.

        Returns True if allowed, False if too deep.
        """
        if event.causation_id is None:
            return True  # Root event, depth = 0

        depth = 0
        current_id = event.causation_id
        visited = {event.id}

        while current_id and depth < MAX_CAUSATION_DEPTH + 1:
            # Check for loops
            if current_id in visited:
                logger.error(
                    "Causation loop detected: event %s in chain of %s",
                    current_id, event.id,
                )
                return False

            visited.add(current_id)
            depth += 1

            # Look up parent event's causation_id from Redis
            parent_causation = await self._redis.get(
                f"{self._prefix}:causation:{current_id}"
            )
            current_id = UUID(parent_causation) if parent_causation else None

        if depth > MAX_CAUSATION_DEPTH:
            logger.warning(
                "Causation depth exceeded for event %s: depth=%d", event.id, depth
            )
            return False

        # Store this event's causation for future lookups
        await self._redis.set(
            f"{self._prefix}:causation:{event.id}",
            str(event.causation_id) if event.causation_id else "",
            ex=3600,  # TTL 1 hour
        )

        return True

    async def check_agent_cooldown(self, agent_id: str) -> bool:
        """Check if agent is past its cooldown period.

        Returns True if allowed, False if in cooldown.
        """
        key = f"{self._prefix}:cooldown:{agent_id}"
        last_exec = await self._redis.get(key)

        if last_exec:
            elapsed = time.time() - float(last_exec)
            if elapsed < AGENT_COOLDOWN_SECONDS:
                logger.debug(
                    "Agent %s in cooldown: %.1fs remaining",
                    agent_id, AGENT_COOLDOWN_SECONDS - elapsed,
                )
                return False
        return True

    async def record_agent_execution(self, agent_id: str) -> None:
        """Record agent execution timestamp for cooldown tracking."""
        key = f"{self._prefix}:cooldown:{agent_id}"
        await self._redis.set(key, str(time.time()), ex=AGENT_COOLDOWN_SECONDS * 2)

    async def check_all(self, event: Event, agent_id: str) -> tuple[bool, str]:
        """Run all safety checks.

        Returns (allowed, reason) tuple.
        """
        if not await self.check_rate_limit(event.user_id):
            return False, "rate_limit_exceeded"

        if not await self.check_causation_depth(event):
            return False, "causation_depth_exceeded"

        if not await self.check_agent_cooldown(agent_id):
            return False, "agent_in_cooldown"

        return True, "ok"
