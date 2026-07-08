"""Mock market data adapter for explicit non-production use."""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

from services.market_data_types import PricePoint, RealTimeQuote

from .base import MarketDataAdapter

logger = logging.getLogger(__name__)


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
    ) -> list[PricePoint]:
        """Generate mock historical data."""
        del start_date, end_date
        data: list[PricePoint] = []
        now = datetime.now()

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

        base_prices = {"SPY": 450.0, "AAPL": 180.0, "TSLA": 250.0}
        current_price = base_prices.get(symbol, 100.0)

        for _ in range(outputsize):
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

            data.append(
                {
                    "time": current_time.isoformat(),
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": random.randint(100000, 10000000),
                }
            )

            current_price = close_price
            current_time += delta

        logger.info(f"Mock: Generated {len(data)} points for {symbol}")
        return data

    async def get_real_time_price(self, symbol: str) -> Optional[RealTimeQuote]:
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
