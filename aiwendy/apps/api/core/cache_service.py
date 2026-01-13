"""Enhanced cache service with decorators and utilities."""

import asyncio
import hashlib
import json
import pickle
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, Union

import redis
import redis.asyncio as redis_async

from config import get_settings
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CacheService:
    """Enhanced Redis cache service with async support."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache service."""
        self.redis_url = redis_url or settings.redis_url
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[redis_async.Redis] = None

    @property
    def sync_client(self) -> redis.Redis:
        """Get synchronous Redis client."""
        if self._sync_client is None:
            self._sync_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        return self._sync_client

    @property
    async def async_client(self) -> redis_async.Redis:
        """Get asynchronous Redis client."""
        if self._async_client is None:
            self._async_client = redis_async.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._async_client

    # Synchronous methods
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.sync_client.get(key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            serialized = self._serialize(value)
            if ttl:
                return self.sync_client.setex(key, ttl, serialized)
            else:
                return self.sync_client.set(key, serialized)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(self.sync_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            keys = self.sync_client.keys(pattern)
            if keys:
                return self.sync_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear error for pattern {pattern}: {str(e)}")
            return 0

    # Asynchronous methods
    async def get_async(self, key: str) -> Optional[Any]:
        """Get value from cache asynchronously."""
        try:
            client = await self.async_client
            value = await client.get(key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Async cache get error for key {key}: {str(e)}")
            return None

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache asynchronously."""
        try:
            client = await self.async_client
            serialized = self._serialize(value)
            if ttl:
                return await client.setex(key, ttl, serialized)
            else:
                return await client.set(key, serialized)
        except Exception as e:
            logger.error(f"Async cache set error for key {key}: {str(e)}")
            return False

    async def delete_async(self, key: str) -> bool:
        """Delete key from cache asynchronously."""
        try:
            client = await self.async_client
            return bool(await client.delete(key))
        except Exception as e:
            logger.error(f"Async cache delete error for key {key}: {str(e)}")
            return False

    async def clear_pattern_async(self, pattern: str) -> int:
        """Clear all keys matching pattern asynchronously."""
        try:
            client = await self.async_client
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Async cache clear error for pattern {pattern}: {str(e)}")
            return 0

    # Utility methods
    def _serialize(self, value: Any) -> str:
        """Serialize value for storage."""
        if isinstance(value, (str, int, float)):
            return str(value)
        try:
            return json.dumps(value)
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value).hex()

    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage."""
        try:
            # Try JSON first
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            try:
                # Try as pickle
                return pickle.loads(bytes.fromhex(value))
            except:
                # Return as string
                return value

    def make_key(self, *parts: Any) -> str:
        """Create a cache key from parts."""
        return ":".join(str(p) for p in parts)

    def make_hash_key(self, data: Any) -> str:
        """Create a hash-based cache key."""
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# Decorators


def cache(
    key_prefix: str,
    ttl: Union[int, timedelta] = 300,
    key_func: Optional[Callable] = None,
) -> Callable:
    """
    Cache decorator for synchronous functions.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds or timedelta
        key_func: Optional function to generate cache key from arguments

    Example:
        @cache("user", ttl=3600)
        def get_user(user_id: str):
            return fetch_user_from_db(user_id)
    """
    if isinstance(ttl, timedelta):
        ttl = int(ttl.total_seconds())

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_service = get_cache_service()

            # Generate cache key
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default key generation
                key_parts = [key_prefix]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.append(cache_service.make_hash_key(kwargs))
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            cache_service.set(cache_key, result, ttl)

            return result

        # Add cache management methods
        wrapper.clear_cache = lambda: get_cache_service().clear_pattern(
            f"{key_prefix}:*"
        )
        wrapper.cache_key_prefix = key_prefix

        return wrapper

    return decorator


def cache_async(
    key_prefix: str,
    ttl: Union[int, timedelta] = 300,
    key_func: Optional[Callable] = None,
) -> Callable:
    """
    Cache decorator for asynchronous functions.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds or timedelta
        key_func: Optional function to generate cache key from arguments

    Example:
        @cache_async("user", ttl=3600)
        async def get_user(user_id: str):
            return await fetch_user_from_db(user_id)
    """
    if isinstance(ttl, timedelta):
        ttl = int(ttl.total_seconds())

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_service = get_cache_service()

            # Generate cache key
            if key_func:
                cache_key = f"{key_prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default key generation
                key_parts = [key_prefix]
                if args:
                    key_parts.extend(str(arg) for arg in args)
                if kwargs:
                    key_parts.append(cache_service.make_hash_key(kwargs))
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = await cache_service.get_async(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            await cache_service.set_async(cache_key, result, ttl)

            return result

        # Add cache management methods
        wrapper.clear_cache = lambda: asyncio.create_task(
            get_cache_service().clear_pattern_async(f"{key_prefix}:*")
        )
        wrapper.cache_key_prefix = key_prefix

        return wrapper

    return decorator


def invalidate_cache(*patterns: str) -> Callable:
    """
    Decorator to invalidate cache patterns after function execution.

    Args:
        patterns: Cache key patterns to invalidate

    Example:
        @invalidate_cache("user:*", "dashboard:*")
        def update_user(user_id: str, data: dict):
            return save_user_to_db(user_id, data)
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
                cache_service = get_cache_service()
                for pattern in patterns:
                    await cache_service.clear_pattern_async(pattern)
                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                cache_service = get_cache_service()
                for pattern in patterns:
                    cache_service.clear_pattern(pattern)
                return result

            return sync_wrapper

    return decorator


# Cache key generators


def user_cache_key(user_id: str, *parts: str) -> str:
    """Generate user-specific cache key."""
    return f"user:{user_id}:{':'.join(parts)}"


def project_cache_key(project_id: str, *parts: str) -> str:
    """Generate project-specific cache key."""
    return f"project:{project_id}:{':'.join(parts)}"


def dashboard_cache_key(user_id: str, period: str = "default") -> str:
    """Generate dashboard cache key."""
    return f"dashboard:{user_id}:{period}"


def report_cache_key(report_id: str) -> str:
    """Generate report cache key."""
    return f"report:{report_id}"
