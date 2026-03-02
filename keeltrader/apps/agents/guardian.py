"""Guardian Agent — risk management, trade blocking, position sizing.

Enforces the 8-layer safety barrier, monitors portfolio risk,
detects dangerous trading patterns, and manages the circuit breaker.
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


def create_guardian(
    model: str = "anthropic/claude-sonnet-4-20250514",
) -> GuardianAgent:
    """Factory: create a configured Guardian agent."""
    config = AgentConfig(
        agent_id="guardian",
        name="Guardian",
        description="Risk management — safety barrier enforcement and portfolio risk monitoring",
        agent_type="guardian",
        model=model,
        temperature=0.2,  # Low temperature for precise risk assessment
        max_tokens=4096,
        subscriptions=[
            EventType.TRADE_OPENED.value,
            EventType.TRADE_CLOSED.value,
            EventType.ORDER_REQUESTED.value,
            EventType.PATTERN_DETECTED.value,
            EventType.LOSS_STREAK.value,
            EventType.POSITION_RISK_HIGH.value,
            EventType.DAILY_LOSS_LIMIT.value,
            EventType.AGENT_RECOMMENDATION.value,
        ],
        trust_level=1,  # SUGGEST — can suggest but not execute trades
        cooldown_seconds=10,
        is_active=True,
    )
    return GuardianAgent(config)


class GuardianAgent(BaseAgent):
    """Guardian Agent implementation."""

    def _default_system_prompt(self) -> str:
        template = TEMPLATE_DIR / "guardian.txt"
        if template.exists():
            return template.read_text()
        return "You are the Guardian Agent of KeelTrader."

    def _register_tools(self, agent: Agent) -> None:
        """Register market, portfolio, memory, and communication tools."""
        register_tools_for_agent(agent, "guardian")

        @agent.tool
        async def evaluate_trade_risk(
            ctx: RunContext[AgentDependencies],
            symbol: str,
            side: str,
            amount: float,
            entry_price: float,
            stop_loss: float | None = None,
            leverage: float = 1.0,
            asset_class: str = "crypto",
        ) -> dict[str, Any]:
            """Evaluate risk for a proposed trade.

            Args:
                symbol: Trading pair (e.g., "BTC/USDT", "AAPL", "AAPL 250321C200")
                side: "buy" or "sell"
                amount: Position size in base currency (shares for stocks)
                entry_price: Planned entry price
                stop_loss: Stop-loss price (recommended but optional for stocks)
                leverage: Leverage multiplier (always 1.0 for stocks)
                asset_class: "crypto", "stock", "option", "future"
            """
            trading_mode = ctx.deps.extra.get("trading_mode", "swap")
            # Infer asset_class from trading_mode if not explicitly provided
            if asset_class == "crypto" and trading_mode in ("stock", "option", "future"):
                asset_class = trading_mode

            result: dict[str, Any] = {
                "symbol": symbol,
                "side": side,
                "trading_mode": trading_mode,
                "asset_class": asset_class,
                "decision": "REJECT",
                "reasons": [],
                "risk_metrics": {},
            }

            # === Asset-class-specific checks ===

            if asset_class == "stock":
                # Stocks: no leverage, no short-selling via simple orders
                if leverage > 1:
                    result["reasons"].append("股票不支持杠杆交易")
                    return result
                # Position value — higher limit for stocks ($25,000)
                position_value = amount * entry_price
                result["risk_metrics"]["position_value_usd"] = position_value
                if position_value > 25000:
                    result["reasons"].append(
                        f"股票仓位过大 (${position_value:,.0f}) — 建议不超过 $25,000"
                    )
                # Stop-loss recommended but not mandatory for stocks
                if stop_loss is not None:
                    risk_per_unit = abs(entry_price - stop_loss)
                    risk_usd = risk_per_unit * amount
                    result["risk_metrics"]["risk_usd"] = risk_usd
                    result["risk_metrics"]["risk_pct_of_entry"] = (
                        risk_per_unit / entry_price * 100 if entry_price else 0
                    )
                else:
                    result["risk_metrics"]["warning"] = "未设置止损 — 建议设置止损保护"

                result["risk_metrics"]["leverage"] = 1.0

            elif asset_class == "option":
                # Options: check naked position risk
                position_value = amount * entry_price * 100  # 1 contract = 100 shares
                result["risk_metrics"]["position_value_usd"] = position_value
                result["risk_metrics"]["contracts"] = amount
                result["risk_metrics"]["notional_per_contract"] = entry_price * 100

                if side == "sell":
                    # Selling options = potentially unlimited risk (naked)
                    result["risk_metrics"]["naked_risk"] = True
                    result["reasons"].append(
                        "卖出期权（裸仓）风险极高 — 请确认有对冲持仓"
                    )

                if position_value > 10000:
                    result["reasons"].append(
                        f"期权仓位过大 (${position_value:,.0f}) — 建议不超过 $10,000"
                    )

                result["risk_metrics"]["leverage"] = 1.0

            elif asset_class == "future":
                # Futures: inherent leverage, check margin
                position_value = amount * entry_price
                result["risk_metrics"]["position_value_usd"] = position_value

                # Futures have inherent leverage via margin
                if stop_loss is None:
                    result["reasons"].append(
                        "期货必须设置止损 — 杠杆合约风险极高"
                    )
                    return result

                risk_per_unit = abs(entry_price - stop_loss)
                risk_usd = risk_per_unit * amount
                result["risk_metrics"]["risk_usd"] = risk_usd
                result["risk_metrics"]["risk_pct_of_entry"] = (
                    risk_per_unit / entry_price * 100 if entry_price else 0
                )

                if position_value > 50000:
                    result["reasons"].append(
                        f"期货仓位过大 (${position_value:,.0f}) — 请确认保证金充足"
                    )

                result["risk_metrics"]["leverage"] = leverage

            else:
                # Crypto (default path — original logic)
                # Spot mode checks
                if trading_mode == "spot":
                    if leverage > 1:
                        result["reasons"].append("现货模式不支持杠杆")
                        return result
                    if side == "sell":
                        result["risk_metrics"]["warning"] = "现货卖出 — 请确认持有该资产"

                # Position value
                position_value = amount * entry_price
                result["risk_metrics"]["position_value_usd"] = position_value

                # Check stop-loss
                if stop_loss is None:
                    result["reasons"].append("没有设置止损 — 必须设置止损才能开仓")
                    return result

                # Calculate risk per trade
                if side == "buy":
                    risk_per_unit = entry_price - stop_loss
                else:
                    risk_per_unit = stop_loss - entry_price

                if risk_per_unit <= 0:
                    result["reasons"].append("止损方向错误 — 止损价格设置不合理")
                    return result

                risk_usd = risk_per_unit * amount * leverage
                result["risk_metrics"]["risk_usd"] = risk_usd
                result["risk_metrics"]["risk_pct_of_entry"] = (
                    risk_per_unit / entry_price * 100
                )

                # Leverage check
                if leverage > 10:
                    result["reasons"].append(f"杠杆过高 ({leverage}x) — 建议不超过 10x")
                    return result

                # Position size check (max $5000 per trade for crypto)
                if position_value * leverage > 5000:
                    result["reasons"].append(
                        f"仓位过大 (${position_value * leverage:,.0f}) — 建议不超过 $5,000"
                    )

                result["risk_metrics"]["leverage"] = leverage

            # If no blocking issues, approve
            if not result["reasons"]:
                result["decision"] = "APPROVE"
                result["reasons"].append("所有风控检查通过")
            elif all(
                "仓位过大" in r or "建议" in r or "warning" in str(r)
                for r in result["reasons"]
            ):
                result["decision"] = "APPROVE_WITH_CONDITIONS"

            return result

        @agent.tool
        async def check_portfolio_risk(
            ctx: RunContext[AgentDependencies],
        ) -> dict[str, Any]:
            """Check current portfolio risk status.

            Returns overall risk assessment including open positions,
            daily P&L, and concentration metrics.
            """
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                risk: dict[str, Any] = {
                    "circuit_breaker": False,
                    "open_positions": 0,
                    "risk_level": "low",
                    "warnings": [],
                }

                # Check circuit breaker
                cb = await r.get("keeltrader:circuit_breaker")
                if cb and cb == b"1":
                    risk["circuit_breaker"] = True
                    risk["risk_level"] = "critical"
                    risk["warnings"].append("Circuit Breaker 已激活")

                # Count ghost positions
                user_id = ctx.deps.user_id or ""
                open_ids = await r.smembers(f"keeltrader:ghost_trades:{user_id}:open")
                risk["open_positions"] = len(open_ids)

                if len(open_ids) >= 5:
                    risk["warnings"].append(f"活跃持仓过多 ({len(open_ids)})")
                    risk["risk_level"] = max(risk["risk_level"], "medium")

                return risk

            finally:
                await r.aclose()

        @agent.tool
        async def activate_circuit_breaker(
            ctx: RunContext[AgentDependencies],
            reason: str,
        ) -> str:
            """Activate the circuit breaker to halt all trading.

            Only use this for critical risk situations.

            Args:
                reason: Why the circuit breaker is being activated
            """
            import redis.asyncio as aioredis

            r = aioredis.from_url(ctx.deps.redis_url)
            try:
                from ..execution.circuit_breaker import CircuitBreaker
                cb = CircuitBreaker(r)
                await cb.activate(
                    reason=reason,
                    activated_by=f"guardian:{ctx.deps.user_id or 'system'}",
                )
                logger.warning("Guardian activated circuit breaker: %s", reason)
                return f"Circuit Breaker 已激活: {reason}"
            finally:
                await r.aclose()

        @agent.tool
        async def record_risk_event(
            ctx: RunContext[AgentDependencies],
            event_type: str,
            details: str,
            severity: str = "medium",
        ) -> str:
            """Record a risk event in memory for audit and pattern tracking.

            Args:
                event_type: Type of risk event
                details: Description
                severity: low/medium/high/critical
            """
            from ..memory.tools import memory_update

            await memory_update(
                key=f"risk_event:{event_type}",
                value={
                    "type": event_type,
                    "details": details,
                    "severity": severity,
                    "user_id": ctx.deps.user_id,
                },
                layer="episodic",
                agent_id="guardian",
                user_id=ctx.deps.user_id,
                importance={"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}.get(
                    severity, 0.5
                ),
            )
            return f"Risk event recorded: {event_type} ({severity})"

    async def handle_event(
        self, event: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle events with guardian-specific logic."""
        event_type = event.get("type", "")
        payload = event.get("payload", {})

        if event_type == EventType.ORDER_REQUESTED.value:
            return await self._evaluate_order(payload, deps)
        elif event_type == EventType.TRADE_OPENED.value:
            return await self._check_new_trade(payload, deps)
        elif event_type == EventType.LOSS_STREAK.value:
            return await self._handle_loss_streak(payload, deps)
        elif event_type == EventType.DAILY_LOSS_LIMIT.value:
            return await self._handle_daily_loss_limit(payload, deps)
        elif event_type == EventType.POSITION_RISK_HIGH.value:
            return await self._handle_high_risk_position(payload, deps)
        elif event_type == EventType.AGENT_RECOMMENDATION.value:
            return await self._evaluate_recommendation(payload, deps)
        else:
            return await super().handle_event(event, deps)

    async def _evaluate_order(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Evaluate an order request through safety checks."""
        agent = self.get_pydantic_agent()
        prompt = (
            f"Order request: {payload}\n\n"
            "1. Use evaluate_trade_risk to assess this order.\n"
            "2. Use check_portfolio_risk to see current risk status.\n"
            "3. If approved, clearly state the conditions.\n"
            "4. If rejected, explain exactly why and what would make it acceptable.\n"
            "5. Record the evaluation with record_risk_event."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "order_evaluation"},
            )
        except Exception as e:
            logger.error("Order evaluation failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False,
                message=f"订单评估失败: {e}",
            )

    async def _check_new_trade(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Check a newly opened trade for risk compliance."""
        symbol = payload.get("symbol", "?")
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            message=f"New trade registered for monitoring: {symbol}",
            data={"trigger": "trade_opened", "symbol": symbol},
        )

    async def _handle_loss_streak(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a loss streak — escalate to Psychology Coach."""
        streak_count = payload.get("streak_count", 3)

        agent = self.get_pydantic_agent()
        prompt = (
            f"Loss streak detected: {streak_count} consecutive losses.\n\n"
            "1. Check portfolio risk.\n"
            "2. Record this risk event.\n"
            "3. If streak >= 5, consider activating circuit breaker.\n"
            "4. Provide risk assessment and recommend Psychology Coach consultation."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "loss_streak", "streak_count": streak_count},
                events_emitted=[EventType.BEHAVIOR_ALERT.value],
            )
        except Exception as e:
            logger.error("Loss streak handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_daily_loss_limit(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle daily loss limit breach — activate circuit breaker."""
        agent = self.get_pydantic_agent()
        prompt = (
            f"CRITICAL: Daily loss limit breached.\n"
            f"Details: {payload}\n\n"
            "1. Activate the circuit breaker immediately.\n"
            "2. Record this critical risk event.\n"
            "3. Explain the situation clearly for the user."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "daily_loss_limit"},
                events_emitted=[EventType.CIRCUIT_BREAKER_ON.value],
            )
        except Exception as e:
            logger.error("Daily loss limit handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _handle_high_risk_position(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Handle a high-risk position alert."""
        symbol = payload.get("symbol", "?")
        agent = self.get_pydantic_agent()
        prompt = (
            f"High risk position detected: {symbol}\n"
            f"Details: {payload}\n\n"
            "1. Evaluate the current risk.\n"
            "2. Record the risk event.\n"
            "3. Suggest risk reduction actions (reduce position, tighten stop)."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "position_risk_high", "symbol": symbol},
            )
        except Exception as e:
            logger.error("High risk position handling failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )

    async def _evaluate_recommendation(
        self, payload: dict[str, Any], deps: AgentDependencies
    ) -> AgentResult:
        """Evaluate a trade recommendation from another agent."""
        source_agent = payload.get("source_agent", "unknown")
        agent = self.get_pydantic_agent()
        prompt = (
            f"Trade recommendation from {source_agent}:\n{payload}\n\n"
            "1. Evaluate the trade risk using evaluate_trade_risk.\n"
            "2. Check current portfolio risk.\n"
            "3. Return APPROVE, APPROVE_WITH_CONDITIONS, or REJECT with reasoning."
        )

        try:
            result = await agent.run(prompt, deps=deps)
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                message=result.data if isinstance(result.data, str) else str(result.data),
                data={"trigger": "recommendation_evaluation", "source": source_agent},
            )
        except Exception as e:
            logger.error("Recommendation evaluation failed: %s", e)
            return AgentResult(
                agent_id=self.agent_id, success=False, message=str(e),
            )
