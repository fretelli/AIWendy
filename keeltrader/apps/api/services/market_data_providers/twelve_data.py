"""Twelve Data market data adapter."""

import logging
from datetime import datetime
from typing import Optional

from services.market_data_types import PricePoint, RealTimeQuote

from .base import MarketDataAdapter

logger = logging.getLogger(__name__)


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
    ) -> list[PricePoint]:
        """Fetch historical data from Twelve Data API."""
        try:
            params: dict[str, object] = {
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
                f"{self.base_url}/time_series", params=params
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "error":
                raise Exception(data.get("message", "API error"))

            values = data.get("values", [])
            if not values:
                return []

            result: list[PricePoint] = []
            for item in reversed(values):
                result.append(
                    {
                        "time": item.get("datetime"),
                        "open": float(item.get("open", 0)),
                        "high": float(item.get("high", 0)),
                        "low": float(item.get("low", 0)),
                        "close": float(item.get("close", 0)),
                        "volume": int(item.get("volume", 0)),
                    }
                )

            logger.info(f"TwelveData: Fetched {len(result)} points for {symbol}")
            return result

        except Exception as e:
            logger.error(f"TwelveData error: {e}")
            raise

    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
        """Fetch real-time price from Twelve Data."""
        try:
            price_params = {"symbol": symbol, "apikey": self.api_key}
            price_response = await self.client.get(
                f"{self.base_url}/price", params=price_params
            )
            price_response.raise_for_status()
            price_data = price_response.json()

            if price_data.get("status") == "error":
                raise Exception(price_data.get("message", "API error"))

            quote_params = {"symbol": symbol, "apikey": self.api_key}
            quote_response = await self.client.get(
                f"{self.base_url}/quote", params=quote_params
            )
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
