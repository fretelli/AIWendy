"""Narrow filesystem bridge to the host-owned Agent OS learning core."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


MAX_SNAPSHOT_BYTES = 1_000_000
MAX_FEEDBACK_BYTES = 16_384


class LearningBridge:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.snapshot_path = self.root / "snapshot.json"
        self.inbox_path = self.root / "inbox"

    def snapshot(self) -> dict[str, Any]:
        try:
            if self.snapshot_path.stat().st_size > MAX_SNAPSHOT_BYTES:
                raise ValueError("learning snapshot is too large")
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"available": False, "state": "not_configured", "memories": []}
        except (OSError, ValueError, json.JSONDecodeError):
            return {"available": False, "state": "invalid_snapshot", "memories": []}
        memories = payload.get("memories")
        if not isinstance(memories, list):
            return {"available": False, "state": "invalid_snapshot", "memories": []}
        return {
            "available": True,
            "state": "ready",
            "generated_at": payload.get("generated_at"),
            "memory_count": len(memories),
            "memories": memories[:200],
        }

    def record_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = str(uuid4())
        row = {
            "schema_version": 1,
            "event_id": event_id,
            "entry_type": "keeltrader",
            "event_type": payload["event_type"],
            "summary": payload["summary"],
            "conversation_id": payload["conversation_id"],
            "task_id": payload.get("task_id") or "",
            "message_id": payload["message_id"],
            "user_id": payload["user_id"],
            "created_at": datetime.now(UTC).isoformat(),
        }
        encoded = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        if len(encoded) > MAX_FEEDBACK_BYTES:
            raise ValueError("feedback event is too large")
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        target = self.inbox_path / f"{event_id}.json"
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return {"accepted": True, "event_id": event_id}
