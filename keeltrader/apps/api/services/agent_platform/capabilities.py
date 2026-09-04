"""Read the deployment-owned Structured Data capability manifest."""
from __future__ import annotations

import json
import re
from pathlib import Path
from threading import Lock
from typing import Any

from config import get_settings

_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_lock = Lock()
_cached: tuple[int, dict[str, Any]] | None = None


def _unavailable(reason: str) -> dict[str, Any]:
    return {"available": False, "version": "unavailable", "generated_at": None, "source": "tushare-structured-data",
            "capabilities": [], "unavailable_reason": reason, "synthetic_substitution": False}


def read_capability_manifest() -> dict[str, Any]:
    global _cached
    path = Path(get_settings().market_capability_manifest_path)
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return _unavailable("结构化数据能力清单不可用；不扩大查询白名单或合成缺失数据。")
    with _lock:
        if _cached and _cached[0] == mtime:
            return _cached[1]
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return _unavailable("结构化数据能力清单损坏；查询白名单保持为空。")
        capabilities = payload.get("capabilities") if isinstance(payload, dict) else None
        if not isinstance(capabilities, list):
            return _unavailable("结构化数据能力清单格式不受支持。")
        payload["available"] = True
        _cached = (mtime, payload)
        return payload


def queryable_tables() -> frozenset[str]:
    manifest = read_capability_manifest()
    tables = {str(item.get("table")) for item in manifest.get("capabilities", [])
              if item.get("physical") and item.get("available") and item.get("exposure") in {"typed_api", "agent_query"}
              and item.get("table") and _IDENT.match(str(item.get("table")))}
    return frozenset(tables)


def physical_tables() -> frozenset[str]:
    manifest = read_capability_manifest()
    tables = {str(item.get("table")) for item in manifest.get("capabilities", [])
              if item.get("physical") and item.get("available") and item.get("table")
              and _IDENT.match(str(item.get("table")))}
    return frozenset(tables)


def classified_tables() -> frozenset[str]:
    """Return every valid physical table, including retained unavailable data."""
    manifest = read_capability_manifest()
    return frozenset(
        str(item.get("table"))
        for item in manifest.get("capabilities", [])
        if item.get("physical") and item.get("table") and _IDENT.match(str(item.get("table")))
    )


def capability_status(table: str) -> dict[str, Any] | None:
    """Return the manifest entry for a classified physical table."""
    if not _IDENT.match(table):
        return None
    return next(
        (
            dict(item)
            for item in read_capability_manifest().get("capabilities", [])
            if item.get("physical") and item.get("table") == table
        ),
        None,
    )


def capability_version() -> str:
    return str(read_capability_manifest().get("version") or "unavailable")
