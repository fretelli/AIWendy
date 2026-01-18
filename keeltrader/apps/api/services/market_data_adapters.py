"""Market data provider adapters for multi-source support."""

import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class MarketDataAdapter(ABC):
    """Abstract base class for market data providers."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical OHLCV data."""
        pass

    @abstractmethod
    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price data."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the data source is available and configured."""
        pass

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class TwelveDataAdapter(MarketDataAdapter):
    """Twelve Data market data provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://api.twelvedata.com"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical data from Twelve Data API."""
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

            response = await self.client.get(f"{self.base_url}/time_series", params=params)
            response.raise_for_status()
            data = response.json()

            if "status" in data and data["status"] == "error":
                raise Exception(data.get("message", "API error"))

            values = data.get("values", [])
            if not values:
                return []

            # Convert to standard format (time ascending)
            result = []
            for item in reversed(values):
                result.append({
                    "time": item.get("datetime"),
                    "open": float(item.get("open", 0)),
                    "high": float(item.get("high", 0)),
                    "low": float(item.get("low", 0)),
                    "close": float(item.get("close", 0)),
                    "volume": int(item.get("volume", 0)),
                })

            logger.info(f"TwelveData: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"TwelveData error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price from Twelve Data."""
        try:
            # Get price
            price_params = {"symbol": symbol, "apikey": self.api_key}
            price_response = await self.client.get(f"{self.base_url}/price", params=price_params)
            price_response.raise_for_status()
            price_data = price_response.json()

            if "status" in price_data and price_data["status"] == "error":
                raise Exception(price_data.get("message", "API error"))

            # Get quote for additional info
            quote_params = {"symbol": symbol, "apikey": self.api_key}
            quote_response = await self.client.get(f"{self.base_url}/quote", params=quote_params)
            quote_data = quote_response.json() if quote_response.status_code == 200 else {}

            price = float(price_data.get("price", 0))
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
            logger.error(f"TwelveData real-time error: {e}")
            raise


class AlphaVantageAdapter(MarketDataAdapter):
    """Alpha Vantage market data provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://www.alphavantage.co/query"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _map_interval(self, interval: str) -> tuple:
        """Map standard interval to Alpha Vantage format."""
        # Return (function, interval_param)
        if interval in ["1min", "5min", "15min", "30min", "60min"]:
            return ("TIME_SERIES_INTRADAY", interval)
        elif interval == "1day":
            return ("TIME_SERIES_DAILY", None)
        elif interval == "1week":
            return ("TIME_SERIES_WEEKLY", None)
        elif interval == "1month":
            return ("TIME_SERIES_MONTHLY", None)
        else:
            return ("TIME_SERIES_DAILY", None)  # Default to daily

    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical data from Alpha Vantage."""
        try:
            function, av_interval = self._map_interval(interval)

            params = {
                "function": function,
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "full" if outputsize > 100 else "compact",
            }

            if av_interval:
                params["interval"] = av_interval

            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            # Check for errors
            if "Error Message" in data:
                raise Exception(data["Error Message"])
            if "Note" in data:
                raise Exception("API rate limit exceeded")

            # Find the time series key
            time_series_key = None
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break

            if not time_series_key:
                return []

            time_series = data[time_series_key]

            # Convert to standard format
            result = []
            for timestamp, values in sorted(time_series.items())[:outputsize]:
                result.append({
                    "time": timestamp,
                    "open": float(values.get("1. open", 0)),
                    "high": float(values.get("2. high", 0)),
                    "low": float(values.get("3. low", 0)),
                    "close": float(values.get("4. close", 0)),
                    "volume": int(values.get("5. volume", 0)),
                })

            logger.info(f"AlphaVantage: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"AlphaVantage error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price from Alpha Vantage."""
        try:
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key,
            }

            response = await self.client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if "Error Message" in data:
                raise Exception(data["Error Message"])

            quote = data.get("Global Quote", {})
            if not quote:
                raise Exception("No quote data returned")

            price = float(quote.get("05. price", 0))
            change = float(quote.get("09. change", 0))
            change_percent = float(quote.get("10. change percent", "0").replace("%", ""))
            volume = int(quote.get("06. volume", 0))

            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": datetime.now().isoformat(),
                "volume": volume,
            }

        except Exception as e:
            logger.error(f"AlphaVantage real-time error: {e}")
            raise


