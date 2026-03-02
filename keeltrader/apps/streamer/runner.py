"""Market data streamer — CCXT polling-based price monitoring with event emission.

Uses CCXT REST API polling (not WebSocket) for reliability. Monitors configured
symbols and emits price events to Redis Streams when alert conditions trigger.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

import ccxt.async_support as ccxt
import redis.asyncio as aioredis

from .price_monitor import PriceAlert, PriceMonitor

logger = logging.getLogger(__name__)

# Default symbols to monitor
DEFAULT_WATCHLIST = [
    "BTC/USDT",
    "ETH/USDT",
]

# Polling interval in seconds
POLL_INTERVAL = int(os.environ.get("STREAMER_POLL_INTERVAL", "30"))


class MarketStreamer:
    """Market data streamer with price monitoring and event emission.

    Polls exchange prices at regular intervals, checks alert rules,
    and emits price.alert events to the Redis Streams event bus.
    """

    def __init__(self, redis_url: str, db_url: str):
        self._redis_url = redis_url
        self._db_url = db_url
        self._redis: aioredis.Redis | None = None
        self._exchange: ccxt.Exchange | None = None
        self._monitor = PriceMonitor()
        self._running = False
        self._watchlist: list[str] = list(DEFAULT_WATCHLIST)
        self._stream_key = "keeltrader:events"

    async def start(self) -> None:
        """Start the market streamer."""
        logger.info("Starting market streamer...")

        # Initialize Redis
        self._redis = aioredis.from_url(self._redis_url, decode_responses=False)

        # Initialize exchange (public data only)
        exchange_config: dict[str, Any] = {"enableRateLimit": True}
        # Use proxy if configured (for GFW bypass)
        http_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        if http_proxy:
            exchange_config["aiohttp_proxy"] = http_proxy
            logger.info("Using proxy: %s", http_proxy)
        self._exchange = ccxt.okx(exchange_config)

        # Load watchlist from Redis (user-configured symbols)
        await self._load_watchlist()

        # Setup default alerts for watchlist
        await self._init_alerts()

        self._running = True
        logger.info(
            "Market streamer started. Watching %d symbols, poll interval %ds",
            len(self._watchlist), POLL_INTERVAL,
        )

        try:
            await self._poll_loop()
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the market streamer."""
        self._running = False
        if self._exchange:
            await self._exchange.close()
            self._exchange = None
        if self._redis:
            await self._redis.aclose()
            self._redis = None
        logger.info("Market streamer stopped.")

    async def _load_watchlist(self) -> None:
        """Load watchlist from Redis (or use defaults)."""
        if self._redis:
            stored = await self._redis.smembers("keeltrader:watchlist")
            if stored:
                self._watchlist = [s.decode() if isinstance(s, bytes) else s for s in stored]
                logger.info("Loaded watchlist from Redis: %s", self._watchlist)
            else:
                # Store defaults
                for symbol in self._watchlist:
                    await self._redis.sadd("keeltrader:watchlist", symbol)

    async def _init_alerts(self) -> None:
        """Initialize price alerts — fetch current prices and set default alerts."""
        if not self._exchange:
            return

        for symbol in self._watchlist:
            try:
                ticker = await self._exchange.fetch_ticker(symbol)
                price = ticker.get("last", 0)
                if price:
                    self._monitor.update_price(symbol, price)
                    self._monitor.add_default_alerts(symbol)
                    logger.info("Initialized %s at %.2f", symbol, price)
            except Exception as e:
                logger.error("Failed to init %s: %s", symbol, e)

    async def _heartbeat(self) -> None:
        """Publish heartbeat to Redis every 30 seconds."""
        import json
        from datetime import datetime

        while self._running:
            try:
                if self._redis:
                    status = {
                        "symbols": self._watchlist,
                        "poll_interval": POLL_INTERVAL,
                        "running": self._running,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    await self._redis.set(
                        "keeltrader:streamer:heartbeat",
                        json.dumps(status),
                        ex=60,
                    )
            except Exception as e:
                logger.debug("Heartbeat failed: %s", e)
            await asyncio.sleep(30)

    async def _poll_loop(self) -> None:
        """Main polling loop — fetch prices and check alerts."""
        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._heartbeat())

        try:
            while self._running:
                try:
                    await self._poll_prices()
                except Exception as e:
                    logger.error("Poll cycle error: %s", e)

                await asyncio.sleep(POLL_INTERVAL)
        finally:
            heartbeat_task.cancel()

    async def _poll_prices(self) -> None:
        """Fetch current prices for all watched symbols."""
        if not self._exchange:
            return

        for symbol in self._watchlist:
            try:
                ticker = await self._exchange.fetch_ticker(symbol)
                price = ticker.get("last", 0)
                if not price:
                    continue

                # Update monitor and check alerts
                triggered = self._monitor.update_price(symbol, price)

                # Store latest price in Redis for other services
                if self._redis:
                    await self._redis.hset(
                        "keeltrader:prices",
                        symbol,
                        str(price),
                    )

                # Emit events for triggered alerts
                for alert_data in triggered:
                    await self._emit_price_alert(alert_data)

            except Exception as e:
                logger.error("Failed to poll %s: %s", symbol, e)

    async def _emit_price_alert(self, alert_data: dict[str, Any]) -> None:
        """Emit a price.alert event to the event bus."""
        if not self._redis:
            return

        import json
        from uuid import uuid4
        from datetime import datetime

        event_id = str(uuid4())
        correlation_id = str(uuid4())

        stream_data = {
            "id": event_id,
            "type": "price.alert",
            "source": "market-streamer",
            "user_id": alert_data.get("user_id", ""),
            "agent_id": "",
            "payload": json.dumps(alert_data),
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "causation_id": "",
        }

        await self._redis.xadd(self._stream_key, stream_data, maxlen=10000)
        logger.info(
            "Emitted price.alert: %s %s @ %.2f",
            alert_data["symbol"], alert_data["alert_type"], alert_data["price"],
        )


async def main():
    """Entry point for the market streamer process."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    db_url = os.environ.get("DATABASE_URL", "")

    streamer = MarketStreamer(redis_url=redis_url, db_url=db_url)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(streamer.stop()))

    await streamer.start()


if __name__ == "__main__":
    asyncio.run(main())
