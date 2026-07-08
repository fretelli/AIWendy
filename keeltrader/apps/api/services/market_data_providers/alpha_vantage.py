"""Alpha Vantage market data adapter."""

import logging
from datetime import datetime
from typing import Optional

from services.market_data_types import PricePoint, RealTimeQuote

from .base import MarketDataAdapter

logger = logging.getLogger(__name__)


class AlphaVantageAdapter(MarketDataAdapter):
    """Alpha Vantage market data provider."""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.base_url = "https://www.alphavantage.co/query"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _map_interval(self, interval: str) -> tuple[str, Optional[str]]:
        """Map standard interval to Alpha Vantage format."""
        if interval in ["1min", "5min", "15min", "30min", "60min"]:
            return ("TIME_SERIES_INTRADAY", interval)
        if interval == "1day":
            return ("TIME_SERIES_DAILY", None)
        if interval == "1week":
            return ("TIME_SERIES_WEEKLY", None)
        if interval == "1month":
            return ("TIME_SERIES_MONTHLY", None)
        return ("TIME_SERIES_DAILY", None)

    async def get_historical_data(
        self,
        symbol: str,
        interval: str,
        outputsize: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[PricePoint]:
        """Fetch historical data from Alpha Vantage."""
        del start_date, end_date
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

            if "Error Message" in data:
                raise Exception(data["Error Message"])
            if "Note" in data:
                raise Exception("API rate limit exceeded")

            time_series_key = next(
                (key for key in data.keys() if "Time Series" in key), None
            )
            if not time_series_key:
                return []

            result: list[PricePoint] = []
            for timestamp, values in sorted(data[time_series_key].items())[:outputsize]:
                result.append(
                    {
                        "time": timestamp,
                        "open": float(values.get("1. open", 0)),
                        "high": float(values.get("2. high", 0)),
                        "low": float(values.get("3. low", 0)),
                        "close": float(values.get("4. close", 0)),
                        "volume": int(values.get("5. volume", 0)),
                    }
                )

            logger.info(f"AlphaVantage: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"AlphaVantage error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
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
