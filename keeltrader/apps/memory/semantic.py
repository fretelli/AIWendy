"""L2 Semantic Memory — vector-similarity search via Redis.

Semantic memory stores knowledge, rules, and insights that can be retrieved
by meaning rather than exact key. For MVP, uses TF-IDF-like keyword matching
in Redis. Future: pgvector embeddings for true semantic search.

Entries represent factual knowledge: trading rules, learned patterns,
user preferences, market insights.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_PREFIX = "keeltrader:memory:semantic"
_INDEX_PREFIX = "keeltrader:memory:semantic_idx"
_TTL_DAYS = 365  # Semantic memories persist long


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer for keyword matching."""
    text = text.lower()
    # Keep CJK characters as individual tokens + english words
    tokens: list[str] = []
    # English words
    tokens.extend(re.findall(r"[a-z0-9]+", text))
    # CJK characters (Chinese/Japanese/Korean)
    tokens.extend(re.findall(r"[\u4e00-\u9fff]", text))
    return tokens


def _keyword_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    """Simple keyword overlap score (0.0–1.0)."""
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_counter = Counter(doc_tokens)
    hits = sum(1 for t in query_tokens if doc_counter[t] > 0)
    return hits / len(query_tokens)


class SemanticMemory:
    """L2 Semantic Memory — keyword-based semantic search over Redis."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

    async def store(
        self,
        key: str,
        value: Any,
        agent_id: str,
        user_id: str | None = None,
        importance: float = 0.5,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Store a semantic memory entry.

        Args:
            key: Descriptive key/title
            value: Content (string or JSON-serializable)
            agent_id: Agent storing the memory
            user_id: User context
            importance: 0.0–1.0 importance score
            tags: Optional tags for categorization

        Returns:
            Stored entry as dict
        """
        entry_id = str(uuid4())
        now = datetime.utcnow()

        value_str = json.dumps(value) if not isinstance(value, str) else value
        # Build searchable text from key + value + tags
        search_text = f"{key} {value_str} {' '.join(tags or [])}"
        tokens = _tokenize(search_text)

        entry = {
            "id": entry_id,
            "key": key,
            "value": value_str,
            "agent_id": agent_id,
            "user_id": user_id or "",
            "importance": str(importance),
            "tags": json.dumps(tags or []),
            "tokens": json.dumps(tokens[:200]),  # Cap tokens
            "created_at": now.isoformat(),
            "last_accessed": now.isoformat(),
        }

        scope = f"{agent_id}:{user_id or 'global'}"
        ttl = _TTL_DAYS * 86400

        r = aioredis.from_url(self._redis_url)
        try:
            pipe = r.pipeline()
            hash_key = f"{_PREFIX}:{entry_id}"
            pipe.hset(hash_key, mapping=entry)
            pipe.expire(hash_key, ttl)

            # Add to scope set for listing
            idx_key = f"{_INDEX_PREFIX}:{scope}"
            pipe.sadd(idx_key, entry_id)
            pipe.expire(idx_key, ttl)

            # Key-based exact lookup
            key_idx = f"{_PREFIX}:by_key:{scope}:{key}"
            pipe.set(key_idx, entry_id, ex=ttl)

            await pipe.execute()

            logger.debug("Semantic memory stored: %s key=%s", entry_id, key)
            return {**entry, "value": value, "tags": tags or []}

        finally:
            await r.aclose()

    async def search(
        self,
        query: str,
        agent_id: str,
        user_id: str | None = None,
        limit: int = 10,
        min_score: float = 0.1,
    ) -> list[dict[str, Any]]:
        """Search semantic memories by keyword similarity.

        Args:
            query: Natural language query
            agent_id: Agent context
            user_id: User context
            limit: Max results
            min_score: Minimum keyword match score

        Returns:
            Matching entries sorted by relevance
        """
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scope = f"{agent_id}:{user_id or 'global'}"
        idx_key = f"{_INDEX_PREFIX}:{scope}"

        r = aioredis.from_url(self._redis_url)
        try:
            entry_ids = await r.smembers(idx_key)
            scored: list[tuple[float, dict[str, Any]]] = []

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

                # Score by keyword overlap
                try:
                    doc_tokens = json.loads(entry.get("tokens", "[]"))
                except json.JSONDecodeError:
                    doc_tokens = []

                score = _keyword_score(query_tokens, doc_tokens)
                # Boost by importance
                importance = float(entry.get("importance", "0.5"))
                score = score * 0.8 + importance * 0.2

                if score >= min_score:
                    # Parse value
                    try:
                        entry["value"] = json.loads(entry["value"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                    try:
                        entry["tags"] = json.loads(entry["tags"])
                    except (json.JSONDecodeError, TypeError):
                        entry["tags"] = []

                    entry["_score"] = round(score, 3)
                    scored.append((score, entry))

            # Sort by score descending
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [entry for _, entry in scored[:limit]]

            # Update last_accessed
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
        """Get a specific semantic memory by exact key."""
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
            try:
                entry["tags"] = json.loads(entry["tags"])
            except (json.JSONDecodeError, TypeError):
                entry["tags"] = []

            return entry

        finally:
            await r.aclose()

    async def forget(
        self,
        key: str,
        agent_id: str,
        user_id: str | None = None,
    ) -> bool:
        """Delete a semantic memory by key."""
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
            pipe.srem(f"{_INDEX_PREFIX}:{scope}", eid)
            await pipe.execute()

            return True

        finally:
            await r.aclose()
