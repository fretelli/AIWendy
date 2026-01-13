"""Cache utilities for Redis operations."""

import os
from typing import Optional

import redis
from redis import Redis

from config import get_settings

settings = get_settings()

# Global Redis client instance
_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """Get or create Redis client instance."""
    global _redis_client
    if _redis_client is None:
        # Get Redis URL from settings or environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        # Create Redis client
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    return _redis_client


def clear_cache(pattern: str = "*") -> int:
    """Clear cache entries matching the pattern."""
    client = get_redis_client()
    keys = client.keys(pattern)
    if keys:
        return client.delete(*keys)
    return 0
