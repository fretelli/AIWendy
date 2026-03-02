"""Market data streamer — CCXT WebSocket based price monitoring."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

logger = logging.getLogger(__name__)


class MarketStreamer:
    """CCXT WebSocket market data streamer.

    Monitors configured symbols and emits price events
    to the event bus when alert conditions are met.
    """

    def __init__(self, redis_url: str, db_url: str):
        self._redis_url = redis_url
        self._db_url = db_url
        self._running = False

    async def start(self) -> None:
        """Start the market streamer."""
        logger.info("Starting market streamer...")
        self._running = True

        # TODO: Initialize CCXT WebSocket connections
        # TODO: Load watchlist from database
        # TODO: Connect to event bus

        try:
            while self._running:
                await asyncio.sleep(5)
                # TODO: Process market data, check alerts, emit events
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the market streamer."""
        self._running = False
        logger.info("Market streamer stopped.")


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
