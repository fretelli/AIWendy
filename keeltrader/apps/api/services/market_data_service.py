"""
Market data service for fetching price data for charts with multi-source support.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import get_settings
from services.market_data_adapters import (
    AlphaVantageAdapter,
    MarketDataAdapter,
    MockDataAdapter,
    TwelveDataAdapter,
    YahooFinanceAdapter,
)

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and managing market data with fallback support."""

    def __init__(self):
        settings = get_settings()

        # Initialize all available adapters
        self.adapters: List[MarketDataAdapter] = []

        # Priority order: Twelve Data > Alpha Vantage > Yahoo Finance > Mock
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

        # Mock data as final fallback
        self.adapters.append(MockDataAdapter())
        logger.info("Mock data adapter initialized as fallback")

        logger.info(f"Market data service initialized with {len(self.adapters)} data sources")

    async def get_historical_data(
        self,
        symbol: str,
        interval: str = "1day",
        outputsize: int = 60,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
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

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
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

    async def get_technical_indicators(
        self,
        symbol: str,
        interval: str = "1day",
        indicator: str = "sma",
        period: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Calculate technical indicators for a symbol

        Args:
            symbol: Stock symbol
            interval: Time interval
            indicator: Indicator type (sma, ema, rsi, macd, bbands)
            period: Period for the indicator

        Returns:
            List of indicator values
        """
        try:
            # Get historical data
            data = await self.get_historical_data(symbol, interval, period * 2)

            if not data:
                return []

            # Calculate the indicator
            if indicator == "sma":
                return self._calculate_sma(data, period)
            elif indicator == "ema":
                return self._calculate_ema(data, period)
            elif indicator == "rsi":
                return self._calculate_rsi(data, period)
            else:
                return []
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return []

    def _calculate_sma(self, data: List[Dict], period: int) -> List[Dict]:
        """Calculate Simple Moving Average"""
        sma_data = []

        for i in range(period - 1, len(data)):
            sum_price = sum(d["close"] for d in data[i - period + 1 : i + 1])
            sma_value = sum_price / period

            sma_data.append(
                {
                    "time": data[i]["time"],
                    "value": round(sma_value, 2),
                }
            )

        return sma_data

    def _calculate_ema(self, data: List[Dict], period: int) -> List[Dict]:
        """Calculate Exponential Moving Average"""
        ema_data = []
        multiplier = 2 / (period + 1)

        # Start with SMA for the first value
        if len(data) >= period:
            sma = sum(d["close"] for d in data[:period]) / period
            ema_data.append(
                {
                    "time": data[period - 1]["time"],
                    "value": round(sma, 2),
                }
            )

            # Calculate EMA for remaining values
            for i in range(period, len(data)):
                ema_value = (
                    data[i]["close"] - ema_data[-1]["value"]
                ) * multiplier + ema_data[-1]["value"]
                ema_data.append(
                    {
                        "time": data[i]["time"],
                        "value": round(ema_value, 2),
                    }
                )

        return ema_data

    def _calculate_rsi(self, data: List[Dict], period: int = 14) -> List[Dict]:
        """Calculate Relative Strength Index"""
        rsi_data = []

        if len(data) < period + 1:
            return rsi_data

        # Calculate price changes
        changes = []
        for i in range(1, len(data)):
            changes.append(data[i]["close"] - data[i - 1]["close"])

        # Calculate initial average gain and loss
        gains = [c if c > 0 else 0 for c in changes[:period]]
        losses = [-c if c < 0 else 0 for c in changes[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Calculate RSI
        for i in range(period, len(changes)):
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_data.append(
                {
                    "time": data[i + 1]["time"],
                    "value": round(rsi, 2),
                }
            )

            # Update averages
            current_gain = changes[i] if changes[i] > 0 else 0
            current_loss = -changes[i] if changes[i] < 0 else 0

            avg_gain = (avg_gain * (period - 1) + current_gain) / period
            avg_loss = (avg_loss * (period - 1) + current_loss) / period

        return rsi_data

    async def close(self):
        """Close all HTTP clients in adapters."""
        for adapter in self.adapters:
            try:
                await adapter.close()
            except Exception as e:
                logger.error(f"Error closing adapter {adapter.__class__.__name__}: {e}")
