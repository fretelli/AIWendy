"""Portfolio tools — get_positions, get_balance, get_open_orders, get_trade_history.

Wraps ExchangeAdapter for account/portfolio data. Requires authenticated instances.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from ..exchange import ExchangeAdapter, create_adapter

logger = logging.getLogger(__name__)

# Authenticated adapter instances per user (managed by factory cache)


async def _get_user_adapter(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    trading_mode: str = "swap",
) -> ExchangeAdapter:
    """Get or create an authenticated exchange adapter instance."""
    return create_adapter(
        exchange_name=exchange_name,
        api_key=api_key,
        api_secret=api_secret,
        passphrase=passphrase,
        trading_mode=trading_mode,
        use_cache=True,
    )


async def get_balance(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    trading_mode: str = "swap",
) -> dict[str, Any]:
    """Get account balance.

    Args:
        exchange_name: Exchange name (okx, bybit)
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase (OKX)
        trading_mode: "spot" or "swap"

    Returns:
        Dict with total, free, used balances per currency
    """
    try:
        adapter = await _get_user_adapter(exchange_name, api_key, api_secret, passphrase, trading_mode)
        balances = await adapter.fetch_balance()
        non_zero = {}
        for b in balances:
            non_zero[b.currency] = {
                "total": b.total,
                "free": b.free,
                "used": b.used,
            }
        return {
            "exchange": exchange_name,
            "balances": non_zero,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("get_balance failed on %s: %s", exchange_name, e)
        return {"exchange": exchange_name, "error": str(e)}


async def get_positions(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    symbol: str | None = None,
    trading_mode: str = "swap",
) -> list[dict[str, Any]]:
    """Get open positions (futures/perpetual).

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter for specific symbol
        trading_mode: "spot" or "swap"

    Returns:
        List of position dicts
    """
    if trading_mode == "spot":
        return [{"info": "Spot mode — no futures positions. Use get_balance() to check holdings."}]
    try:
        adapter = await _get_user_adapter(exchange_name, api_key, api_secret, passphrase, trading_mode)
        positions = await adapter.fetch_positions(symbol)
        return [
            {
                "symbol": pos.symbol,
                "side": pos.side,
                "size": pos.size,
                "notional": pos.notional,
                "entry_price": pos.entry_price,
                "mark_price": pos.mark_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "leverage": pos.leverage,
                "liquidation_price": pos.liquidation_price,
                "margin_mode": pos.margin_mode,
                "timestamp": pos.timestamp,
            }
            for pos in positions
        ]
    except Exception as e:
        logger.error("get_positions failed on %s: %s", exchange_name, e)
        return []


async def get_open_orders(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    symbol: str | None = None,
    trading_mode: str = "swap",
) -> list[dict[str, Any]]:
    """Get open orders.

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter for specific symbol
        trading_mode: "spot" or "swap"

    Returns:
        List of order dicts
    """
    try:
        adapter = await _get_user_adapter(exchange_name, api_key, api_secret, passphrase, trading_mode)
        orders = await adapter.fetch_open_orders(symbol)
        return [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side,
                "type": o.order_type,
                "price": o.price,
                "amount": o.amount,
                "filled": o.filled,
                "remaining": o.remaining,
                "status": o.status,
                "timestamp": o.timestamp,
            }
            for o in orders
        ]
    except Exception as e:
        logger.error("get_open_orders failed on %s: %s", exchange_name, e)
        return []


async def get_trade_history(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    symbol: str | None = None,
    days: int = 7,
    trading_mode: str = "swap",
) -> list[dict[str, Any]]:
    """Get trade history.

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter
        days: Number of days to look back
        trading_mode: "spot" or "swap"

    Returns:
        List of trade dicts
    """
    try:
        adapter = await _get_user_adapter(exchange_name, api_key, api_secret, passphrase, trading_mode)
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        trades = await adapter.fetch_my_trades(symbol, since=since, limit=100)
        return [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "price": t.price,
                "amount": t.amount,
                "cost": t.cost,
                "fee": t.fee_cost,
                "fee_currency": t.fee_currency,
                "timestamp": t.timestamp,
            }
            for t in trades
        ]
    except Exception as e:
        logger.error("get_trade_history failed on %s: %s", exchange_name, e)
        return []
