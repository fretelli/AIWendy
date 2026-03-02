"""IBKR real-time streaming — event-driven market data via IB Gateway.

Subscribes to IB Gateway streaming market data and pushes price updates
to Redis.  Unlike the polling-based MarketStreamer (apps/streamer/runner.py),
this uses IB Gateway's push-based data feed for lower latency.

Usage:
    streamer = IbkrStreamer(redis_url, gateway_host, gateway_port)
    await streamer.subscribe(["AAPL", "MSFT", "SPY"])
    await streamer.start()
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Lazy import ib_async
_ib_async = None


def _get_ib():
    global _ib_async
    if _ib_async is None:
        import ib_async
        _ib_async = ib_async
    return _ib_async


class IbkrStreamer:
    """Event-driven IBKR market data streamer.

    Connects to IB Gateway and subscribes to real-time market data.
    Price updates are pushed to Redis hash (keeltrader:prices) and
    optionally emitted as events to the Redis Streams event bus.
    """

    def __init__(
        self,
        redis_url: str,
        gateway_host: str = "keeltrader-ib-gateway",
        gateway_port: int = 4001,
        client_id: int = 20,  # Separate client_id for streaming
    ):
        self._redis_url = redis_url
        self._gateway_host = gateway_host
        self._gateway_port = gateway_port
        self._client_id = client_id
        self._redis: aioredis.Redis | None = None
        self._ib = None
        self._symbols: list[str] = []
        self._contracts: dict[str, Any] = {}  # symbol → qualified contract
        self._running = False
        self._stream_key = "keeltrader:events"

    async def start(self) -> None:
        """Connect to IB Gateway and start streaming."""
        ib = _get_ib()

        self._redis = aioredis.from_url(self._redis_url, decode_responses=False)
        self._ib = ib.IB()

        logger.info(
            "Connecting IBKR streamer to %s:%s (client_id=%s)",
            self._gateway_host, self._gateway_port, self._client_id,
        )

        await self._ib.connectAsync(
            host=self._gateway_host,
            port=self._gateway_port,
            clientId=self._client_id,
            readonly=True,
        )

        # Register the event-driven callback
        self._ib.pendingTickersEvent += self._on_pending_tickers

        self._running = True
        logger.info("IBKR streamer connected. Subscribing to %d symbols.", len(self._symbols))

        # Subscribe to all configured symbols
        await self._subscribe_all()

        # Keep running until stopped
        try:
            while self._running:
                await asyncio.sleep(1)
                # ib_async processes events internally
                self._ib.sleep(0)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Disconnect and clean up."""
        self._running = False

        if self._ib and self._ib.isConnected():
            # Cancel all market data subscriptions
            for contract in self._contracts.values():
                self._ib.cancelMktData(contract)
            self._ib.disconnect()
            logger.info("IBKR streamer disconnected.")

        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def subscribe(self, symbols: list[str]) -> None:
        """Set symbols to subscribe to.

        Args:
            symbols: List of symbols (e.g., ["AAPL", "MSFT", "SPY"])
        """
        self._symbols = symbols

    async def _subscribe_all(self) -> None:
        """Subscribe to market data for all configured symbols."""
        ib = _get_ib()

        for symbol in self._symbols:
            try:
                # Create stock contract (most common for IBKR streaming)
                contract = ib.Stock(symbol, "SMART", "USD")
                qualified = await self._ib.qualifyContractsAsync(contract)

                if not qualified:
                    logger.warning("Could not qualify contract for %s", symbol)
                    continue

                contract = qualified[0]
                self._contracts[symbol] = contract

                # Subscribe to streaming data
                self._ib.reqMktData(contract, genericTickList="", snapshot=False)
                logger.info("Subscribed to streaming data: %s", symbol)

            except Exception as e:
                logger.error("Failed to subscribe %s: %s", symbol, e)

    def _on_pending_tickers(self, tickers: set) -> None:
        """Callback fired by ib_async when ticker data updates arrive."""
        for ticker in tickers:
            if ticker.contract is None:
                continue

            symbol = ticker.contract.symbol
            price = ticker.last if ticker.last is not None else ticker.close

            if price is None or price <= 0:
                continue

            # Fire-and-forget async task for Redis update
            asyncio.create_task(self._update_price(symbol, ticker))

    async def _update_price(self, symbol: str, ticker: Any) -> None:
        """Push price update to Redis."""
        if not self._redis:
            return

        try:
            price = ticker.last if ticker.last is not None else ticker.close
            if price is None:
                return

            # Update price hash
            await self._redis.hset("keeltrader:prices", symbol, str(float(price)))

            # Store detailed ticker data
            ticker_data = {
                "symbol": symbol,
                "last": float(price),
                "bid": float(ticker.bid) if ticker.bid is not None else None,
                "ask": float(ticker.ask) if ticker.ask is not None else None,
                "high": float(ticker.high) if ticker.high is not None else None,
                "low": float(ticker.low) if ticker.low is not None else None,
                "volume": int(ticker.volume) if ticker.volume is not None else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "ibkr_stream",
            }

            await self._redis.set(
                f"keeltrader:ticker:{symbol}",
                json.dumps(ticker_data),
                ex=60,  # Expire after 60s if no updates
            )

        except Exception as e:
            logger.debug("Failed to update price for %s: %s", symbol, e)
