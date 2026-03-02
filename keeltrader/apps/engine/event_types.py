"""Event type definitions for the KeelTrader event engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """All event types in the system."""

    # Market events
    PRICE_ALERT = "price.alert"
    KLINE_PATTERN = "kline.pattern"
    FUNDING_RATE_CHANGE = "funding_rate.change"

    # Trade events
    TRADE_OPENED = "trade.opened"
    TRADE_CLOSED = "trade.closed"
    TRADE_MODIFIED = "trade.modified"

    # Order events
    ORDER_REQUESTED = "order.requested"
    ORDER_APPROVED = "order.approved"
    ORDER_REJECTED = "order.rejected"
    ORDER_EXECUTED = "order.executed"
    ORDER_FAILED = "order.failed"

    # Risk events
    STOP_LOSS_TRIGGERED = "stop_loss.triggered"
    POSITION_RISK_HIGH = "position.risk_high"
    LOSS_STREAK = "loss.streak"
    DAILY_LOSS_LIMIT = "daily_loss.limit"

    # Pattern events
    PATTERN_DETECTED = "pattern.detected"
    BEHAVIOR_ALERT = "behavior.alert"

    # Agent events
    AGENT_ANALYSIS = "agent.analysis"
    AGENT_RECOMMENDATION = "agent.recommendation"
    AGENT_ERROR = "agent.error"

    # Guardian events
    CIRCUIT_BREAKER_ON = "circuit_breaker.on"
    CIRCUIT_BREAKER_OFF = "circuit_breaker.off"
    TRADING_BLOCKED = "trading.blocked"
    TRADING_UNBLOCKED = "trading.unblocked"

    # User events
    USER_MESSAGE = "user.message"
    USER_CONFIRMATION = "user.confirmation"
    USER_COMMAND = "user.command"

    # Scheduled events
    DAILY_REVIEW = "daily.review"
    WEEKLY_REVIEW = "weekly.review"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    HEALTH_CHECK = "health.check"


class Event(BaseModel):
    """Immutable event record."""

    id: UUID = Field(default_factory=uuid4)
    type: EventType
    source: str  # component that emitted the event
    user_id: UUID | None = None
    agent_id: str | None = None
    payload: dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID | None = None  # parent event that caused this one

    def to_stream_dict(self) -> dict[str, str]:
        """Serialize for Redis Streams (all values must be strings)."""
        return {
            "id": str(self.id),
            "type": self.type.value,
            "source": self.source,
            "user_id": str(self.user_id) if self.user_id else "",
            "agent_id": self.agent_id or "",
            "payload": self.model_dump_json(include={"payload"}).strip('{"payload":').rstrip("}") if self.payload else "{}",
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": str(self.correlation_id),
            "causation_id": str(self.causation_id) if self.causation_id else "",
        }

    @classmethod
    def from_stream_dict(cls, data: dict[str, str]) -> Event:
        """Deserialize from Redis Streams."""
        import json

        return cls(
            id=UUID(data["id"]),
            type=EventType(data["type"]),
            source=data["source"],
            user_id=UUID(data["user_id"]) if data.get("user_id") else None,
            agent_id=data.get("agent_id") or None,
            payload=json.loads(data.get("payload", "{}")),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=UUID(data["correlation_id"]),
            causation_id=UUID(data["causation_id"]) if data.get("causation_id") else None,
        )
