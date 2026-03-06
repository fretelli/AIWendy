"""Exchange adapter ABC and unified data classes.

Defines the contract that all exchange adapters (CCXT, IBKR, etc.) must implement.
Data classes provide a normalized view regardless of the underlying exchange.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class UnifiedBalance:
    """Normalized account balance."""

    currency: str
    total: float = 0.0
    free: float = 0.0
    used: float = 0.0


@dataclass
class UnifiedPosition:
    """Normalized open position."""

    symbol: str
    side: str  # "long" or "short"
    size: float = 0.0
    notional: float = 0.0
    entry_price: float = 0.0
    mark_price: float = 0.0
    unrealized_pnl: float = 0.0
    leverage: float = 1.0
    liquidation_price: float | None = None
    margin_mode: str | None = None
    asset_class: str = "crypto"
    timestamp: str | None = None


@dataclass
class UnifiedOrder:
    """Normalized order."""

    id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit", "stop", etc.
    price: float | None = None
    amount: float = 0.0
    filled: float = 0.0
    remaining: float = 0.0
    status: str = ""
    cost: float | None = None
    average: float | None = None
    asset_class: str = "crypto"
    timestamp: str | None = None


@dataclass
class UnifiedTrade:
    """Normalized trade record."""

    id: str
    symbol: str
    side: str
    price: float = 0.0
    amount: float = 0.0
    cost: float = 0.0
    fee_cost: float | None = None
    fee_currency: str | None = None
    asset_class: str = "crypto"
    timestamp: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedTicker:
    """Normalized ticker/price data."""

    symbol: str
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    high_24h: float | None = None
    low_24h: float | None = None
    volume_24h: float | None = None
    change_24h: float | None = None
    change_pct_24h: float | None = None
    timestamp: str | None = None


class ExchangeAdapter(ABC):
    """Abstract base class for exchange adapters.

    Every exchange integration (CCXT, IBKR, etc.) implements this interface.
    Tools and services interact exclusively through this contract.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Exchange name (e.g., 'okx', 'bybit', 'ibkr')."""

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Whether this adapter has trading credentials configured."""

    # --- Account / Portfolio (authenticated) ---

    @abstractmethod
    async def fetch_balance(self) -> list[UnifiedBalance]:
        """Fetch account balances. Returns only non-zero balances."""

    @abstractmethod
    async def fetch_positions(
        self, symbol: str | None = None,
    ) -> list[UnifiedPosition]:
        """Fetch open positions."""

    @abstractmethod
    async def fetch_open_orders(
        self, symbol: str | None = None,
    ) -> list[UnifiedOrder]:
        """Fetch open orders."""

    @abstractmethod
    async def fetch_my_trades(
        self,
        symbol: str | None = None,
        since: int | None = None,
        limit: int = 100,
    ) -> list[UnifiedTrade]:
        """Fetch user trade history."""

    # --- Execution (authenticated) ---

    @abstractmethod
    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None = None,
        params: dict[str, Any] | None = None,
    ) -> UnifiedOrder:
        """Place an order. Returns the created order."""

    @abstractmethod
    async def cancel_order(
        self, order_id: str, symbol: str,
    ) -> dict[str, Any]:
        """Cancel an order. Returns status dict."""

    # --- Public Market Data (no auth required) ---

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> UnifiedTicker:
        """Fetch current ticker for a symbol."""

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 100,
    ) -> list[list[float]]:
        """Fetch OHLCV candles. Returns list of [timestamp, O, H, L, C, V]."""

    @abstractmethod
    async def fetch_order_book(
        self, symbol: str, limit: int = 10,
    ) -> dict[str, Any]:
        """Fetch order book. Returns dict with 'bids' and 'asks'."""

    async def fetch_funding_rate(self, symbol: str) -> dict[str, Any]:
        """Fetch funding rate (perpetual contracts). Override if supported."""
        return {"symbol": symbol, "info": "Funding rate not supported by this adapter"}

    # --- Lifecycle ---

    @abstractmethod
    async def close(self) -> None:
        """Close connections and clean up resources."""

    async def test_connection(self) -> dict[str, Any]:
        """Test the connection by fetching balance. Override for custom logic."""
        try:
            balances = await self.fetch_balance()
            return {
                "success": True,
                "message": "Connection successful",
                "data": {
                    "exchange": self.name,
                    "currencies_count": len(balances),
                },
            }
        except Exception as e:
            return {"success": False, "message": f"Connection failed: {e}"}
