"""L0 Working Memory — manages current context for agent LLM calls.

Working memory is ephemeral and lives only within a single agent invocation.
It assembles the context window from:
- Recent conversation turns
- Active positions/alerts
- Latest market data snapshot
- High-priority memories from other layers
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


@dataclass
class WorkingMemoryContext:
    """Assembled context for an agent's LLM call."""

    user_id: str = ""
    agent_id: str = ""
    recent_messages: list[dict[str, str]] = field(default_factory=list)
    active_positions: list[dict[str, Any]] = field(default_factory=list)
    market_snapshot: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    pinned_memories: list[dict[str, Any]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_prompt_section(self) -> str:
        """Render working memory as a text section for the system prompt."""
        parts: list[str] = []

        if self.market_snapshot:
            lines = []
            for sym, price in self.market_snapshot.items():
                lines.append(f"  {sym}: ${float(price):,.2f}")
            if lines:
                parts.append("## 实时行情\n" + "\n".join(lines))

        if self.active_positions:
            lines = []
            for pos in self.active_positions[:5]:
                sym = pos.get("symbol", "?")
                side = pos.get("side", "?")
                pnl = pos.get("unrealized_pnl", 0)
                lines.append(f"  {sym} {side} PnL: ${pnl:+,.2f}")
            parts.append("## 活跃持仓\n" + "\n".join(lines))

        if self.alerts:
            lines = [f"  - {a.get('message', str(a))}" for a in self.alerts[:5]]
            parts.append("## 待处理告警\n" + "\n".join(lines))

        if self.pinned_memories:
            lines = [
                f"  - [{m.get('key', '?')}] {m.get('value', '')}"
                for m in self.pinned_memories[:5]
            ]
            parts.append("## 记忆备注\n" + "\n".join(lines))

        return "\n\n".join(parts) if parts else ""


class WorkingMemory:
    """Assembles L0 working memory from Redis state."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url

    async def assemble(
        self,
        user_id: str,
        agent_id: str,
    ) -> WorkingMemoryContext:
        """Assemble working memory context for an agent call."""
        ctx = WorkingMemoryContext(user_id=user_id, agent_id=agent_id)

        r = aioredis.from_url(self._redis_url)
        try:
            # Market snapshot from cached prices
            prices = await r.hgetall("keeltrader:prices")
            if prices:
                ctx.market_snapshot = {
                    (k.decode() if isinstance(k, bytes) else k): (
                        v.decode() if isinstance(v, bytes) else v
                    )
                    for k, v in prices.items()
                }

            # Active ghost positions
            open_ids = await r.smembers(f"keeltrader:ghost_trades:{user_id}:open")
            for trade_id in list(open_ids)[:5]:
                tid = trade_id.decode() if isinstance(trade_id, bytes) else trade_id
                trade_data = await r.hgetall(f"keeltrader:ghost_trade:{tid}")
                if trade_data:
                    ctx.active_positions.append(
                        {
                            k.decode() if isinstance(k, bytes) else k: (
                                v.decode() if isinstance(v, bytes) else v
                            )
                            for k, v in trade_data.items()
                        }
                    )

            # Pinned/important memories from Redis cache
            pinned_key = f"keeltrader:memory:pinned:{agent_id}:{user_id}"
            pinned_raw = await r.lrange(pinned_key, 0, 4)
            for raw in pinned_raw:
                try:
                    data = raw.decode() if isinstance(raw, bytes) else raw
                    ctx.pinned_memories.append(json.loads(data))
                except (json.JSONDecodeError, AttributeError):
                    pass

            # Circuit breaker status
            cb = await r.get("keeltrader:circuit_breaker")
            if cb and cb == b"1":
                ctx.alerts.append(
                    {"type": "circuit_breaker", "message": "Circuit Breaker 已激活 — 所有交易暂停"}
                )

        except Exception as e:
            logger.warning("Failed to assemble working memory: %s", e)
        finally:
            await r.aclose()

        return ctx
