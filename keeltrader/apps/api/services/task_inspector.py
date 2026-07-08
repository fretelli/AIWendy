"""Pure response builders for Celery task inspection endpoints."""

from datetime import datetime
from typing import Any, Dict, List

from domain.user.models import User


def _timestamp() -> str:
    return datetime.utcnow().isoformat()


def active_tasks_response(
    active_tasks: Dict[str, List[Dict[str, Any]]] | None,
    current_user: User,
    limit: int,
) -> Dict[str, Any]:
    if not active_tasks:
        return {"tasks": [], "total": 0, "timestamp": _timestamp()}

    user_tasks: List[Dict[str, Any]] = []
    for worker, tasks in active_tasks.items():
        for task in tasks:
            task_args = task.get("args", [])
            task_kwargs = task.get("kwargs", {})
            user_id_match = (
                str(current_user.id) in task_args
                or task_kwargs.get("user_id") == str(current_user.id)
                or current_user.is_admin
            )

            if user_id_match:
                user_tasks.append(
                    {
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "worker": worker,
                        "args": task.get("args"),
                        "kwargs": task.get("kwargs"),
                        "time_start": task.get("time_start"),
                    }
                )

    user_tasks = user_tasks[:limit]
    return {
        "tasks": user_tasks,
        "total": len(user_tasks),
        "timestamp": _timestamp(),
    }


def empty_active_tasks_error_response(message: str) -> Dict[str, Any]:
    return {
        "tasks": [],
        "total": 0,
        "error": message,
        "timestamp": _timestamp(),
    }


def scheduled_tasks_response(beat_schedule: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    scheduled_tasks = [
        {
            "name": task_name,
            "task": task_info.get("task"),
            "schedule": str(task_info.get("schedule")),
            "args": task_info.get("args", []),
            "kwargs": task_info.get("kwargs", {}),
        }
        for task_name, task_info in beat_schedule.items()
    ]

    return {
        "scheduled_tasks": scheduled_tasks,
        "total": len(scheduled_tasks),
        "timestamp": _timestamp(),
    }


def task_stats_response(
    stats: Dict[str, Dict[str, Any]] | None,
    active: Dict[str, List[Dict[str, Any]]] | None,
    scheduled: Dict[str, List[Dict[str, Any]]] | None,
    reserved: Dict[str, List[Dict[str, Any]]] | None,
) -> Dict[str, Any]:
    active_count = sum(len(tasks) for tasks in (active or {}).values())
    scheduled_count = sum(len(tasks) for tasks in (scheduled or {}).values())
    reserved_count = sum(len(tasks) for tasks in (reserved or {}).values())

    worker_stats: List[Dict[str, Any]] = []
    if stats:
        for worker, worker_info in stats.items():
            pool = worker_info.get("pool", {})
            worker_stats.append(
                {
                    "worker": worker,
                    "pool": pool.get("implementation"),
                    "max_concurrency": pool.get("max-concurrency"),
                    "processes": pool.get("processes"),
                    "total_tasks": worker_info.get("total", {}),
                }
            )

    return {
        "queue_stats": {
            "active_tasks": active_count,
            "scheduled_tasks": scheduled_count,
            "reserved_tasks": reserved_count,
        },
        "workers": worker_stats,
        "timestamp": _timestamp(),
    }


def empty_task_stats_error_response(message: str) -> Dict[str, Any]:
    return {
        "queue_stats": {
            "active_tasks": 0,
            "scheduled_tasks": 0,
            "reserved_tasks": 0,
        },
        "workers": [],
        "error": message,
        "timestamp": _timestamp(),
    }
