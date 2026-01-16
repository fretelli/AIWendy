"""
Market data service for fetching price data for charts
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings

logger = logging.getLogger(__name__)


class MarketDataService:
    """Service for fetching and managing market data"""

    def __init__(self):
        settings = get_settings()
        self.base_url = "https://api.twelvedata.com"
        self.api_key = settings.twelve_data_api_key
        self.client = httpx.AsyncClient(timeout=30.0)

        if self.api_key:
            logger.info("Twelve Data API key configured - using real market data")
        else:
            logger.info("No Twelve Data API key - using mock data")

    async def get_historical_data(
        self,
        symbol: str,
        interval: str = "1day",
        outputsize: int = 60,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical price data for a symbol

        Args:
            symbol: Stock symbol (e.g., "AAPL", "SPY")
            interval: Time interval (1min, 5min, 15min, 30min, 1h, 1day, 1week, 1month)
            outputsize: Number of data points
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            List of OHLCV data points
        """
        try:
            # Use real API if key is configured, otherwise use mock data
            if self.api_key:
                return await self._fetch_real_data(symbol, interval, outputsize, start_date, end_date)
            else:
                return await self._generate_mock_data(symbol, interval, outputsize)
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            # Fallback to mock data on error
            logger.info("Falling back to mock data")
            return await self._generate_mock_data(symbol, interval, outputsize)

    async def _fetch_real_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch real market data from Twelve Data API"""
        try:
            params = {
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key,
            }

            if start_date:
                params["start_date"] = start_date.strftime("%Y-%m-%d")
            if end_date:
                params["end_date"] = end_date.strftime("%Y-%m-%d")

            response = await self.client.get(
                f"{self.base_url}/time_series",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "status" in data and data["status"] == "error":
                logger.error(f"Twelve Data API error: {data.get('message', 'Unknown error')}")
                raise Exception(data.get("message", "API error"))

            # Parse the response
            values = data.get("values", [])
            if not values:
                logger.warning(f"No data returned for symbol {symbol}")
                return []

            # Convert to our format (time ascending order)
            result = []
            for item in reversed(values):  # Twelve Data returns newest first
                result.append({
                    "time": item.get("datetime"),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("close", 0)),
                    "volume": int(item.get("volume", 0)),
                })

            logger.info(f"Fetched {len(result)} data points for {symbol}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching real data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching real data: {e}")
            raise

    async def _generate_mock_data(
        self, symbol: str, interval: str, outputsize: int
    ) -> List[Dict[str, Any]]:
        """Generate mock OHLCV data for testing"""
        import random
        from datetime import datetime, timedelta

        data = []
        now = datetime.now()

        # Determine time delta based on interval
        delta_map = {
            "1min": timedelta(minutes=1),
            "5min": timedelta(minutes=5),
            "15min": timedelta(minutes=15),
            "30min": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "1day": timedelta(days=1),
            "1week": timedelta(weeks=1),
            "1month": timedelta(days=30),
        }

        delta = delta_map.get(interval, timedelta(days=1))
        current_time = now - (delta * outputsize)

        # Generate base price based on symbol
        base_price = 100.0
        if symbol == "SPY":
            base_price = 450.0
        elif symbol == "AAPL":
            base_price = 180.0
        elif symbol == "TSLA":
            base_price = 250.0

        current_price = base_price

        for i in range(outputsize):
            # Generate realistic OHLC data
            volatility = 0.02
            trend = random.choice([-1, 1]) * random.random() * 0.01

            open_price = current_price
            close_price = open_price * (
                1 + trend + volatility * (random.random() - 0.5)
            )
            high_price = max(open_price, close_price) * (
                1 + volatility * random.random() * 0.5
            )
            low_price = min(open_price, close_price) * (
                1 - volatility * random.random() * 0.5
            )
            volume = random.randint(100000, 10000000)

            data.append(
                {
                    "time": current_time.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": volume,
                }
            )

            current_price = close_price
            current_time += delta

        return data

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time price for a symbol

        Args:
            symbol: Stock symbol

        Returns:
            Current price data
        """
        try:
            if self.api_key:
                return await self._fetch_real_time_price(symbol)
            else:
                return await self._generate_mock_price(symbol)
        except Exception as e:
            logger.error(f"Error fetching real-time price: {e}")
            # Fallback to mock data
            return await self._generate_mock_price(symbol)

    async def _fetch_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price from Twelve Data API"""
        try:
            params = {
                "symbol": symbol,
                "apikey": self.api_key,
            }

            response = await self.client.get(
                f"{self.base_url}/price",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            # Check for API errors
            if "status" in data and data["status"] == "error":
                logger.error(f"Twelve Data API error: {data.get('message', 'Unknown error')}")
                raise Exception(data.get("message", "API error"))

            # Get quote data for additional info
            quote_params = {
                "symbol": symbol,
                "apikey": self.api_key,
            }
            quote_response = await self.client.get(
                f"{self.base_url}/quote",
                params=quote_params,
            )
            quote_data = quote_response.json() if quote_response.status_code == 200 else {}

            price = float(data.get("price", 0))
            change = float(quote_data.get("change", 0))
            change_percent = float(quote_data.get("percent_change", 0))
            volume = int(quote_data.get("volume", 0))

            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": datetime.now().isoformat(),
                "volume": volume,
            }

        except Exception as e:
            logger.error(f"Error fetching real-time price: {e}")
            raise

    async def _generate_mock_price(self, symbol: str) -> Dict[str, Any]:
        """Generate mock real-time price data"""
        import random

        base_price = 100.0
        if symbol == "SPY":
            base_price = 450.0
        elif symbol == "AAPL":
            base_price = 180.0
        elif symbol == "TSLA":
            base_price = 250.0

        current_price = base_price * (1 + random.random() * 0.02 - 0.01)

        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(random.random() * 5 - 2.5, 2),
            "change_percent": round(random.random() * 2 - 1, 2),
            "timestamp": datetime.now().isoformat(),
            "volume": random.randint(100000, 10000000),
        }

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
        """Close the HTTP client"""
        await self.client.aclose()
