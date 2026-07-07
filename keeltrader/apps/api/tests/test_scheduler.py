"""Scheduler unit tests."""

import asyncio
from datetime import datetime, timedelta

import pytest

import scheduler


def test_trade_sync_default_disabled():
    assert scheduler.settings.trade_sync_enabled is False


def test_trade_sync_due_uses_configured_interval():
    now = datetime(2026, 1, 1, 12, 0, 0)

    assert scheduler._trade_sync_due(None, now, 60) is True
    assert scheduler._trade_sync_due(now - timedelta(seconds=59), now, 60) is False
    assert scheduler._trade_sync_due(now - timedelta(seconds=60), now, 60) is True


@pytest.mark.asyncio
async def test_schedule_trade_sync_skips_when_previous_run_active(monkeypatch):
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_trade_sync():
        started.set()
        await release.wait()

    monkeypatch.setattr(scheduler, "_trade_sync_task", None)
    monkeypatch.setattr(scheduler, "_run_trade_sync", fake_trade_sync)

    assert scheduler._schedule_trade_sync() is True
    await started.wait()
    assert scheduler._schedule_trade_sync() is False

    release.set()
    await scheduler._trade_sync_task
    monkeypatch.setattr(scheduler, "_trade_sync_task", None)
