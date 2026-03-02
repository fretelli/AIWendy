"""Memory tools — agent-callable tools for self-managing memory.

Provides memory_search, memory_update, and memory_forget tools
that agents can use via PydanticAI tool registration.

Routes to appropriate memory layer (episodic/semantic/procedural).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Default Redis URL (used when called outside of agent deps context)
_DEFAULT_REDIS = os.environ.get("REDIS_URL", "redis://localhost:6379/3")


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: UUID
    agent_id: str
    user_id: UUID | None
    memory_key: str
    memory_value: Any
    memory_layer: str  # episodic / semantic / procedural
    importance: float = 0.5
    last_accessed: datetime
    created_at: datetime
    expires_at: datetime | None = None


class MemorySearchResult(BaseModel):
    """Result of a memory search."""
    entries: list[MemoryEntry]
    total_count: int
    query: str


def _get_redis_url() -> str:
    return os.environ.get("REDIS_URL", _DEFAULT_REDIS)


async def memory_search(
    query: str,
    layer: str = "episodic",
    agent_id: str = "",
    user_id: str | None = None,
    time_range_days: int | None = None,
    limit: int = 10,
) -> MemorySearchResult:
    """Search agent memory across layers.

    Args:
        query: Search query (text for semantic search, key pattern for episodic)
        layer: Memory layer (episodic/semantic/procedural)
        agent_id: Agent performing the search
        user_id: User context
        time_range_days: Limit to recent N days (episodic only)
        limit: Max results

    Returns:
        MemorySearchResult with matching entries
    """
    redis_url = _get_redis_url()
    entries: list[MemoryEntry] = []

    try:
        if layer == "episodic":
            from .episodic import EpisodicMemory
            mem = EpisodicMemory(redis_url)
            results = await mem.search(
                query=query,
                agent_id=agent_id,
                user_id=user_id,
                time_range_days=time_range_days,
                limit=limit,
            )
            for r in results:
                entries.append(_dict_to_entry(r, layer="episodic"))

        elif layer == "semantic":
            from .semantic import SemanticMemory
            mem = SemanticMemory(redis_url)
            results = await mem.search(
                query=query,
                agent_id=agent_id,
                user_id=user_id,
                limit=limit,
            )
            for r in results:
                entries.append(_dict_to_entry(r, layer="semantic"))

        elif layer == "procedural":
            from .procedural import ProceduralMemory
            mem = ProceduralMemory(redis_url)
            rules = await mem.get_trading_rules(agent_id, user_id)
            # Filter rules by query
            query_lower = query.lower()
            matched = [
                r for r in rules
                if query_lower in r.lower() or not query
            ]
            for i, rule in enumerate(matched[:limit]):
                entries.append(MemoryEntry(
                    id=uuid4(),
                    agent_id=agent_id,
                    user_id=UUID(user_id) if user_id else None,
                    memory_key=f"rule_{i}",
                    memory_value=rule,
                    memory_layer="procedural",
                    importance=0.8,
                    last_accessed=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                ))

        else:
            logger.warning("Unknown memory layer: %s", layer)

    except Exception as e:
        logger.error("Memory search failed: %s", e)

    logger.info(
        "Memory search: agent=%s layer=%s query=%s results=%d",
        agent_id, layer, query[:50], len(entries),
    )
    return MemorySearchResult(entries=entries, total_count=len(entries), query=query)


async def memory_update(
    key: str,
    value: Any,
    layer: str = "episodic",
    agent_id: str = "",
    user_id: str | None = None,
    importance: float = 0.5,
    expires_in_hours: int | None = None,
) -> MemoryEntry:
    """Update or create a memory entry in the specified layer.

    Args:
        key: Memory key (unique within agent+user+layer)
        value: Memory value (any JSON-serializable data)
        layer: Memory layer (episodic/semantic)
        agent_id: Agent managing the memory
        user_id: User context
        importance: 0.0 to 1.0 importance score
        expires_in_hours: Optional TTL in hours

    Returns:
        The created/updated MemoryEntry
    """
    redis_url = _get_redis_url()

    try:
        if layer == "episodic":
            from .episodic import EpisodicMemory
            mem = EpisodicMemory(redis_url)
            result = await mem.store(
                key=key,
                value=value,
                agent_id=agent_id,
                user_id=user_id,
                importance=importance,
                expires_in_hours=expires_in_hours,
            )
            return _dict_to_entry(result, layer="episodic")

        elif layer == "semantic":
            from .semantic import SemanticMemory
            mem = SemanticMemory(redis_url)
            tags = []
            if isinstance(value, dict):
                tags = value.get("tags", [])
            result = await mem.store(
                key=key,
                value=value,
                agent_id=agent_id,
                user_id=user_id,
                importance=importance,
                tags=tags,
            )
            return _dict_to_entry(result, layer="semantic")

        elif layer == "procedural":
            from .procedural import ProceduralMemory
            mem = ProceduralMemory(redis_url)
            if user_id:
                await mem.add_trading_rule(user_id, str(value))
            else:
                await mem.set_config(key, value)
            now = datetime.utcnow()
            return MemoryEntry(
                id=uuid4(),
                agent_id=agent_id,
                user_id=UUID(user_id) if user_id else None,
                memory_key=key,
                memory_value=value,
                memory_layer="procedural",
                importance=importance,
                last_accessed=now,
                created_at=now,
            )

    except Exception as e:
        logger.error("Memory update failed: %s", e)

    logger.info(
        "Memory update: agent=%s layer=%s key=%s",
        agent_id, layer, key,
    )
    now = datetime.utcnow()
    return MemoryEntry(
        id=uuid4(),
        agent_id=agent_id,
        user_id=UUID(user_id) if user_id else None,
        memory_key=key,
        memory_value=value,
        memory_layer=layer,
        importance=importance,
        last_accessed=now,
        created_at=now,
    )


async def memory_forget(
    key: str,
    layer: str = "episodic",
    agent_id: str = "",
    user_id: str | None = None,
) -> bool:
    """Forget (delete) a memory entry.

    Returns True if entry was found and deleted.
    """
    redis_url = _get_redis_url()

    try:
        if layer == "episodic":
            from .episodic import EpisodicMemory
            mem = EpisodicMemory(redis_url)
            return await mem.forget(key=key, agent_id=agent_id, user_id=user_id)

        elif layer == "semantic":
            from .semantic import SemanticMemory
            mem = SemanticMemory(redis_url)
            return await mem.forget(key=key, agent_id=agent_id, user_id=user_id)

        elif layer == "procedural":
            from .procedural import ProceduralMemory
            mem = ProceduralMemory(redis_url)
            if user_id:
                return await mem.remove_trading_rule(user_id, key)
            return False

    except Exception as e:
        logger.error("Memory forget failed: %s", e)
        return False

    logger.info(
        "Memory forget: agent=%s layer=%s key=%s",
        agent_id, layer, key,
    )
    return True


def _dict_to_entry(data: dict[str, Any], layer: str) -> MemoryEntry:
    """Convert a raw dict from memory backends into a MemoryEntry."""
    now = datetime.utcnow()
    uid = data.get("user_id", "")

    return MemoryEntry(
        id=UUID(data["id"]) if data.get("id") else uuid4(),
        agent_id=data.get("agent_id", ""),
        user_id=UUID(uid) if uid and uid != "" else None,
        memory_key=data.get("key", ""),
        memory_value=data.get("value", ""),
        memory_layer=layer,
        importance=float(data.get("importance", "0.5")),
        last_accessed=_parse_dt(data.get("last_accessed")) or now,
        created_at=_parse_dt(data.get("created_at")) or now,
    )


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None
