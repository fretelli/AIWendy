from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from domain.agentos.models import PortfolioInstrument
from services.agentos import AgentOSService


class FakeSession:
    def __init__(self, manual=None):
        self.manual = manual

    async def scalar(self, _query):
        return self.manual


class FakeTushare:
    def __init__(self, available=True):
        self.available = available
        self.calls = []

    async def latest_instrument_price(self, instrument_type, symbol, as_of):
        self.calls.append((instrument_type, symbol, as_of))
        if not self.available:
            return None
        return {"price": 12.5, "price_as_of": as_of, "source": f"tushare.{instrument_type}",
                "valuation_method": "published_close"}


def instrument(instrument_type: str) -> PortfolioInstrument:
    return PortfolioInstrument(id=uuid4(), user_id=uuid4(), symbol="TEST", provider_symbol="TEST.PRO",
        name="Test", market="CN", asset_class=instrument_type, instrument_type=instrument_type,
        currency="CNY", direction="long", multiplier=1, metadata_json={})


@pytest.mark.asyncio
@pytest.mark.parametrize("instrument_type", ["stock", "etf", "open_fund", "future", "option", "convertible_bond"])
async def test_official_instrument_types_use_their_provider_symbol(instrument_type):
    service = AgentOSService(FakeSession(), uuid4())
    service.tushare = FakeTushare()
    as_of = date(2026, 7, 31)
    result = await service._resolve_price(instrument(instrument_type), as_of, None, None)
    assert result["price_status"] == "current"
    assert result["price"] == Decimal("12.5")
    assert service.tushare.calls == [(instrument_type, "TEST.PRO", as_of)]


@pytest.mark.asyncio
async def test_official_price_wins_over_transaction_manual_price():
    as_of = date(2026, 7, 31)
    manual = SimpleNamespace(price=Decimal("99"), price_date=as_of)
    service = AgentOSService(FakeSession(manual), uuid4())
    service.tushare = FakeTushare(True)
    result = await service._resolve_price(instrument("stock"), as_of, Decimal("98"), as_of)
    assert result["price"] == Decimal("12.5")
    assert result["price_source"].startswith("tushare.")


@pytest.mark.asyncio
async def test_dated_manual_alternative_is_traceable_and_old_trade_price_expires():
    as_of = date(2026, 7, 31)
    manual = SimpleNamespace(price=Decimal("101.2"), price_date=as_of - timedelta(days=20))
    service = AgentOSService(FakeSession(manual), uuid4())
    service.tushare = FakeTushare(False)
    result = await service._resolve_price(instrument("alternative"), as_of, None, None)
    assert result["valuation_method"] == "dated_manual_nav"
    assert result["price_status"] == "current"

    service = AgentOSService(FakeSession(), uuid4())
    service.tushare = FakeTushare(False)
    expired = await service._resolve_price(instrument("manual"), as_of, Decimal("99"), as_of - timedelta(days=4))
    assert expired["price_status"] == "unavailable"
    assert expired["price"] is None