class YahooFinanceAdapter(MarketDataAdapter):
    """Yahoo Finance market data provider (free, no API key required)."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://query1.finance.yahoo.com"

    def is_available(self) -> bool:
        return True  # Always available, no API key required

    def _map_interval(self, interval: str) -> str:
        """Map standard interval to Yahoo Finance format."""
        mapping = {
            "1min": "1m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "1h": "1h",
            "1day": "1d",
            "1week": "1wk",
            "1month": "1mo",
        }
        return mapping.get(interval, "1d")

    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch historical data from Yahoo Finance."""
        try:
            # Calculate date range
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                # Calculate based on interval and outputsize
                if "min" in interval or "h" in interval:
                    start_date = end_date - timedelta(days=7)
                else:
                    start_date = end_date - timedelta(days=outputsize)

            period1 = int(start_date.timestamp())
            period2 = int(end_date.timestamp())
            yf_interval = self._map_interval(interval)

            url = f"{self.base_url}/v8/finance/chart/{symbol}"
            params = {
                "period1": period1,
                "period2": period2,
                "interval": yf_interval,
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Check for errors
            if data.get("chart", {}).get("error"):
                raise Exception(data["chart"]["error"]["description"])

            result_data = data.get("chart", {}).get("result", [])
            if not result_data:
                return []

            quote = result_data[0]
            timestamps = quote.get("timestamp", [])
            indicators = quote.get("indicators", {}).get("quote", [{}])[0]

            # Convert to standard format
            result = []
            for i, ts in enumerate(timestamps[:outputsize]):
                try:
                    result.append({
                        "time": datetime.fromtimestamp(ts).isoformat(),
                        "open": float(indicators["open"][i] or 0),
                        "high": float(indicators["high"][i] or 0),
                        "low": float(indicators["low"][i] or 0),
                        "close": float(indicators["close"][i] or 0),
                        "volume": int(indicators["volume"][i] or 0),
                    })
                except (IndexError, TypeError, ValueError):
                    continue

            logger.info(f"YahooFinance: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"YahooFinance error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price from Yahoo Finance."""
        try:
            url = f"{self.base_url}/v8/finance/chart/{symbol}"
            params = {"range": "1d", "interval": "1m"}

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("chart", {}).get("error"):
                raise Exception(data["chart"]["error"]["description"])

            result_data = data.get("chart", {}).get("result", [])
            if not result_data:
                raise Exception("No data returned")

            meta = result_data[0].get("meta", {})
            price = float(meta.get("regularMarketPrice", 0))
            previous_close = float(meta.get("previousClose", price))
            change = price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0

            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "timestamp": datetime.now().isoformat(),
                "volume": int(meta.get("regularMarketVolume", 0)),
            }

        except Exception as e:
            logger.error(f"YahooFinance real-time error: {e}")
            raise


class MockDataAdapter(MarketDataAdapter):
    """Mock data provider for testing."""

    def is_available(self) -> bool:
        return True

    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Generate mock historical data."""
        data = []
        now = datetime.now()

        # Determine time delta
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

        # Base price
        base_prices = {"SPY": 450.0, "AAPL": 180.0, "TSLA": 250.0}
        current_price = base_prices.get(symbol, 100.0)

        for i in range(outputsize):
            volatility = 0.02
            trend = random.choice([-1, 1]) * random.random() * 0.01

            open_price = current_price
            close_price = open_price * (1 + trend + volatility * (random.random() - 0.5))
            high_price = max(open_price, close_price) * (1 + volatility * random.random() * 0.5)
            low_price = min(open_price, close_price) * (1 - volatility * random.random() * 0.5)
            volume = random.randint(100000, 10000000)

            data.append({
                "time": current_time.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": volume,
            })

            current_price = close_price
            current_time += delta

        logger.info(f"Mock: Generated {len(data)} points for {symbol}")
        return data

    async def get_real_time_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Generate mock real-time price."""
        base_prices = {"SPY": 450.0, "AAPL": 180.0, "TSLA": 250.0}
        base_price = base_prices.get(symbol, 100.0)
        current_price = base_price * (1 + random.random() * 0.02 - 0.01)

        return {
            "symbol": symbol,
            "price": round(current_price, 2),
            "change": round(random.random() * 5 - 2.5, 2),
            "change_percent": round(random.random() * 2 - 1, 2),
            "timestamp": datetime.now().isoformat(),
            "volume": random.randint(100000, 10000000),
        }
