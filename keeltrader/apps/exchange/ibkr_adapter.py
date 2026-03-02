"""IBKR adapter — connects to IB Gateway via ib_async (TCP :4001).

Sprint B: Read-only operations (balance, positions, orders, trades, market data).
Sprint C will add order execution.

Requires ib_async>=1.0.0 and a running IB Gateway or TWS instance.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from .base import (
    ExchangeAdapter,
    UnifiedBalance,
    UnifiedOrder,
    UnifiedPosition,
    UnifiedTicker,
    UnifiedTrade,
)
from .ibkr_contracts import (
    contract_to_symbol,
    detect_asset_class,
    parse_symbol,
    symbol_to_contract,
)

logger = logging.getLogger(__name__)

# Lazy import ib_async
_ib_async = None


def _get_ib():
    global _ib_async
    if _ib_async is None:
        try:
            import ib_async
            _ib_async = ib_async
        except ImportError:
            raise ImportError(
                "ib_async is required for IBKR support. "
                "Install with: pip install ib_async>=1.0.0"
            )
    return _ib_async


class IbkrAdapter(ExchangeAdapter):
    """Adapter for Interactive Brokers via IB Gateway/TWS.

    Uses ib_async for async TCP communication with IB Gateway.
    """

    def __init__(
        self,
        gateway_host: str = "127.0.0.1",
        gateway_port: int = 4001,
        client_id: int = 1,
        trading_mode: str = "stock",
        username: str | None = None,
        readonly: bool = True,
    ):
        self._gateway_host = gateway_host
        self._gateway_port = gateway_port
        self._client_id = client_id
        self._trading_mode = trading_mode
        self._username = username
        self._readonly = readonly
        self._ib = None
        self._connected = False

    @property
    def name(self) -> str:
        return "ibkr"

    @property
    def is_authenticated(self) -> bool:
        return self._connected

    async def _ensure_connected(self) -> Any:
        """Ensure we have an active IB connection."""
        ib = _get_ib()

        if self._ib is None:
            self._ib = ib.IB()

        if not self._ib.isConnected():
            logger.info(
                "Connecting to IB Gateway at %s:%s (client_id=%s, readonly=%s)",
                self._gateway_host, self._gateway_port, self._client_id, self._readonly,
            )
            await self._ib.connectAsync(
                host=self._gateway_host,
                port=self._gateway_port,
                clientId=self._client_id,
                readonly=self._readonly,
            )
            self._connected = True
            logger.info("Connected to IB Gateway")

        return self._ib

    # --- Account / Portfolio ---

    async def fetch_balance(self) -> list[UnifiedBalance]:
        ib_conn = await self._ensure_connected()

        # Request account summary
        account_values = ib_conn.accountSummary()
        if not account_values:
            # If no cached data, request it
            ib_conn.reqAccountSummary()
            await asyncio.sleep(2)
            account_values = ib_conn.accountSummary()

        balances = []
        seen_tags = set()
        for av in account_values:
            if av.tag == "TotalCashValue" and av.currency not in seen_tags:
                seen_tags.add(av.currency)
                balances.append(UnifiedBalance(
                    currency=av.currency,
                    total=float(av.value),
                    free=float(av.value),
                    used=0.0,
                ))

        # Also add NetLiquidation as a summary entry
        for av in account_values:
            if av.tag == "NetLiquidation" and av.currency == "USD":
                balances.insert(0, UnifiedBalance(
                    currency="NetLiquidation",
                    total=float(av.value),
                    free=float(av.value),
                    used=0.0,
                ))
                break

        return balances

    async def fetch_positions(
        self, symbol: str | None = None,
    ) -> list[UnifiedPosition]:
        ib_conn = await self._ensure_connected()

        positions = ib_conn.positions()
        result = []

        for pos in positions:
            contract = pos.contract
            pos_symbol = contract_to_symbol(contract)

            if symbol and pos_symbol != symbol:
                continue

            size = float(pos.position)
            if size == 0:
                continue

            # Detect asset class from contract type
            ib = _get_ib()
            if isinstance(contract, ib.Stock):
                asset_class = "stock"
            elif isinstance(contract, ib.Option):
                asset_class = "option"
            elif isinstance(contract, ib.Future):
                asset_class = "future"
            else:
                asset_class = "other"

            result.append(UnifiedPosition(
                symbol=pos_symbol,
                side="long" if size > 0 else "short",
                size=abs(size),
                notional=abs(size) * float(pos.avgCost),
                entry_price=float(pos.avgCost),
                mark_price=float(pos.marketPrice) if hasattr(pos, "marketPrice") else 0.0,
                unrealized_pnl=float(pos.unrealizedPNL) if hasattr(pos, "unrealizedPNL") else 0.0,
                leverage=1.0,  # Stocks have no leverage; margin is separate
                asset_class=asset_class,
            ))

        return result

    async def fetch_open_orders(
        self, symbol: str | None = None,
    ) -> list[UnifiedOrder]:
        ib_conn = await self._ensure_connected()

        open_orders = ib_conn.openOrders()
        result = []

        for trade in ib_conn.openTrades():
            contract = trade.contract
            order = trade.order
            order_status = trade.orderStatus

            order_symbol = contract_to_symbol(contract)
            if symbol and order_symbol != symbol:
                continue

            # Detect asset class
            asset_class = detect_asset_class(order_symbol)

            result.append(UnifiedOrder(
                id=str(order.orderId),
                symbol=order_symbol,
                side="buy" if order.action == "BUY" else "sell",
                order_type=_map_ib_order_type(order.orderType),
                price=float(order.lmtPrice) if order.lmtPrice else None,
                amount=float(order.totalQuantity),
                filled=float(order_status.filled),
                remaining=float(order_status.remaining),
                status=order_status.status.lower(),
                asset_class=asset_class,
            ))

        return result

    async def fetch_my_trades(
        self,
        symbol: str | None = None,
        since: int | None = None,
        limit: int = 100,
    ) -> list[UnifiedTrade]:
        ib_conn = await self._ensure_connected()

        # Request execution reports
        fills = ib_conn.fills()
        result = []

        for fill in fills:
            contract = fill.contract
            execution = fill.execution
            commission_report = fill.commissionReport

            trade_symbol = contract_to_symbol(contract)
            if symbol and trade_symbol != symbol:
                continue

            # Filter by time
            trade_time = execution.time
            if since and trade_time:
                trade_ts = int(trade_time.timestamp() * 1000) if hasattr(trade_time, "timestamp") else 0
                if trade_ts < since:
                    continue

            asset_class = detect_asset_class(trade_symbol)

            result.append(UnifiedTrade(
                id=execution.execId,
                symbol=trade_symbol,
                side="buy" if execution.side == "BOT" else "sell",
                price=float(execution.price),
                amount=float(execution.shares),
                cost=float(execution.price) * float(execution.shares),
                fee_cost=float(commission_report.commission) if commission_report else None,
                fee_currency=commission_report.currency if commission_report else None,
                asset_class=asset_class,
                timestamp=str(trade_time) if trade_time else None,
                raw={
                    "execId": execution.execId,
                    "orderId": execution.orderId,
                    "exchange": execution.exchange,
                    "side": execution.side,
                },
            ))

        return result[:limit]

    # --- Execution (Sprint C — currently raises for read-only) ---

    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> UnifiedOrder:
        if self._readonly:
            raise PermissionError(
                "IBKR adapter is in read-only mode. "
                "Set READ_ONLY_API=no in IB Gateway config to enable trading."
            )

        ib_conn = await self._ensure_connected()
        ib = _get_ib()

        # Parse symbol to IB Contract
        parsed = parse_symbol(symbol, default_asset_class=self._trading_mode)
        contract = symbol_to_contract(symbol, asset_class=parsed.asset_class)

        # Qualify contract
        qualified = await ib_conn.qualifyContractsAsync(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract for symbol: {symbol}")
        contract = qualified[0]

        # Build IB Order
        action = "BUY" if side.lower() == "buy" else "SELL"
        ib_order_type = _map_to_ib_order_type(order_type)

        order = ib.Order(
            action=action,
            totalQuantity=amount,
            orderType=ib_order_type,
        )

        if price and ib_order_type in ("LMT", "STP_LMT"):
            order.lmtPrice = price
        if price and ib_order_type in ("STP", "STP_LMT"):
            order.auxPrice = price

        # Handle extra params
        if params:
            if params.get("outsideRth"):
                order.outsideRth = True
            if params.get("tif"):
                order.tif = params["tif"]

        # Place order
        trade = ib_conn.placeOrder(contract, order)

        # Wait briefly for initial status
        await asyncio.sleep(1)

        return UnifiedOrder(
            id=str(trade.order.orderId),
            symbol=symbol,
            side=side,
            order_type=order_type,
            price=price,
            amount=amount,
            filled=float(trade.orderStatus.filled),
            remaining=float(trade.orderStatus.remaining),
            status=trade.orderStatus.status.lower(),
            asset_class=parsed.asset_class,
        )

    async def cancel_order(
        self, order_id: str, symbol: str,
    ) -> dict[str, Any]:
        if self._readonly:
            raise PermissionError("IBKR adapter is in read-only mode.")

        ib_conn = await self._ensure_connected()

        # Find the trade by order ID
        for trade in ib_conn.openTrades():
            if str(trade.order.orderId) == order_id:
                ib_conn.cancelOrder(trade.order)
                await asyncio.sleep(1)
                return {
                    "order_id": order_id,
                    "status": "cancelled",
                }

        return {
            "order_id": order_id,
            "status": "not_found",
        }

    # --- Public Market Data ---

    async def fetch_ticker(self, symbol: str) -> UnifiedTicker:
        ib_conn = await self._ensure_connected()

        parsed = parse_symbol(symbol, default_asset_class=self._trading_mode)
        contract = symbol_to_contract(symbol, asset_class=parsed.asset_class)

        # Qualify contract
        qualified = await ib_conn.qualifyContractsAsync(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract: {symbol}")
        contract = qualified[0]

        # Request snapshot market data
        ticker = ib_conn.reqMktData(contract, snapshot=True)
        # Wait for data
        for _ in range(20):  # 2 seconds max
            await asyncio.sleep(0.1)
            if ticker.last is not None or ticker.close is not None:
                break

        price = ticker.last if ticker.last is not None else ticker.close

        return UnifiedTicker(
            symbol=symbol,
            last=float(price) if price is not None else None,
            bid=float(ticker.bid) if ticker.bid is not None else None,
            ask=float(ticker.ask) if ticker.ask is not None else None,
            high_24h=float(ticker.high) if ticker.high is not None else None,
            low_24h=float(ticker.low) if ticker.low is not None else None,
            volume_24h=float(ticker.volume) if ticker.volume is not None else None,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[list[float]]:
        ib_conn = await self._ensure_connected()

        parsed = parse_symbol(symbol, default_asset_class=self._trading_mode)
        contract = symbol_to_contract(symbol, asset_class=parsed.asset_class)

        qualified = await ib_conn.qualifyContractsAsync(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract: {symbol}")
        contract = qualified[0]

        # Map timeframe to IB format
        bar_size = _map_timeframe(timeframe)
        duration = _calc_duration(timeframe, limit)

        bars = await ib_conn.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
        )

        result = []
        for bar in bars:
            ts = int(bar.date.timestamp() * 1000) if hasattr(bar.date, "timestamp") else 0
            result.append([ts, bar.open, bar.high, bar.low, bar.close, bar.volume])

        return result[-limit:]

    async def fetch_order_book(
        self, symbol: str, limit: int = 10,
    ) -> dict[str, Any]:
        ib_conn = await self._ensure_connected()

        parsed = parse_symbol(symbol, default_asset_class=self._trading_mode)
        contract = symbol_to_contract(symbol, asset_class=parsed.asset_class)

        qualified = await ib_conn.qualifyContractsAsync(contract)
        if not qualified:
            raise ValueError(f"Could not qualify contract: {symbol}")
        contract = qualified[0]

        # Request market depth
        depth_data = ib_conn.reqMktDepth(contract, numRows=limit)
        await asyncio.sleep(2)  # Wait for depth data

        ticker = depth_data
        bids = []
        asks = []

        if hasattr(ticker, "domBids"):
            for entry in (ticker.domBids or [])[:limit]:
                bids.append([float(entry.price), float(entry.size)])
        if hasattr(ticker, "domAsks"):
            for entry in (ticker.domAsks or [])[:limit]:
                asks.append([float(entry.price), float(entry.size)])

        return {"bids": bids, "asks": asks}

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "info": "Funding rate not applicable for IBKR"}

    # --- Connection Test ---

    async def test_connection(self) -> dict[str, Any]:
        try:
            ib_conn = await self._ensure_connected()
            accounts = ib_conn.managedAccounts()
            return {
                "success": True,
                "message": "Connected to IB Gateway",
                "data": {
                    "exchange": "ibkr",
                    "accounts": accounts,
                    "username": self._username or "unknown",
                },
            }
        except Exception as e:
            return {"success": False, "message": f"IB Gateway connection failed: {e}"}

    # --- Lifecycle ---

    async def close(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
            logger.info("Disconnected from IB Gateway")
        self._connected = False


# --- Helper functions ---

def _map_ib_order_type(ib_type: str) -> str:
    """Map IB order type to unified format."""
    mapping = {
        "MKT": "market",
        "LMT": "limit",
        "STP": "stop",
        "STP LMT": "stop_limit",
        "TRAIL": "trailing_stop",
    }
    return mapping.get(ib_type, ib_type.lower())


def _map_to_ib_order_type(unified_type: str) -> str:
    """Map unified order type to IB format."""
    mapping = {
        "market": "MKT",
        "limit": "LMT",
        "stop": "STP",
        "stop_limit": "STP_LMT",
        "trailing_stop": "TRAIL",
    }
    return mapping.get(unified_type.lower(), "MKT")


def _map_timeframe(timeframe: str) -> str:
    """Map common timeframe strings to IB bar sizes."""
    mapping = {
        "1m": "1 min",
        "5m": "5 mins",
        "15m": "15 mins",
        "30m": "30 mins",
        "1h": "1 hour",
        "4h": "4 hours",
        "1d": "1 day",
        "1w": "1 week",
    }
    return mapping.get(timeframe, "1 hour")


def _calc_duration(timeframe: str, limit: int) -> str:
    """Calculate IB duration string from timeframe and bar count."""
    multipliers = {
        "1m": limit,             # minutes
        "5m": limit * 5,
        "15m": limit * 15,
        "30m": limit * 30,
        "1h": limit,             # hours
        "4h": limit * 4,
        "1d": limit,             # days
        "1w": limit * 7,
    }
    minutes = multipliers.get(timeframe, limit * 60)

    if timeframe in ("1d", "1w"):
        days = minutes
        if days > 365:
            return f"{days // 365} Y"
        return f"{days} D"

    if minutes > 1440:  # More than a day
        days = minutes // 1440 + 1
        return f"{days} D"

    return f"{minutes * 60} S"
