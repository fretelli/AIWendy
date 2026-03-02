"""Event engine main loop — reads from Redis Streams and dispatches to agents."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

import redis.asyncio as aioredis

from ..agents.base import AgentDependencies
from .dispatcher import EventDispatcher
from .event_bus import EventBus
from .safety import EventSafety

logger = logging.getLogger(__name__)


class EventEngine:
    """Main event engine that reads events and dispatches to agents."""

    def __init__(
        self,
        redis_url: str,
        db_url: str,
        litellm_base: str = "",
        litellm_key: str = "",
    ):
        self._redis_url = redis_url
        self._db_url = db_url
        self._litellm_base = litellm_base
        self._litellm_key = litellm_key
        self._bus = EventBus(redis_url)
        self._safety: EventSafety | None = None
        self._dispatcher: EventDispatcher | None = None
        self._running = False
        self._consumer_name = f"engine-{os.getpid()}"

    @property
    def bus(self) -> EventBus:
        return self._bus

    @property
    def dispatcher(self) -> EventDispatcher | None:
        return self._dispatcher

    async def start(self) -> None:
        """Initialize connections and start the event loop."""
        logger.info("Starting event engine (consumer: %s)...", self._consumer_name)

        await self._bus.connect()
        self._safety = EventSafety(self._bus.redis)
        self._dispatcher = EventDispatcher(self._safety)

        # Register agents
        await self._register_agents()

        self._running = True
        logger.info("Event engine started. Listening for events...")

        try:
            await self._event_loop()
        except asyncio.CancelledError:
            logger.info("Event engine cancelled.")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the event engine."""
        self._running = False
        await self._bus.disconnect()
        logger.info("Event engine stopped.")

    async def _register_agents(self) -> None:
        """Register all active agents with the dispatcher."""
        from ..agents.orchestrator import create_orchestrator
        from ..agents.technical import create_technical_analyst
        from ..agents.executor import create_executor
        from ..agents.psychology import create_psychology_coach
        from ..agents.guardian import create_guardian

        # Use the LiteLLM model prefix for routing
        orchestrator_model = os.environ.get(
            "ORCHESTRATOR_MODEL", "anthropic/claude-sonnet-4-20250514"
        )
        analyst_model = os.environ.get(
            "ANALYST_MODEL", "anthropic/claude-haiku-4-5-20251001"
        )
        executor_model = os.environ.get(
            "EXECUTOR_MODEL", "anthropic/claude-haiku-4-5-20251001"
        )
        coach_model = os.environ.get(
            "COACH_MODEL", "anthropic/claude-sonnet-4-20250514"
        )
        guardian_model = os.environ.get(
            "GUARDIAN_MODEL", "anthropic/claude-sonnet-4-20250514"
        )

        orchestrator = create_orchestrator(model=orchestrator_model)
        self._dispatcher.register_agent(orchestrator)

        technical = create_technical_analyst(model=analyst_model)
        self._dispatcher.register_agent(technical)

        executor = create_executor(model=executor_model)
        self._dispatcher.register_agent(executor)

        psychology = create_psychology_coach(model=coach_model)
        self._dispatcher.register_agent(psychology)

        guardian = create_guardian(model=guardian_model)
        self._dispatcher.register_agent(guardian)

        logger.info(
            "Agent registration complete. Registered: %d agents — %s",
            len(self._dispatcher.registered_agents),
            list(self._dispatcher.registered_agents.keys()),
        )

    async def _event_loop(self) -> None:
        """Main event processing loop."""
        deps = AgentDependencies(
            db_url=self._db_url,
            redis_url=self._redis_url,
            litellm_base=self._litellm_base,
            litellm_key=self._litellm_key,
        )

        while self._running:
            try:
                events = await self._bus.read_new(
                    consumer_name=self._consumer_name,
                    count=10,
                    block_ms=5000,
                )

                for msg_id, event in events:
                    try:
                        # Set user context
                        deps.user_id = str(event.user_id) if event.user_id else None

                        results = await self._dispatcher.dispatch(event, deps)

                        # Acknowledge after processing
                        await self._bus.ack(msg_id)

                        for r in results:
                            if not r.success:
                                logger.warning(
                                    "Agent %s failed: %s", r.agent_id, r.message
                                )
                    except Exception as e:
                        logger.error("Failed to process event %s: %s", msg_id, e)
                        # Still ack to prevent infinite retry
                        await self._bus.ack(msg_id)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Event loop error: %s", e)
                await asyncio.sleep(1)  # Brief pause before retry


async def main():
    """Entry point for the event engine process."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    db_url = os.environ.get("DATABASE_URL", "")
    litellm_base = os.environ.get("LITELLM_API_BASE", "")
    litellm_key = os.environ.get("LITELLM_API_KEY", "")

    engine = EventEngine(
        redis_url=redis_url,
        db_url=db_url,
        litellm_base=litellm_base,
        litellm_key=litellm_key,
    )

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(engine.stop()))

    await engine.start()


if __name__ == "__main__":
    asyncio.run(main())
