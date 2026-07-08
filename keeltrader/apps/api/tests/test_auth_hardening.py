"""Authentication hardening regression tests."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.auth.password_reset import PasswordResetService
from services.auth.sessions import AuthSessionService


def test_auth_routes_are_mounted(client):
    paths = {route.path for route in client.app.routes if hasattr(route, "path")}

    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/sessions" in paths
    assert "/api/v1/auth/forgot-password" in paths
    assert "/api/v1/auth/reset-password" in paths
    assert "/api/v1/auth/google" in paths


@pytest.mark.asyncio
async def test_password_reset_default_disabled_does_not_touch_redis(monkeypatch):
    service = PasswordResetService()
    monkeypatch.setattr(service, "settings", SimpleNamespace(password_reset_enabled=False))

    def fail_redis():
        raise AssertionError("redis should not be used when password reset is disabled")

    monkeypatch.setattr("services.auth.password_reset.get_redis_client", fail_redis)

    result = await service.request_reset(_FailingSession(), "user@example.com")

    assert result.enabled is False
    assert result.user_exists is False
    assert result.token is None


@pytest.mark.asyncio
async def test_password_reset_disabled_rejects_reset(monkeypatch):
    service = PasswordResetService()
    monkeypatch.setattr(service, "settings", SimpleNamespace(password_reset_enabled=False))

    ok = await service.reset_password(_FailingSession(), "token", "NewPassword1")

    assert ok is False


@pytest.mark.asyncio
async def test_session_service_issues_tokens_and_writes_redis(monkeypatch):
    redis = _FakeRedis()
    monkeypatch.setattr("services.auth.sessions.get_redis_client", lambda: redis)
    service = AuthSessionService()
    monkeypatch.setattr(service, "settings", SimpleNamespace(jwt_expire_minutes=30))

    session = _FakeSession()
    user = SimpleNamespace(id=uuid4())

    tokens = await service.issue_tokens(session, user)

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.expires_in == 1800
    assert session.committed is True
    assert len(session.added) == 1
    assert redis.setex_calls == [(f"session:{tokens.session_id}", 1800, str(user.id))]


@pytest.mark.asyncio
async def test_revoke_db_session_deletes_redis_and_marks_revoked(monkeypatch):
    redis = _FakeRedis()
    monkeypatch.setattr("services.auth.sessions.get_redis_client", lambda: redis)
    service = AuthSessionService()
    user_session = SimpleNamespace(id=uuid4(), revoked_at=None)
    session = _FakeSession(scalar=user_session)

    assert await service.revoke_db_session(session, str(user_session.id)) is True

    assert user_session.revoked_at is not None
    assert session.committed is True
    assert redis.deleted == [f"session:{user_session.id}"]


class _FailingSession:
    async def execute(self, *args, **kwargs):
        raise AssertionError("database should not be used")


class _FakeScalarResult:
    def __init__(self, scalar=None, items=None):
        self._scalar = scalar
        self._items = items or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        return self

    def all(self):
        return self._items


class _FakeSession:
    def __init__(self, scalar=None):
        self.scalar = scalar
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = datetime.utcnow()
            if getattr(item, "last_activity_at", None) is None:
                item.last_activity_at = datetime.utcnow()
            if getattr(item, "expires_at", None) is None:
                item.expires_at = datetime.utcnow() + timedelta(minutes=30)

    async def commit(self):
        self.committed = True

    async def execute(self, *args, **kwargs):
        return _FakeScalarResult(self.scalar)


class _FakeRedis:
    def __init__(self):
        self.setex_calls = []
        self.deleted = []
        self.values = {}

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)
