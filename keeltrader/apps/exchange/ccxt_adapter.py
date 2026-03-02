"""CCXT adapter — wraps CCXT async exchanges behind the ExchangeAdapter interface.

Handles all 5 crypto exchanges (Binance, OKX, Bybit, Coinbase, Kraken).
Proxy injection, trading mode, and passphrase are handled at construction time.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import ccxt.async_support as ccxt

from .base import (
    ExchangeAdapter,
    UnifiedBalance,
    UnifiedOrder,
    UnifiedPosition,
    UnifiedTicker,
    UnifiedTrade,
)

logger = logging.getLogger(__name__)


def _apply_proxy(config: dict) -> dict:
    """Inject aiohttp_proxy into config if proxy env vars are set."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    if proxy:
        config["aiohttp_proxy"] = proxy
    return config


class CcxtAdapter(ExchangeAdapter):
    """Adapter for all CCXT-supported crypto exchanges."""

    def __init__(
        self,
        exchange_name: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        passphrase: str | None = None,
        trading_mode: str = "swap",
        is_testnet: bool = False,
    ):
        self._exchange_name = exchange_name
        self._trading_mode = trading_mode
        self._authenticated = bool(api_key and api_secret)

        exchange_class = getattr(ccxt, exchange_name, None)
        if exchange_class is None:
            raise ValueError(f"Unknown CCXT exchange: {exchange_name}")

        config: dict[str, Any] = _apply_proxy({"enableRateLimit": True})

        if api_key and api_secret:
            config["apiKey"] = api_key
            config["secret"] = api_secret
            config["options"] = {"defaultType": trading_mode}
            if passphrase:
                config["password"] = passphrase
            if is_testnet:
                config["sandbox"] = True

        self._exchange: ccxt.Exchange = exchange_class(config)

    @property
    def name(self) -> str:
        return self._exchange_name

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated

    @property
    def exchange(self) -> ccxt.Exchange:
        """Direct access to underlying CCXT exchange (for edge cases)."""
        return self._exchange

    # --- Account / Portfolio ---

    async def fetch_balance(self) -> list[UnifiedBalance]:
        raw = await self._exchange.fetch_balance()
        result = []
        for currency, amount in raw.get("total", {}).items():
            if amount and float(amount) > 0:
                result.append(UnifiedBalance(
                    currency=currency,
                    total=float(raw["total"].get(currency, 0)),
                    free=float(raw["free"].get(currency, 0)),
                    used=float(raw["used"].get(currency, 0)),
                ))
        return result

    async def fetch_positions(
        self, symbol: str | None = None,
    ) -> list[UnifiedPosition]:
        symbols = [symbol] if symbol else None
        raw_positions = await self._exchange.fetch_positions(symbols)
        result = []
        for pos in raw_positions:
            size = float(pos.get("contracts", 0) or 0)
            if size == 0:
                continue
            result.append(UnifiedPosition(
                symbol=pos.get("symbol", ""),
                side=pos.get("side", ""),
                size=size,
                notional=float(pos.get("notional", 0) or 0),
                entry_price=float(pos.get("entryPrice", 0) or 0),
                mark_price=float(pos.get("markPrice", 0) or 0),
                unrealized_pnl=float(pos.get("unrealizedPnl", 0) or 0),
                leverage=float(pos.get("leverage", 1) or 1),
                liquidation_price=pos.get("liquidationPrice"),
                margin_mode=pos.get("marginMode"),
                timestamp=pos.get("datetime"),
            ))
        return result

    async def fetch_open_orders(
        self, symbol: str | None = None,
    ) -> list[UnifiedOrder]:
        raw_orders = await self._exchange.fetch_open_orders(symbol)
        return [
            UnifiedOrder(
                id=o.get("id", ""),
                symbol=o.get("symbol", ""),
                side=o.get("side", ""),
                order_type=o.get("type", ""),
                price=o.get("price"),
                amount=float(o.get("amount", 0) or 0),
                filled=float(o.get("filled", 0) or 0),
                remaining=float(o.get("remaining", 0) or 0),
                status=o.get("status", ""),
                timestamp=o.get("datetime"),
            )
            for o in raw_orders
        ]

    async def fetch_my_trades(
        self,
        symbol: str | None = None,
        since: int | None = None,
        limit: int = 100,
    ) -> list[UnifiedTrade]:
        raw_trades = await self._exchange.fetch_my_trades(symbol, since=since, limit=limit)
        return [
            UnifiedTrade(
                id=t.get("id", ""),
                symbol=t.get("symbol", ""),
                side=t.get("side", ""),
                price=float(t.get("price", 0) or 0),
                amount=float(t.get("amount", 0) or 0),
                cost=float(t.get("cost", 0) or 0),
                fee_cost=(t.get("fee") or {}).get("cost"),
                fee_currency=(t.get("fee") or {}).get("currency"),
                timestamp=t.get("datetime"),
                raw=t,
            )
            for t in raw_trades
        ]

    # --- Execution ---

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> UnifiedOrder:
        result = await self._exchange.create_order(
            symbol=symbol,
            type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params or {},
        )
        return UnifiedOrder(
            id=result.get("id", ""),
            symbol=symbol,
            side=side,
            order_type=order_type,
            amount=amount,
            price=result.get("price"),
            filled=float(result.get("filled", 0) or 0),
            remaining=float(result.get("remaining", 0) or 0),
            status=result.get("status", ""),
            cost=result.get("cost"),
            average=result.get("average"),
            timestamp=result.get("datetime"),
        )

    async def cancel_order(
        self, order_id: str, symbol: str,
    ) -> dict[str, Any]:
        result = await self._exchange.cancel_order(order_id, symbol)
        return {
            "order_id": order_id,
            "status": result.get("status", "cancelled"),
        }

    # --- Public Market Data ---

    async def fetch_ticker(self, symbol: str) -> UnifiedTicker:
        raw = await self._exchange.fetch_ticker(symbol)
        return UnifiedTicker(
            symbol=symbol,
            last=raw.get("last"),
            bid=raw.get("bid"),
            ask=raw.get("ask"),
            high_24h=raw.get("high"),
            low_24h=raw.get("low"),
            volume_24h=raw.get("baseVolume"),
            change_24h=raw.get("change"),
            change_pct_24h=raw.get("percentage"),
            timestamp=raw.get("datetime"),
        )

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[list[float]]:
        return await self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def fetch_order_book(
        self, symbol: str, limit: int = 10,
    ) -> dict[str, Any]:
        return await self._exchange.fetch_order_book(symbol, limit=limit)

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        raw = await self._exchange.fetch_funding_rate(symbol)
        return {
            "symbol": symbol,
            "funding_rate": raw.get("fundingRate"),
            "funding_timestamp": raw.get("fundingDatetime"),
            "next_funding_time": raw.get("nextFundingDatetime"),
            "mark_price": raw.get("markPrice"),
            "index_price": raw.get("indexPrice"),
        }

    # --- Sync wrappers (for legacy synchronous callers) ---

    def fetch_balance_sync(self) -> dict[str, Any]:
        """Synchronous fetch_balance using the underlying sync CCXT exchange.

        Used by services that haven't migrated to async (trade_sync, exchange_service).
        Creates a temporary sync exchange instance.
        """
        import ccxt as ccxt_sync

        exchange_class = getattr(ccxt_sync, self._exchange_name)
        config: dict[str, Any] = {"enableRateLimit": True}
        if self._exchange.apiKey:
            config["apiKey"] = self._exchange.apiKey
            config["secret"] = self._exchange.secret
            config["options"] = {"defaultType": self._trading_mode}
            if hasattr(self._exchange, "password") and self._exchange.password:
                config["password"] = self._exchange.password
            if self._exchange.urls.get("test"):
                config["sandbox"] = True
        ex = exchange_class(config)
        try:
            return ex.fetch_balance()
        finally:
            if hasattr(ex, "close"):
                try:
                    ex.close()
                except Exception:
                    pass

    def fetch_my_trades_sync(
        self,
        symbol: str | None = None,
        since: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Synchronous fetch_my_trades for legacy callers."""
        import ccxt as ccxt_sync

        exchange_class = getattr(ccxt_sync, self._exchange_name)
        config: dict[str, Any] = {"enableRateLimit": True}
        if self._exchange.apiKey:
            config["apiKey"] = self._exchange.apiKey
            config["secret"] = self._exchange.secret
            config["options"] = {"defaultType": self._trading_mode}
            if hasattr(self._exchange, "password") and self._exchange.password:
                config["password"] = self._exchange.password
        ex = exchange_class(config)
        try:
            return ex.fetch_my_trades(symbol, since=since, limit=limit)
        finally:
            if hasattr(ex, "close"):
                try:
                    ex.close()
                except Exception:
                    pass

    # --- Lifecycle ---

    async def close(self) -> None:
        await self._exchange.close()
