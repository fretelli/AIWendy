"""Read-only search over the host-exported general knowledge snapshot."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

MAX_BYTES = 20_000_000


def _terms(query: str) -> list[str]:
    lowered = query.lower().strip()
    words = re.findall(r"[a-z0-9_.:/-]{2,}|[\u4e00-\u9fff]{2,}", lowered)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    words.extend(chinese[index:index + 2] for index in range(max(0, len(chinese) - 1)))
    return list(dict.fromkeys(term for term in words if term))[:40]


def search_snapshot(path: str | Path, query: str, limit: int = 5) -> dict[str, Any]:
    snapshot = Path(path)
    try:
        if snapshot.stat().st_size > MAX_BYTES:
            raise ValueError("knowledge snapshot is too large")
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"available": False, "items": [], "state": "not_configured"}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"available": False, "items": [], "state": "invalid_snapshot"}
    terms = _terms(query)
    scored = []
    for item in payload.get("chunks", []):
        title = str(item.get("title") or "")
        content = str(item.get("content") or "")
        haystack = f"{title}\n{content}".lower()
        score = sum(haystack.count(term) + (3 if term in title.lower() else 0) for term in terms)
        if score:
            scored.append((score, {"title": title, "source": item.get("source"), "content": content, "score": score}))
    scored.sort(key=lambda row: (-row[0], str(row[1].get("source") or "")))
    return {"available": True, "state": "ready", "generated_at": payload.get("generated_at"),
            "document_count": payload.get("document_count", 0), "items": [row[1] for row in scored[:limit]]}


def prompt_context(path: str | Path, query: str, limit: int = 4) -> str:
    result = search_snapshot(path, query, limit)
    return "\n\n".join(
        f"[{item['title']}] ({item['source']})\n{item['content']}" for item in result.get("items", [])
    )
