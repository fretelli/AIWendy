"""Task event helpers (Redis pub/sub + ownership)."""

from __future__ import annotations

import json
from typing import Any, Optional

from core.cache import get_redis_client

TASK_OWNER_KEY_PREFIX = "task:owner:"
TASK_EVENT_CHANNEL_PREFIX = "task:events:"


def task_owner_key(task_id: str) -> str:
    return f"{TASK_OWNER_KEY_PREFIX}{task_id}"


def task_event_channel(task_id: str) -> str:
    return f"{TASK_EVENT_CHANNEL_PREFIX}{task_id}"


def record_task_owner(
    task_id: str, user_id: str, ttl_seconds: int = 24 * 60 * 60
) -> None:
    """Record task ownership for authorization checks."""
    redis_client = get_redis_client()
    redis_client.setex(task_owner_key(task_id), ttl_seconds, user_id)


def get_task_owner(task_id: str) -> Optional[str]:
    """Best-effort get task owner (may be missing if expired)."""
    redis_client = get_redis_client()
    value = redis_client.get(task_owner_key(task_id))
    return str(value) if value else None


def publish_task_event(task_id: str, payload: dict[str, Any]) -> None:
    """Publish a task event to Redis pub/sub."""
    redis_client = get_redis_client()
    redis_client.publish(
        task_event_channel(task_id), json.dumps(payload, ensure_ascii=False)
    )
