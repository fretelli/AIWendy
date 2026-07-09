"""
Market data service for fetching price data for charts with multi-source support.
"""

import logging
from datetime import datetime
from typing import Optional

from config import get_settings
from services.market_data_adapters import (
    AlphaVantageAdapter,
    MarketDataAdapter,
    MockDataAdapter,
    TwelveDataAdapter,
    YahooFinanceAdapter,
)
from services.market_data_types import PricePoint, RealTimeQuote

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and managing market data with fallback support."""

    def __init__(self):
        settings = get_settings()

        # Initialize all available adapters
        self.adapters: list[MarketDataAdapter] = []

        # Priority order: Twelve Data > Alpha Vantage > Yahoo Finance.
        # Mock data is never a production fallback; it must be explicitly enabled.
        twelve_data_key = getattr(settings, "twelve_data_api_key", None)
        if twelve_data_key:
            self.adapters.append(TwelveDataAdapter(twelve_data_key))
            logger.info("Twelve Data adapter initialized")

        alpha_vantage_key = getattr(settings, "alpha_vantage_api_key", None)
        if alpha_vantage_key:
            self.adapters.append(AlphaVantageAdapter(alpha_vantage_key))
            logger.info("Alpha Vantage adapter initialized")

        # Yahoo Finance is always available (no API key required)
        self.adapters.append(YahooFinanceAdapter())
        logger.info("Yahoo Finance adapter initialized")

        allow_mock = (
            getattr(settings, "enable_mock_market_data", False)
            and settings.environment.lower() in {"development", "dev", "test", "testing"}
        )
        if allow_mock:
            self.adapters.append(MockDataAdapter())
            logger.info("Mock data adapter initialized by explicit non-production setting")

        logger.info(f"Market data service initialized with {len(self.adapters)} data sources")

    async def get_historical_data(
        self,
        symbol: str,
        interval: str = "1day",
        outputsize: int = 60,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[PricePoint]:
        """
        Fetch historical price data for a symbol with automatic fallback.

        Args:
            symbol: Stock symbol (e.g., "AAPL", "SPY")
            interval: Time interval (1min, 5min, 15min, 30min, 1h, 1day, 1week, 1month)
            outputsize: Number of data points
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of OHLCV data points
        """
        # Try each adapter in priority order
        for adapter in self.adapters:
            if not adapter.is_available():
                continue

            try:
                logger.info(f"Attempting to fetch data from {adapter.__class__.__name__}")
                data = await adapter.get_historical_data(
                    symbol=symbol,
                    interval=interval,
                    outputsize=outputsize,
                    start_date=start_date,
                    end_date=end_date,
                )

                if data:
                    logger.info(
                        f"Successfully fetched {len(data)} points from {adapter.__class__.__name__}"
                    )
                    return data

            except Exception as e:
                logger.warning(f"{adapter.__class__.__name__} failed: {e}, trying next source")
                continue

        # If all adapters fail, return empty list
        logger.error(f"All data sources failed for symbol {symbol}")
        return []

    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
        """
        Get real-time price for a symbol with automatic fallback.

        Args:
            symbol: Stock symbol

        Returns:
            Current price data
        """
        # Try each adapter in priority order
        for adapter in self.adapters:
            if not adapter.is_available():
                continue

            try:
                logger.info(
                    f"Attempting to fetch real-time price from {adapter.__class__.__name__}"
                )
                data = await adapter.get_real_time_price(symbol)

                if data:
                    logger.info(
                        f"Successfully fetched real-time price from {adapter.__class__.__name__}"
                    )
                    return data

            except Exception as e:
                logger.warning(
                    f"{adapter.__class__.__name__} real-time failed: {e}, trying next source"
                )
                continue

        # If all adapters fail, return None
        logger.error(f"All data sources failed for real-time price of {symbol}")
        return None

    async def close(self):
        """Close all HTTP clients in adapters."""
        for adapter in self.adapters:
            try:
                await adapter.close()
            except Exception as e:
                logger.error(f"Error closing adapter {adapter.__class__.__name__}: {e}")
