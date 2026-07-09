"""Read-only market price tools used as valuation context."""

from __future__ import annotations

import logging
from typing import Any

from ..exchange import ExchangeAdapter, create_adapter

logger = logging.getLogger(__name__)

_adapters: dict[str, ExchangeAdapter] = {}


async def _get_exchange(name: str = "okx") -> ExchangeAdapter:
    """Get or create a public-data exchange adapter without API keys."""
    if name not in _adapters:
        _adapters[name] = create_adapter(name, use_cache=True)
    return _adapters[name]


async def get_price(
    symbol: str,
    exchange: str = "okx",
) -> dict[str, Any]:
    """Get the latest price for valuation context.

    This tool intentionally does not expose chart, candle, momentum, or
    indicator calculations.
    """
    adapter = await _get_exchange(exchange)
    try:
        ticker = await adapter.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "exchange": exchange,
            "price": ticker.last,
            "bid": ticker.bid,
            "ask": ticker.ask,
            "high_24h": ticker.high_24h,
            "low_24h": ticker.low_24h,
            "volume_24h": ticker.volume_24h,
            "change_24h": ticker.change_24h,
            "change_pct_24h": ticker.change_pct_24h,
            "timestamp": ticker.timestamp,
            "usage": "valuation_context_only",
        }
    except Exception as e:
        logger.error("get_price failed for %s on %s: %s", symbol, exchange, e)
        return {"symbol": symbol, "exchange": exchange, "error": str(e)}
