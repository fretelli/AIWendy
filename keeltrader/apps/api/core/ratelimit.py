"""Rate limiting implementation."""

import time
from typing import Optional, Tuple

import redis.asyncio as redis

from config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimiter:
    """Redis-based sliding window rate limiter."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        window_start = now - window_seconds

        # Use pipeline for atomic operations
        async with self.redis.pipeline() as pipe:
            # Remove expired entries
            await pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            await pipe.zcard(key)
            # Execute pipeline
            results = await pipe.execute()

        current_count = results[1]

        # Check if limit exceeded
        if current_count >= limit:
            return False, 0

        # Add current request
        async with self.redis.pipeline() as pipe:
            await pipe.zadd(key, {str(now): now})
            await pipe.expire(key, window_seconds)
            await pipe.execute()

        remaining = limit - current_count - 1
        return True, max(0, remaining)

    async def get_retry_after(self, key: str, window_seconds: int) -> int:
        """Get seconds until rate limit resets."""
        now = time.time()
        window_start = now - window_seconds

        # Get oldest entry in current window
        oldest_entries = await self.redis.zrangebyscore(
            key, window_start, now, start=0, num=1, withscores=True
        )

        if oldest_entries:
            oldest_timestamp = oldest_entries[0][1]
            retry_after = int(oldest_timestamp + window_seconds - now)
            return max(1, retry_after)

        return 1

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        await self.redis.delete(key)


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter

    if _rate_limiter is None:
        redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        _rate_limiter = RateLimiter(redis_client)

    return _rate_limiter
