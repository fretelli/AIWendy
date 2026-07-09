"""Task router hardening regressions."""

import sys
from importlib import import_module
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


class _FakeStates:
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class _FakeAsyncResult:
    def __init__(self, task_id, app=None):
        self.task_id = task_id
        self.state = _FakeStates.PENDING
        self.result = None
        self.info = None
        self.traceback = None

    def ready(self):
        return False

    def successful(self):
        return False

    def failed(self):
        return False


class _FakeTask:
    def delay(self, **kwargs):
        return SimpleNamespace(id="task-1")


sys.modules.setdefault("celery", SimpleNamespace(states=_FakeStates))
sys.modules.setdefault("celery.result", SimpleNamespace(AsyncResult=_FakeAsyncResult))
sys.modules.setdefault("domain.knowledge", SimpleNamespace())
sys.modules.setdefault(
    "domain.knowledge.models",
    SimpleNamespace(KnowledgeDocument=type("KnowledgeDocument", (), {})),
)
sys.modules.setdefault("workers", SimpleNamespace())
sys.modules.setdefault(
    "workers.celery_app",
    SimpleNamespace(celery_app=SimpleNamespace(control=SimpleNamespace())),
)
sys.modules.setdefault(
    "workers.knowledge_tasks",
    SimpleNamespace(ingest_knowledge_document=_FakeTask(), semantic_search=_FakeTask()),
)
sys.modules.setdefault(
    "workers.report_tasks",
    SimpleNamespace(
        generate_daily_report=_FakeTask(),
        generate_monthly_report=_FakeTask(),
        generate_weekly_report=_FakeTask(),
    ),
)

tasks = import_module("routers.tasks")
task_monitor = import_module("services.task_monitor")


class _FakeRedis:
    def __init__(self, owner):
        self.owner = owner

    async def get(self, key):
        return self.owner


class _FakeCache:
    def __init__(self, owner):
        self.owner = owner

    @property
    async def async_client(self):
        return _FakeRedis(self.owner)


class _ReadyResult:
    state = "SUCCESS"
    result = {"ok": True}
    info = None
    traceback = None

    def ready(self):
        return True

    def successful(self):
        return True

    def failed(self):
        return False


class _FakePubSub:
    def __init__(self):
        self.subscribed = []
        self.unsubscribed = []
        self.closed = False

    async def subscribe(self, channel):
        self.subscribed.append(channel)

    async def get_message(self, **kwargs):
        return None

    async def unsubscribe(self, channel):
        self.unsubscribed.append(channel)

    async def close(self):
        self.closed = True


class _FakeRedisClient:
    def __init__(self):
        self.pubsub_instance = _FakePubSub()

    def pubsub(self):
        return self.pubsub_instance


@pytest.mark.asyncio
async def test_task_owner_mismatch_preserves_forbidden(monkeypatch):
    owner_id = uuid4()
    current_user = SimpleNamespace(id=uuid4(), is_admin=False)

    monkeypatch.setattr(task_monitor, "get_cache_service", lambda: _FakeCache(str(owner_id)))

    with pytest.raises(HTTPException) as exc:
        await tasks._ensure_task_owner("task-1", current_user, "en")

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_task_owner_mismatch_in_status_is_not_masked_as_500(monkeypatch):
    owner_id = uuid4()
    current_user = SimpleNamespace(id=uuid4(), is_admin=False)
    request = SimpleNamespace(headers={}, cookies={})

    monkeypatch.setattr(task_monitor, "get_cache_service", lambda: _FakeCache(str(owner_id)))

    with pytest.raises(HTTPException) as exc:
        await tasks.get_task_status("task-1", request, current_user)

    assert exc.value.status_code == 403


def test_queued_task_response_shape():
    assert tasks._queued_task_response("task-1", "queued") == {
        "task_id": "task-1",
        "status": "queued",
        "message": "queued",
        "check_status_url": "/api/v1/tasks/status/task-1",
    }


@pytest.mark.asyncio
async def test_task_status_event_stream_emits_ready_snapshot_and_cleans_up():
    redis_client = _FakeRedisClient()
    events = []

    async for event in task_monitor.task_status_event_stream(
        "task-1",
        _ReadyResult(),
        redis_client,
    ):
        events.append(event)

    assert len(events) == 1
    assert '"ready": true' in events[0]
    assert redis_client.pubsub_instance.subscribed == ["task:events:task-1"]
    assert redis_client.pubsub_instance.unsubscribed == ["task:events:task-1"]
    assert redis_client.pubsub_instance.closed is True
