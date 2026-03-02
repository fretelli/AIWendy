"""Trust levels and execution permissions for the safety barrier system."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel


class TrustLevel(IntEnum):
    """Agent trust levels for execution permissions.

    Progression: OBSERVE → SUGGEST → CONFIRM → AUTO
    """
    OBSERVE = 0   # Can only watch, no trade suggestions
    SUGGEST = 1   # Can suggest trades (shown to user, no execution)
    CONFIRM = 2   # Can request trade execution (requires user confirmation via TG)
    AUTO = 3      # Can execute trades automatically (within limits)


class ExecutionPermission(BaseModel):
    """Per-agent execution permission configuration."""

    agent_id: str
    trust_level: TrustLevel = TrustLevel.OBSERVE
    max_order_usd: float = 0.0
    daily_limit: int = 0  # max orders per day
    allowed_symbols: list[str] = []
    require_stop_loss: bool = True
    max_position_pct: float = 5.0  # max % of portfolio per trade
    daily_loss_limit_usd: float = 500.0  # lock all agents if exceeded
