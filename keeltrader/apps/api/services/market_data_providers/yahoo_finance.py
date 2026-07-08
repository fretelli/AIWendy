"""Yahoo Finance market data adapter."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from services.market_data_types import PricePoint, RealTimeQuote

from .base import MarketDataAdapter

logger = logging.getLogger(__name__)


class YahooFinanceAdapter(MarketDataAdapter):
    """Yahoo Finance market data provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://query1.finance.yahoo.com"

    def is_available(self) -> bool:
        return True

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
    ) -> list[PricePoint]:
        """Fetch historical data from Yahoo Finance."""
        try:
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                if "min" in interval or "h" in interval:
                    start_date = end_date - timedelta(days=7)
                else:
                    start_date = end_date - timedelta(days=outputsize)

            url = f"{self.base_url}/v8/finance/chart/{symbol}"
            params = {
                "period1": int(start_date.timestamp()),
                "period2": int(end_date.timestamp()),
                "interval": self._map_interval(interval),
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("chart", {}).get("error"):
                raise Exception(data["chart"]["error"]["description"])

            result_data = data.get("chart", {}).get("result", [])
            if not result_data:
                return []

            quote = result_data[0]
            timestamps = quote.get("timestamp", [])
            indicators = quote.get("indicators", {}).get("quote", [{}])[0]

            result: list[PricePoint] = []
            for i, ts in enumerate(timestamps[:outputsize]):
                try:
                    result.append(
                        {
                            "time": datetime.fromtimestamp(ts).isoformat(),
                            "open": float(indicators["open"][i] or 0),
                            "high": float(indicators["high"][i] or 0),
                            "low": float(indicators["low"][i] or 0),
                            "close": float(indicators["close"][i] or 0),
                            "volume": int(indicators["volume"][i] or 0),
                        }
                    )
                except (IndexError, TypeError, ValueError):
                    continue

            logger.info(f"YahooFinance: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"YahooFinance error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
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
