"""Agent Matrix API routes — agent status, event submission, ghost trades."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Request/Response models ---


class AgentStatusResponse(BaseModel):
    agent_id: str
    name: str
    agent_type: str
    is_active: bool
    subscriptions: list[str]
    trust_level: int


class EventSubmitRequest(BaseModel):
    event_type: str
    user_id: str | None = None
    payload: dict[str, Any] = {}
    correlation_id: str | None = None


class EventSubmitResponse(BaseModel):
    success: bool
    event_id: str
    message: str = ""


class AgentChatRequest(BaseModel):
    message: str
    user_id: str
    agent_id: str = "orchestrator"


class AgentChatResponse(BaseModel):
    agent_id: str
    success: bool
    message: str
    data: dict[str, Any] = {}


# --- Routes ---


@router.get("/agents", response_model=list[AgentStatusResponse])
async def list_agents():
    """List all registered agents and their status."""
    try:
        from apps.agents.orchestrator import create_orchestrator
        from apps.agents.technical import create_technical_analyst
        from apps.agents.executor import create_executor
        from apps.agents.psychology import create_psychology_coach
        from apps.agents.guardian import create_guardian

        agents = [
            create_orchestrator(),
            create_technical_analyst(),
            create_executor(),
            create_psychology_coach(),
            create_guardian(),
        ]
        return [
            AgentStatusResponse(
                agent_id=a.config.agent_id,
                name=a.config.name,
                agent_type=a.config.agent_type,
                is_active=a.config.is_active,
                subscriptions=a.config.subscriptions,
                trust_level=a.config.trust_level,
            )
            for a in agents
        ]
    except Exception as e:
        logger.error("Failed to list agents: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events", response_model=EventSubmitResponse)
async def submit_event(req: EventSubmitRequest):
    """Submit an event to the event bus (for testing/manual triggers)."""
    import os

    import redis.asyncio as aioredis

    from apps.engine.event_types import Event, EventType

    try:
        event_type = EventType(req.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event type: {req.event_type}. "
            f"Valid types: {[e.value for e in EventType]}",
        )

    event = Event(
        type=event_type,
        source="api",
        user_id=req.user_id,
        payload=req.payload,
        correlation_id=req.correlation_id or str(uuid4()),
    )

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        await r.xadd(
            "keeltrader:events",
            event.to_stream_dict(),
            maxlen=10000,
        )
        return EventSubmitResponse(
            success=True,
            event_id=str(event.id),
            message=f"Event {event_type.value} submitted",
        )
    finally:
        await r.aclose()


@router.post("/agents/chat", response_model=AgentChatResponse)
async def chat_with_agent(req: AgentChatRequest):
    """Send a direct message to an agent (bypassing event bus).

    Primarily for testing and Telegram-less interaction.
    """
    import os

    from apps.agents.base import AgentDependencies

    deps = AgentDependencies(
        user_id=req.user_id,
        db_url=os.environ.get("DATABASE_URL", ""),
        redis_url=os.environ.get("REDIS_URL", ""),
        litellm_base=os.environ.get("LITELLM_API_BASE", ""),
        litellm_key=os.environ.get("LITELLM_API_KEY", ""),
    )

    try:
        if req.agent_id == "orchestrator":
            from apps.agents.orchestrator import create_orchestrator
            agent = create_orchestrator()
        elif req.agent_id in ("technical", "technical-analyst"):
            from apps.agents.technical import create_technical_analyst
            agent = create_technical_analyst()
        elif req.agent_id == "executor":
            from apps.agents.executor import create_executor
            agent = create_executor()
        elif req.agent_id in ("psychology", "psychology-coach", "coach"):
            from apps.agents.psychology import create_psychology_coach
            agent = create_psychology_coach()
        elif req.agent_id == "guardian":
            from apps.agents.guardian import create_guardian
            agent = create_guardian()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent_id}")

        result = await agent.run(req.message, deps=deps)
        return AgentChatResponse(
            agent_id=result.agent_id,
            success=result.success,
            message=result.message,
            data=result.data,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Agent chat failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/events/stream-info")
async def event_stream_info():
    """Get Redis Streams event bus statistics."""
    import os

    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        stream_key = "keeltrader:events"
        try:
            info = await r.xinfo_stream(stream_key)
            return {
                "stream": stream_key,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": info.get("groups", 0),
            }
        except Exception:
            return {"stream": stream_key, "length": 0, "message": "Stream not yet created"}
    finally:
        await r.aclose()


@router.get("/agents/health")
async def agent_matrix_health():
    """Get health status of all Agent Matrix services."""
    import json
    import os

    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        services: dict[str, Any] = {}

        # Event engine heartbeat
        engine_hb = await r.get("keeltrader:engine:heartbeat")
        if engine_hb:
            services["event_engine"] = {
                "status": "running",
                **json.loads(engine_hb.decode() if isinstance(engine_hb, bytes) else engine_hb),
            }
        else:
            services["event_engine"] = {"status": "not_running"}

        # Market streamer heartbeat
        streamer_hb = await r.get("keeltrader:streamer:heartbeat")
        if streamer_hb:
            services["market_streamer"] = {
                "status": "running",
                **json.loads(streamer_hb.decode() if isinstance(streamer_hb, bytes) else streamer_hb),
            }
        else:
            services["market_streamer"] = {"status": "not_running"}

        # Circuit breaker
        cb_active = await r.get("keeltrader:circuit_breaker")
        services["circuit_breaker"] = {
            "active": bool(cb_active and cb_active == b"1"),
        }

        # Event stream stats
        try:
            info = await r.xinfo_stream("keeltrader:events")
            services["event_bus"] = {
                "status": "active",
                "length": info.get("length", 0),
                "groups": info.get("groups", 0),
            }
        except Exception:
            services["event_bus"] = {"status": "not_initialized"}

        # Cached prices
        prices = await r.hgetall("keeltrader:prices")
        services["market_data"] = {
            "cached_symbols": len(prices),
        }

        # Overall status
        engine_up = services["event_engine"]["status"] == "running"
        overall = "healthy" if engine_up else "degraded"

        return {
            "status": overall,
            "services": services,
        }
    finally:
        await r.aclose()


@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get detailed status of a specific agent."""
    import os

    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    r = aioredis.from_url(redis_url)
    try:
        cb_active = await r.get("keeltrader:circuit_breaker")
        cooldown_key = f"keeltrader:agent_cooldown:{agent_id}"
        cooldown_ttl = await r.ttl(cooldown_key)

        return {
            "agent_id": agent_id,
            "circuit_breaker_active": bool(cb_active and cb_active == b"1"),
            "cooldown_remaining_seconds": max(0, cooldown_ttl),
        }
    finally:
        await r.aclose()
