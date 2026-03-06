"""
Exchange service for connecting to crypto exchanges via ExchangeAdapter
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import get_settings

logger = logging.getLogger(__name__)


class ExchangeService:
    """Service for interacting with cryptocurrency exchanges"""

    def __init__(self):
        try:
            from apps.exchange.factory import create_adapter
            from apps.exchange.ccxt_adapter import CcxtAdapter

            self._create_adapter = create_adapter
            self._CcxtAdapter = CcxtAdapter
        except ImportError:
            logger.warning("apps.exchange not available, exchange features disabled")
            self._create_adapter = None
            self._CcxtAdapter = None

        settings = get_settings()
        self.adapters: Dict[str, Any] = {}

        # Initialize configured exchanges (skip if exchange module unavailable)
        if self._create_adapter:
            self._init_okx(settings)
            self._init_bybit(settings)

        logger.info(f"Initialized {len(self.adapters)} exchanges: {list(self.adapters.keys())}")

    def _init_okx(self, settings):
        """Initialize OKX exchange"""
        if settings.okx_api_key and settings.okx_api_secret and settings.okx_passphrase:
            try:
                adapter = self._create_adapter(
                    exchange_name="okx",
                    api_key=settings.okx_api_key,
                    api_secret=settings.okx_api_secret,
                    passphrase=settings.okx_passphrase,
                    use_cache=False,
                )
                self.adapters["okx"] = adapter
                logger.info("OKX exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OKX: {e}")

    def _init_bybit(self, settings):
        """Initialize Bybit exchange"""
        if settings.bybit_api_key and settings.bybit_api_secret:
            try:
                adapter = self._create_adapter(
                    exchange_name="bybit",
                    api_key=settings.bybit_api_key,
                    api_secret=settings.bybit_api_secret,
                    use_cache=False,
                )
                self.adapters["bybit"] = adapter
                logger.info("Bybit exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Bybit: {e}")

    def get_available_exchanges(self) -> List[str]:
        """Get list of available/configured exchanges"""
        return list(self.adapters.keys())

    async def get_balance(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """Get account balance from exchange"""
        if exchange_name not in self.adapters:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            adapter = self.adapters[exchange_name]
            # Use sync wrapper since this service historically uses sync CCXT
            if isinstance(adapter, self._CcxtAdapter):
                balance = adapter.fetch_balance_sync()
            else:
                balances = await adapter.fetch_balance()
                balance = {
                    "total": {b.currency: b.total for b in balances},
                    "free": {b.currency: b.free for b in balances},
                    "used": {b.currency: b.used for b in balances},
                }

            formatted_balance = {
                "exchange": exchange_name,
                "timestamp": datetime.now().isoformat(),
                "total": {},
                "free": {},
                "used": {},
            }

            for currency, amounts in balance["total"].items():
                if amounts and amounts > 0:
                    formatted_balance["total"][currency] = amounts
                    formatted_balance["free"][currency] = balance["free"].get(currency, 0)
                    formatted_balance["used"][currency] = balance["used"].get(currency, 0)

            return formatted_balance

        except Exception as e:
            logger.error(f"Error fetching balance from {exchange_name}: {e}")
            return None

    async def get_positions(self, exchange_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get open positions from exchange"""
        if exchange_name not in self.adapters:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            adapter = self.adapters[exchange_name]

            # Check if exchange supports positions via underlying CCXT
            if isinstance(adapter, self._CcxtAdapter) and not adapter.exchange.has["fetchPositions"]:
                logger.warning(f"{exchange_name} does not support positions API")
                return []

            positions = await adapter.fetch_positions()

            formatted_positions = []
            for pos in positions:
                formatted_positions.append({
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "contracts": pos.size,
                    "notional": pos.notional,
                    "leverage": pos.leverage,
                    "entry_price": pos.entry_price,
                    "mark_price": pos.mark_price,
                    "liquidation_price": pos.liquidation_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "percentage": 0,
                    "timestamp": pos.timestamp,
                })

            return formatted_positions

        except Exception as e:
            logger.error(f"Error fetching positions from {exchange_name}: {e}")
            return None

    async def get_open_orders(self, exchange_name: str, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get open orders from exchange"""
        if exchange_name not in self.adapters:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            adapter = self.adapters[exchange_name]
            orders = await adapter.fetch_open_orders(symbol)

            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    "id": order.id,
                    "symbol": order.symbol,
                    "type": order.order_type,
                    "side": order.side,
                    "price": order.price,
                    "amount": order.amount,
                    "filled": order.filled,
                    "remaining": order.remaining,
                    "status": order.status,
                    "timestamp": order.timestamp,
                    "datetime": order.timestamp,
                })

            return formatted_orders

        except Exception as e:
            logger.error(f"Error fetching orders from {exchange_name}: {e}")
            return None

    async def get_trade_history(
        self,
        exchange_name: str,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """Get trade history from exchange"""
        if exchange_name not in self.adapters:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            adapter = self.adapters[exchange_name]

            if not symbol:
                logger.warning(f"Fetching trades without symbol may not be supported on {exchange_name}")
                return []

            trades = await adapter.fetch_my_trades(symbol, since=since, limit=limit)

            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    "id": trade.id,
                    "order_id": None,
                    "symbol": trade.symbol,
                    "type": None,
                    "side": trade.side,
                    "price": trade.price,
                    "amount": trade.amount,
                    "cost": trade.cost,
                    "fee": {"cost": trade.fee_cost, "currency": trade.fee_currency} if trade.fee_cost else None,
                    "timestamp": trade.timestamp,
                    "datetime": trade.timestamp,
                })

            return formatted_trades

        except Exception as e:
            logger.error(f"Error fetching trade history from {exchange_name}: {e}")
            return None

    async def get_markets(self, exchange_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get available trading markets from exchange"""
        if exchange_name not in self.adapters:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            adapter = self.adapters[exchange_name]

            # Access underlying CCXT for market loading (adapter-specific)
            if isinstance(adapter, self._CcxtAdapter):
                markets = adapter.exchange.load_markets()
            else:
                return []

            formatted_markets = []
            for symbol, market in markets.items():
                formatted_markets.append({
                    "symbol": symbol,
                    "base": market.get("base"),
                    "quote": market.get("quote"),
                    "active": market.get("active", False),
                    "type": market.get("type"),
                    "spot": market.get("spot", False),
                    "future": market.get("future", False),
                    "swap": market.get("swap", False),
                })

            return formatted_markets

        except Exception as e:
            logger.error(f"Error fetching markets from {exchange_name}: {e}")
            return None

    def close(self):
        """Close all exchange connections"""
        import asyncio
        for name, adapter in self.adapters.items():
            try:
                asyncio.get_event_loop().run_until_complete(adapter.close())
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")

        self.adapters.clear()
        logger.info("All exchange connections closed")
