"""
Exchange service for connecting to crypto exchanges via CCXT
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import ccxt

from ..config import get_settings

logger = logging.getLogger(__name__)


class ExchangeService:
    """Service for interacting with cryptocurrency exchanges"""

    def __init__(self):
        settings = get_settings()
        self.exchanges: Dict[str, ccxt.Exchange] = {}

        # Initialize configured exchanges
        self._init_binance(settings)
        self._init_okx(settings)
        self._init_bybit(settings)

        logger.info(f"Initialized {len(self.exchanges)} exchanges: {list(self.exchanges.keys())}")

    def _init_binance(self, settings):
        """Initialize Binance exchange"""
        if settings.binance_api_key and settings.binance_api_secret:
            try:
                self.exchanges["binance"] = ccxt.binance({
                    "apiKey": settings.binance_api_key,
                    "secret": settings.binance_api_secret,
                    "enableRateLimit": True,
                    "options": {
                        "defaultType": "spot",  # spot, future, swap
                    }
                })
                logger.info("Binance exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Binance: {e}")

    def _init_okx(self, settings):
        """Initialize OKX exchange"""
        if settings.okx_api_key and settings.okx_api_secret and settings.okx_passphrase:
            try:
                self.exchanges["okx"] = ccxt.okx({
                    "apiKey": settings.okx_api_key,
                    "secret": settings.okx_api_secret,
                    "password": settings.okx_passphrase,
                    "enableRateLimit": True,
                })
                logger.info("OKX exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OKX: {e}")

    def _init_bybit(self, settings):
        """Initialize Bybit exchange"""
        if settings.bybit_api_key and settings.bybit_api_secret:
            try:
                self.exchanges["bybit"] = ccxt.bybit({
                    "apiKey": settings.bybit_api_key,
                    "secret": settings.bybit_api_secret,
                    "enableRateLimit": True,
                })
                logger.info("Bybit exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Bybit: {e}")

    def get_available_exchanges(self) -> List[str]:
        """Get list of available/configured exchanges"""
        return list(self.exchanges.keys())

    async def get_balance(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """
        Get account balance from exchange

        Args:
            exchange_name: Name of the exchange (binance, okx, bybit)

        Returns:
            Balance information with total, free, and used amounts
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            exchange = self.exchanges[exchange_name]
            balance = exchange.fetch_balance()

            # Format the balance data
            formatted_balance = {
                "exchange": exchange_name,
                "timestamp": datetime.now().isoformat(),
                "total": {},
                "free": {},
                "used": {},
            }

            # Extract non-zero balances
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
        """
        Get open positions from exchange

        Args:
            exchange_name: Name of the exchange

        Returns:
            List of open positions
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            exchange = self.exchanges[exchange_name]

            # Check if exchange supports positions
            if not exchange.has["fetchPositions"]:
                logger.warning(f"{exchange_name} does not support positions API")
                return []

            positions = exchange.fetch_positions()

            # Filter and format positions
            formatted_positions = []
            for pos in positions:
                # Only include positions with non-zero size
                if pos.get("contracts", 0) > 0 or pos.get("notional", 0) != 0:
                    formatted_positions.append({
                        "symbol": pos.get("symbol"),
                        "side": pos.get("side"),  # long or short
                        "contracts": pos.get("contracts", 0),
                        "notional": pos.get("notional", 0),
                        "leverage": pos.get("leverage", 1),
                        "entry_price": pos.get("entryPrice"),
                        "mark_price": pos.get("markPrice"),
                        "liquidation_price": pos.get("liquidationPrice"),
                        "unrealized_pnl": pos.get("unrealizedPnl", 0),
                        "percentage": pos.get("percentage", 0),
                        "timestamp": pos.get("timestamp"),
                    })

            return formatted_positions

        except Exception as e:
            logger.error(f"Error fetching positions from {exchange_name}: {e}")
            return None

    async def get_open_orders(self, exchange_name: str, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get open orders from exchange

        Args:
            exchange_name: Name of the exchange
            symbol: Optional symbol to filter orders

        Returns:
            List of open orders
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            exchange = self.exchanges[exchange_name]
            orders = exchange.fetch_open_orders(symbol=symbol)

            # Format orders
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    "id": order.get("id"),
                    "symbol": order.get("symbol"),
                    "type": order.get("type"),  # limit, market, etc.
                    "side": order.get("side"),  # buy or sell
                    "price": order.get("price"),
                    "amount": order.get("amount"),
                    "filled": order.get("filled", 0),
                    "remaining": order.get("remaining"),
                    "status": order.get("status"),
                    "timestamp": order.get("timestamp"),
                    "datetime": order.get("datetime"),
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
        """
        Get trade history from exchange

        Args:
            exchange_name: Name of the exchange
            symbol: Optional symbol to filter trades
            since: Timestamp in milliseconds to fetch trades from
            limit: Maximum number of trades to return

        Returns:
            List of trades
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            exchange = self.exchanges[exchange_name]

            # Fetch trades
            if symbol:
                trades = exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
            else:
                # Some exchanges don't support fetching all trades at once
                # In that case, we'd need to fetch for each symbol separately
                logger.warning(f"Fetching trades without symbol may not be supported on {exchange_name}")
                trades = []

            # Format trades
            formatted_trades = []
            for trade in trades:
                formatted_trades.append({
                    "id": trade.get("id"),
                    "order_id": trade.get("order"),
                    "symbol": trade.get("symbol"),
                    "type": trade.get("type"),
                    "side": trade.get("side"),
                    "price": trade.get("price"),
                    "amount": trade.get("amount"),
                    "cost": trade.get("cost"),
                    "fee": trade.get("fee"),
                    "timestamp": trade.get("timestamp"),
                    "datetime": trade.get("datetime"),
                })

            return formatted_trades

        except Exception as e:
            logger.error(f"Error fetching trade history from {exchange_name}: {e}")
            return None

    async def get_markets(self, exchange_name: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get available trading markets from exchange

        Args:
            exchange_name: Name of the exchange

        Returns:
            List of available markets
        """
        if exchange_name not in self.exchanges:
            logger.error(f"Exchange {exchange_name} not configured")
            return None

        try:
            exchange = self.exchanges[exchange_name]
            markets = exchange.load_markets()

            # Format markets
            formatted_markets = []
            for symbol, market in markets.items():
                formatted_markets.append({
                    "symbol": symbol,
                    "base": market.get("base"),
                    "quote": market.get("quote"),
                    "active": market.get("active", False),
                    "type": market.get("type"),  # spot, future, swap
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
        for name, exchange in self.exchanges.items():
            try:
                if hasattr(exchange, "close"):
                    exchange.close()
            except Exception as e:
                logger.error(f"Error closing {name}: {e}")

        self.exchanges.clear()
        logger.info("All exchange connections closed")
