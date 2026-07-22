"""Read the deployment-owned structured-data publication snapshot."""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from config import get_settings


_lock = Lock()
_cached_mtime_ns: int | None = None
_cached_payload: dict[str, Any] | None = None


def read_publication_status() -> dict[str, Any]:
    global _cached_mtime_ns, _cached_payload
    path = Path(get_settings().market_publication_status_path)
    try:
        mtime_ns = path.stat().st_mtime_ns
    except OSError:
        return {
            "available": False,
            "version": "unavailable",
            "generated_at": None,
            "datasets": [],
            "unavailable_reason": "结构化数据发布状态文件不可用；不以请求时扫描或合成值替代。",
        }
    with _lock:
        if _cached_payload is not None and _cached_mtime_ns == mtime_ns:
            return _cached_payload
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {
                "available": False,
                "version": "invalid",
                "generated_at": None,
                "datasets": [],
                "unavailable_reason": "结构化数据发布状态文件损坏；保留明确不可用状态。",
            }
        if not isinstance(payload, dict) or not isinstance(payload.get("datasets"), list):
            return {
                "available": False,
                "version": "invalid",
                "generated_at": None,
                "datasets": [],
                "unavailable_reason": "结构化数据发布状态格式不受支持。",
            }
        payload["available"] = True
        _cached_mtime_ns = mtime_ns
        _cached_payload = payload
        return payload


def publication_version() -> str:
    return str(read_publication_status().get("version") or "unavailable")
