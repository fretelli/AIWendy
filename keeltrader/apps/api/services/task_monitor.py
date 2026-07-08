"""Helpers for task ownership and Celery status snapshots."""

from typing import Any, Dict

from celery import states
from fastapi import HTTPException

from core.cache_service import get_cache_service
from core.i18n import t
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
