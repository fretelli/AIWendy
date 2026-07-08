"""Market data API contract and data-source boundary tests."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.websockets import WebSocketDisconnect

from core.auth import create_access_token
from core.exceptions import InvalidTokenError


def test_market_data_routes_are_mounted(client):
    paths = {route.path for route in client.app.routes if hasattr(route, "path")}

    assert "/api/v1/market-data/historical/{symbol}" in paths
    assert "/api/v1/market-data/real-time/{symbol}" in paths
    assert "/api/v1/market-data/indicators/{symbol}/{indicator}" in paths
    assert "/api/v1/market-data/symbols/search" in paths


def test_market_data_adapter_compatibility_exports_are_preserved():
    from services.market_data_adapters import (
        AlphaVantageAdapter,
        MarketDataAdapter,
        MockDataAdapter,
        TwelveDataAdapter,
        YahooFinanceAdapter,
    )

    assert issubclass(TwelveDataAdapter, MarketDataAdapter)
    assert issubclass(AlphaVantageAdapter, MarketDataAdapter)
    assert issubclass(YahooFinanceAdapter, MarketDataAdapter)
    assert issubclass(MockDataAdapter, MarketDataAdapter)


def test_market_data_websocket_rejects_unauthenticated_client(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/market-data/ws/SPY"):
            pass

    assert exc.value.code == 1008


@pytest.mark.asyncio
async def test_market_data_not_found_is_not_masked_as_500(monkeypatch):
    from routers import market_data

    class FakeMarketDataService:
        async def get_historical_data(self, **kwargs):
            return []

    monkeypatch.setattr(market_data, "market_data_service", FakeMarketDataService())

    request = SimpleNamespace(cookies={}, headers={})
    current_user = SimpleNamespace(id=uuid4(), is_admin=False)

    with pytest.raises(HTTPException) as exc:
        await market_data.get_historical_data(
            "SPY",
            request,
            interval="1day",
            outputsize=60,
            start_date=None,
            end_date=None,
            current_user=current_user,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_market_data_websocket_accepts_access_token_cookie():
    from core.auth import get_websocket_user

    user_id = uuid4()
    token = create_access_token({"sub": str(user_id)})
    websocket = SimpleNamespace(headers={}, cookies={"keeltrader_access_token": token})
    session = _FakeSession(SimpleNamespace(id=user_id, email="user@example.com", is_active=True))

    user = await get_websocket_user(websocket, session)

    assert user.id == user_id


@pytest.mark.asyncio
async def test_market_data_websocket_rejects_invalid_token_cookie():
    from core.auth import get_websocket_user

    websocket = SimpleNamespace(headers={}, cookies={"keeltrader_access_token": "not-a-token"})

    with pytest.raises(InvalidTokenError):
        await get_websocket_user(websocket, _FakeSession())


@pytest.mark.asyncio
async def test_production_market_data_does_not_register_mock_adapter(monkeypatch):
    from config import get_settings
    from services.market_data_adapters import MockDataAdapter
    from services.market_data_service import MarketDataService

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("KEELTRADER_ENABLE_MOCK_MARKET_DATA", raising=False)
    monkeypatch.delenv("ENABLE_MOCK_MARKET_DATA", raising=False)
    get_settings.cache_clear()

    service = MarketDataService()
    try:
        assert not any(isinstance(adapter, MockDataAdapter) for adapter in service.adapters)
    finally:
        await service.close()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_mock_market_data_requires_explicit_non_production_opt_in(monkeypatch):
    from config import get_settings
    from services.market_data_adapters import MockDataAdapter
    from services.market_data_service import MarketDataService

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("KEELTRADER_ENABLE_MOCK_MARKET_DATA", "1")
    get_settings.cache_clear()

    service = MarketDataService()
    try:
        assert any(isinstance(adapter, MockDataAdapter) for adapter in service.adapters)
    finally:
        await service.close()
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_production_websocket_does_not_start_mock_stream(monkeypatch):
    from config import get_settings
    from services.market_data_websocket import MarketDataWebSocketService

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("KEELTRADER_ENABLE_MOCK_MARKET_DATA", raising=False)
    monkeypatch.delenv("ENABLE_MOCK_MARKET_DATA", raising=False)
    get_settings.cache_clear()

    def fail_create_task(*args, **kwargs):
        raise AssertionError("mock stream should not start in production")

    monkeypatch.setattr("services.market_data_websocket.asyncio.create_task", fail_create_task)
    service = MarketDataWebSocketService()
    websocket = _FakeWebSocket()

    await service.subscribe(websocket, "SPY")
    sent = list(websocket.sent)
    closed_code = websocket.closed_code
    await service.close()
    get_settings.cache_clear()

    assert sent == [
        {
            "type": "error",
            "code": "MARKET_DATA_STREAM_UNAVAILABLE",
            "message": "Real-time market data stream is unavailable.",
        }
    ]
    assert closed_code == 1013


@pytest.mark.asyncio
async def test_websocket_mock_stream_requires_explicit_non_production_opt_in(monkeypatch):
    from config import get_settings
    from services.market_data_websocket import MarketDataWebSocketService

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("KEELTRADER_ENABLE_MOCK_MARKET_DATA", "1")
    get_settings.cache_clear()

    created = []

    def fake_create_task(coro):
        created.append(coro)
        coro.close()
        return SimpleNamespace(cancel=lambda: None)

    monkeypatch.setattr("services.market_data_websocket.asyncio.create_task", fake_create_task)
    service = MarketDataWebSocketService()
    websocket = _FakeWebSocket()

    await service.subscribe(websocket, "SPY")
    sent = list(websocket.sent)
    closed_code = websocket.closed_code
    await service.close()
    get_settings.cache_clear()

    assert created
    assert sent == []
    assert closed_code is None


class _FakeScalarResult:
    def __init__(self, scalar=None):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class _FakeSession:
    def __init__(self, scalar=None):
        self.scalar = scalar

    async def execute(self, *args, **kwargs):
        return _FakeScalarResult(self.scalar)


class _FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed_code = None

    async def send_json(self, data):
        self.sent.append(data)

    async def close(self, code=1000):
        self.closed_code = code
