"""Celery task inspection response builder regressions."""

from types import SimpleNamespace
from uuid import uuid4

from services.task_inspector import (
    active_tasks_response,
    scheduled_tasks_response,
    task_stats_response,
)


def test_active_tasks_response_filters_by_user_and_limits():
    user_id = uuid4()
    other_id = uuid4()
    current_user = SimpleNamespace(id=user_id, is_admin=False)
    response = active_tasks_response(
        {
            "worker-a": [
                {"id": "task-1", "name": "mine", "args": [str(user_id)], "kwargs": {}, "time_start": 1},
                {"id": "task-2", "name": "also-mine", "args": [], "kwargs": {"user_id": str(user_id)}, "time_start": 2},
                {"id": "task-3", "name": "other", "args": [str(other_id)], "kwargs": {}, "time_start": 3},
            ],
        },
        current_user,
        limit=1,
    )

    assert response["total"] == 1
    assert response["tasks"][0]["task_id"] == "task-1"
    assert response["tasks"][0]["worker"] == "worker-a"
    assert "timestamp" in response


def test_active_tasks_response_admin_sees_all_tasks():
    current_user = SimpleNamespace(id=uuid4(), is_admin=True)
    response = active_tasks_response(
        {
            "worker-a": [{"id": "task-1", "name": "one", "args": [], "kwargs": {}}],
            "worker-b": [{"id": "task-2", "name": "two", "args": [], "kwargs": {}}],
        },
        current_user,
        limit=10,
    )

    assert response["total"] == 2
    assert [task["task_id"] for task in response["tasks"]] == ["task-1", "task-2"]


def test_scheduled_tasks_response_preserves_public_shape():
    response = scheduled_tasks_response(
        {
            "daily": {"task": "reports.daily", "schedule": "0 9 * * *", "args": [1], "kwargs": {"locale": "zh"}},
        }
    )

    assert response["total"] == 1
    assert response["scheduled_tasks"][0] == {
        "name": "daily",
        "task": "reports.daily",
        "schedule": "0 9 * * *",
        "args": [1],
        "kwargs": {"locale": "zh"},
    }


def test_task_stats_response_counts_queues_and_worker_pool():
    response = task_stats_response(
        {
            "worker-a": {
                "pool": {"implementation": "prefork", "max-concurrency": 4, "processes": [1, 2]},
                "total": {"reports.daily": 3},
            }
        },
        active={"worker-a": [{}, {}]},
        scheduled={"worker-a": [{}]},
        reserved={"worker-b": [{}, {}, {}]},
    )

    assert response["queue_stats"] == {
        "active_tasks": 2,
        "scheduled_tasks": 1,
        "reserved_tasks": 3,
    }
    assert response["workers"][0] == {
        "worker": "worker-a",
        "pool": "prefork",
        "max_concurrency": 4,
        "processes": [1, 2],
        "total_tasks": {"reports.daily": 3},
    }
