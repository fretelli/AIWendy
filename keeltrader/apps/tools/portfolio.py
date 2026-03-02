"""Portfolio tools — get_positions, get_balance, get_open_orders, get_trade_history.

Wraps CCXT for account/portfolio data. Requires authenticated exchange instances.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import ccxt.async_support as ccxt

from ._proxy import apply_proxy

logger = logging.getLogger(__name__)

# Authenticated exchange instances per user
_user_exchanges: dict[str, ccxt.Exchange] = {}


async def _get_user_exchange(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
) -> ccxt.Exchange:
    """Get or create an authenticated CCXT exchange instance."""
    cache_key = f"{exchange_name}:{api_key[:8]}"
    if cache_key not in _user_exchanges:
        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {exchange_name}")
        config: dict[str, Any] = apply_proxy({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        if passphrase:
            config["password"] = passphrase
        _user_exchanges[cache_key] = exchange_class(config)
    return _user_exchanges[cache_key]


async def get_balance(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
) -> dict[str, Any]:
    """Get account balance.

    Args:
        exchange_name: Exchange name (binance, okx, bybit)
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase (OKX)

    Returns:
        Dict with total, free, used balances per currency
    """
    try:
        ex = await _get_user_exchange(exchange_name, api_key, api_secret, passphrase)
        balance = await ex.fetch_balance()
        # Filter out zero balances
        non_zero = {}
        for currency, amounts in balance.get("total", {}).items():
            if amounts and float(amounts) > 0:
                non_zero[currency] = {
                    "total": float(balance["total"].get(currency, 0)),
                    "free": float(balance["free"].get(currency, 0)),
                    "used": float(balance["used"].get(currency, 0)),
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
) -> list[dict[str, Any]]:
    """Get open positions (futures/perpetual).

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter for specific symbol

    Returns:
        List of position dicts
    """
    try:
        ex = await _get_user_exchange(exchange_name, api_key, api_secret, passphrase)
        symbols = [symbol] if symbol else None
        positions = await ex.fetch_positions(symbols)
        result = []
        for pos in positions:
            size = float(pos.get("contracts", 0) or 0)
            if size == 0:
                continue
            result.append({
                "symbol": pos.get("symbol"),
                "side": pos.get("side"),
                "size": size,
                "notional": float(pos.get("notional", 0) or 0),
                "entry_price": float(pos.get("entryPrice", 0) or 0),
                "mark_price": float(pos.get("markPrice", 0) or 0),
                "unrealized_pnl": float(pos.get("unrealizedPnl", 0) or 0),
                "leverage": float(pos.get("leverage", 1) or 1),
                "liquidation_price": pos.get("liquidationPrice"),
                "margin_mode": pos.get("marginMode"),
                "timestamp": pos.get("datetime"),
            })
        return result
    except Exception as e:
        logger.error("get_positions failed on %s: %s", exchange_name, e)
        return []


async def get_open_orders(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    """Get open orders.

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter for specific symbol

    Returns:
        List of order dicts
    """
    try:
        ex = await _get_user_exchange(exchange_name, api_key, api_secret, passphrase)
        orders = await ex.fetch_open_orders(symbol)
        return [
            {
                "id": o.get("id"),
                "symbol": o.get("symbol"),
                "side": o.get("side"),
                "type": o.get("type"),
                "price": o.get("price"),
                "amount": o.get("amount"),
                "filled": o.get("filled"),
                "remaining": o.get("remaining"),
                "status": o.get("status"),
                "timestamp": o.get("datetime"),
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
) -> list[dict[str, Any]]:
    """Get trade history.

    Args:
        exchange_name: Exchange name
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        symbol: Optional filter
        days: Number of days to look back

    Returns:
        List of trade dicts
    """
    try:
        ex = await _get_user_exchange(exchange_name, api_key, api_secret, passphrase)
        since = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
        trades = await ex.fetch_my_trades(symbol, since=since, limit=100)
        return [
            {
                "id": t.get("id"),
                "symbol": t.get("symbol"),
                "side": t.get("side"),
                "price": float(t.get("price", 0)),
                "amount": float(t.get("amount", 0)),
                "cost": float(t.get("cost", 0)),
                "fee": t.get("fee", {}).get("cost"),
                "fee_currency": t.get("fee", {}).get("currency"),
                "timestamp": t.get("datetime"),
            }
            for t in trades
        ]
    except Exception as e:
        logger.error("get_trade_history failed on %s: %s", exchange_name, e)
        return []
