"""Helpers for task ownership, Celery status snapshots, and SSE streams."""

import asyncio
import json
from typing import Any, AsyncIterator, Dict

from celery import states
from fastapi import HTTPException

from core.cache_service import get_cache_service
from core.i18n import t
from core.task_events import task_event_channel
from domain.user.models import User


async def ensure_task_owner(task_id: str, current_user: User, locale: str) -> None:
    cache = get_cache_service()
    redis_client = await cache.async_client
    owner = await redis_client.get(f"task:owner:{task_id}")
    if owner and (str(owner) != str(current_user.id)) and (not current_user.is_admin):
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))


def queued_task_response(task_id: str, message: str) -> Dict[str, Any]:
    return {
        "task_id": task_id,
        "status": "queued",
        "message": message,
        "check_status_url": f"/api/v1/tasks/status/{task_id}",
    }


def task_result_snapshot(task_id: str, result: Any) -> Dict[str, Any]:
    ready = result.ready()
    return {
        "task_id": task_id,
        "state": result.state,
        "ready": ready,
        "successful": result.successful() if ready else None,
        "failed": result.failed() if ready else None,
        "result": result.result if ready and result.successful() else None,
        "error": str(result.info) if ready and result.failed() else None,
    }


async def task_status_event_stream(
    task_id: str,
    result: Any,
    redis_client: Any,
) -> AsyncIterator[str]:
    """Yield task status updates as Server-Sent Events."""
    channel = task_event_channel(task_id)
    pubsub = redis_client.pubsub()
    last_state: str | None = None
    last_sent_at = 0.0
    try:
        await pubsub.subscribe(channel)

        snapshot = task_result_snapshot(task_id, result)
        yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
        if snapshot["ready"]:
            return

        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message.get("data"):
                data = message["data"]
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode("utf-8", errors="ignore")
                yield f"data: {data}\n\n"
                try:
                    parsed = json.loads(data)
                    if parsed.get("ready") is True:
                        return
                except Exception:
                    pass

            if result.state != last_state:
                last_state = result.state
                snapshot = task_result_snapshot(task_id, result)
                yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                if snapshot["ready"]:
                    return

            now = asyncio.get_running_loop().time()
            if now - last_sent_at > 15:
                last_sent_at = now
                yield "event: ping\ndata: {}\n\n"

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        return
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass


def task_status_response(task_id: str, result: Any, locale: str) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = str(result.info)
            response["traceback"] = result.traceback
    elif result.state == states.PENDING:
        response["info"] = t("messages.task_waiting", locale)
    elif result.state == states.STARTED:
        response["info"] = t("messages.task_started", locale)
    elif result.state != states.FAILURE:
        response["info"] = result.info

    return response
