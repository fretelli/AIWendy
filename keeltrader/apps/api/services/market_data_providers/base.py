"""Base market data adapter contract."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import httpx

from services.market_data_types import PricePoint, RealTimeQuote


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
    ) -> list[PricePoint]:
        """Fetch historical OHLCV data."""

    @abstractmethod
    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
        """Fetch real-time price data."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the data source is available and configured."""

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
