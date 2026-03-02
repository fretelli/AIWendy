"""Executor Agent — trade execution through safety barrier.

Places orders via Exchange Adapter (CCXT / IBKR), manages ghost trades,
tracks execution audit trail.  All orders pass through ExecutionService
safety checks.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

from .base import AgentConfig, AgentDependencies, AgentResult, BaseAgent
from ..engine.event_types import EventType
from ..tools.registry import register_tools_for_agent

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def create_executor(
    model: str = "anthropic/claude-haiku-4-5-20251001",
) -> ExecutorAgent:
    """Factory: create a configured Executor agent."""
    config = AgentConfig(
        agent_id="executor",
        name="Executor",
        description="Trade execution via Exchange Adapter (CCXT/IBKR) with safety barrier",
        agent_type="executor",
        model=model,
        temperature=0.1,  # Low temperature for precise execution
        max_tokens=2048,
        subscriptions=[
            EventType.ORDER_APPROVED.value,
            EventType.ORDER_REQUESTED.value,
            EventType.STOP_LOSS_TRIGGERED.value,
            EventType.CIRCUIT_BREAKER_ON.value,
        ],
        trust_level=2,  # CONFIRM — needs user approval for real trades
        max_order_usd=1000.0,
        daily_limit=10,
        allowed_symbols=[],  # Empty = allow all symbols (filtered by exchange adapter)
        cooldown_seconds=60,
        is_active=True,
    )
    return ExecutorAgent(config)


class ExecutorAgent(BaseAgent):
    """Executor Agent implementation."""

    def _default_system_prompt(self) -> str:
        template = TEMPLATE_DIR / "executor.txt"
        if template.exists():
            return template.read_text()
        return "You are the Executor Agent of KeelTrader."

    def _register_tools(self, agent: Agent) -> None:
        """Register execution and portfolio tools."""
        register_tools_for_agent(agent, "executor")

        @agent.tool
        async def execute_ghost_trade(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            side: str,
            amount: float,
            entry_price: float | None = None,
            stop_loss: float | None = None,
            take_profit: float | None = None,
            reasoning: str = "",
        ) -> dict[str, Any]:
            """Open a ghost (simulated) trade.

            Ghost trades track against real market prices but don't execute on exchange.

            Args:
                symbol: Trading pair
                side: "buy" or "sell"
                amount: Position size in base currency
                entry_price: Entry price (None = current market price)
                stop_loss: Stop loss price
                take_profit: Take profit price
                reasoning: Reasoning for the trade
            """
            trading_mode = ctx.deps.extra.get("trading_mode", "swap")
            if trading_mode == "spot" and side == "sell":
                return {"success": False, "error": "现货模式不支持做空，请使用 buy 方向开仓"}

            from ..execution.ghost import GhostTradingService
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                ghost = GhostTradingService(r)
                return await ghost.open_trade(
                    agent_id=ctx.deps.extra.get("agent_id", "executor"),
                    user_id=ctx.deps.user_id or "",
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reasoning=reasoning,
                )
            finally:
                await r.aclose()

        @agent.tool
        async def close_ghost_trade(
            ctx: RunContext[AgentDependencies],
            trade_id: str,
            exit_price: float | None = None,
        ) -> dict[str, Any]:
            """Close a ghost trade.

            Args:
                trade_id: Ghost trade ID
                exit_price: Exit price (None = current market price)
            """
            from ..execution.ghost import GhostTradingService
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                ghost = GhostTradingService(r)
                return await ghost.close_trade(trade_id, exit_price)
            finally:
                await r.aclose()

        @agent.tool
        async def list_ghost_trades(
            ctx: RunContext[AgentDependencies],
            status: str = "open",
        ) -> list[dict[str, Any]]:
            """List ghost trades.

            Args:
                status: Filter by status ("open", "closed", "all")
            """
            from ..execution.ghost import GhostTradingService
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                ghost = GhostTradingService(r)
                return await ghost.list_trades(
                    user_id=ctx.deps.user_id or "",
                    status=status,
                )
            finally:
                await r.aclose()

        @agent.tool
        async def ghost_portfolio_summary(
            ctx: RunContext[AgentDependencies],
        ) -> dict[str, Any]:
            """Get ghost trading portfolio summary with P&L."""
            from ..execution.ghost import GhostTradingService
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                ghost = GhostTradingService(r)
                return await ghost.portfolio_summary(ctx.deps.user_id or "")
            finally:
                await r.aclose()

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle events with executor-specific logic."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})

        if event_type == EventType.ORDER_APPROVED.value:
            return await self._execute_approved_order(payload, deps)
        elif event_type == EventType.STOP_LOSS_TRIGGERED.value:
            return await self._execute_stop_loss(payload, deps)
        elif event_type == EventType.CIRCUIT_BREAKER_ON.value:
            return await self._handle_circuit_breaker(payload, deps)
        elif event_type == EventType.ORDER_REQUESTED.value:
            return await self._handle_order_request(payload, deps)
        else:
            return await super().handle_event(event, deps)

    async def _execute_approved_order(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Execute an order that was approved by the user via Telegram."""
        order_id = payload.get("order_id", "")
        if not order_id:
            return AgentResult(
                agent_id=self.agent_id, success=False, message="No order_id in payload"
            )

        import redis.asyncio as aioredis

        r = aioredis.from_url(deps.redis_url)
        try:
            order_data = await r.hgetall(f"keeltrader:pending_order:{order_id}")
            if not order_data:
                return AgentResult(
                    agent_id=self.agent_id, success=False,
                    message=f"Pending order {order_id} not found or expired",
                )

            # Decode Redis bytes
            order = {k.decode(): v.decode() for k, v in order_data.items()}

            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=f"Order {order_id} execution started for {order.get('symbol', '?')}",
                data={"order_id": order_id, "order": order},
            )
        finally:
            await r.aclose()

    async def _execute_stop_loss(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Execute a stop-loss close."""
        symbol = payload.get("symbol", "")
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            message=f"Stop-loss triggered for {symbol} — closing position",
            data={"symbol": symbol, "action": "close_position"},
        )

    async def _handle_circuit_breaker(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle circuit breaker activation — cancel all pending orders."""
        logger.warning("Circuit breaker ON — cancelling all pending orders")
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            message="Circuit breaker activated — all execution suspended",
            data={"action": "suspend_all"},
        )

    async def _handle_order_request(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a new order request — run through safety checks."""
        context = payload.get("context", {})

        agent = self.get_pydantic_agent()
        prompt = (
            f"Order request: {context}\n\n"
            "Evaluate this order request. If it's a ghost trade, use execute_ghost_trade. "
            "For real orders, verify all safety parameters are present."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"order_request": context},
            )
        except Exception as e:
            logger.error("Order request handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )
