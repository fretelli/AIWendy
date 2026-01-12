"""Cache key helpers (Redis)."""

from __future__ import annotations

import hashlib
from typing import Optional


def analysis_stats_key(user_id: str, project_id: Optional[str], period: str) -> str:
    project_part = project_id or "all"
    return f"analysis:stats:{user_id}:{project_part}:{period}"


def analysis_patterns_key(user_id: str, project_id: Optional[str], period: str) -> str:
    project_part = project_id or "all"
    return f"analysis:patterns:{user_id}:{project_part}:{period}"


def knowledge_search_key(
    user_id: str, project_id: Optional[str], limit: int, q: str
) -> str:
    q_hash = hashlib.md5((q or "").encode("utf-8")).hexdigest()
    project_part = project_id or "all"
    return f"kb:search:{user_id}:{project_part}:{int(limit)}:{q_hash}"
