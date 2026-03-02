"""Execution service — 8-layer safety barrier for trade execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import redis.asyncio as aioredis

from .circuit_breaker import CircuitBreaker
from .permissions import ExecutionPermission, TrustLevel

logger = logging.getLogger(__name__)


@dataclass
class OrderRequest:
    """Incoming order request from an agent."""
    agent_id: str
    user_id: str
    exchange: str
    symbol: str
    side: str  # buy / sell
    order_type: str  # market / limit
    amount: float
    price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    reasoning: str = ""


@dataclass
class SafetyCheckResult:
    """Result of a single safety barrier check."""
    barrier: int  # 1-8
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ExecutionResult:
    """Result of the full execution pipeline."""
    allowed: bool
    checks: list[SafetyCheckResult]
    blocked_at: int | None = None  # Which barrier blocked
    needs_confirmation: bool = False
    order_id: str | None = None  # If executed


class ExecutionService:
    """8-layer safety barrier for trade execution.

    Barrier 1: Trust level check
    Barrier 2: Order value limit
    Barrier 3: Daily order count limit
    Barrier 4: Daily P&L loss limit
    Barrier 5: Symbol allowlist
    Barrier 6: Stop loss requirement
    Barrier 7: Circuit breaker check
    Barrier 8: User confirmation (Telegram)
    """

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis
        self._circuit_breaker = CircuitBreaker(redis)

    async def check_order(
        self,
        order: OrderRequest,
        permission: ExecutionPermission,
        required_trust: TrustLevel = TrustLevel.CONFIRM,
    ) -> ExecutionResult:
        """Run all 8 safety barriers on an order request."""
        checks: list[SafetyCheckResult] = []

        # Barrier 1: Trust level
        check1 = SafetyCheckResult(
            barrier=1, name="trust_level",
            passed=permission.trust_level >= required_trust,
            detail=f"agent={permission.trust_level.name}, required={required_trust.name}",
        )
        checks.append(check1)
        if not check1.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=1)

        # Barrier 2: Order value limit
        order_value = order.amount * (order.price or 0)
        check2 = SafetyCheckResult(
            barrier=2, name="order_value",
            passed=order_value <= permission.max_order_usd or permission.max_order_usd == 0,
            detail=f"value=${order_value:.2f}, max=${permission.max_order_usd:.2f}",
        )
        checks.append(check2)
        if not check2.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=2)

        # Barrier 3: Daily order count
        daily_count = await self._get_daily_order_count(order.agent_id, order.user_id)
        check3 = SafetyCheckResult(
            barrier=3, name="daily_limit",
            passed=daily_count < permission.daily_limit or permission.daily_limit == 0,
            detail=f"count={daily_count}, max={permission.daily_limit}",
        )
        checks.append(check3)
        if not check3.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=3)

        # Barrier 4: Daily P&L loss limit
        daily_pnl = await self._get_daily_pnl(order.user_id)
        check4 = SafetyCheckResult(
            barrier=4, name="daily_loss_limit",
            passed=daily_pnl > -permission.daily_loss_limit_usd,
            detail=f"pnl=${daily_pnl:.2f}, limit=-${permission.daily_loss_limit_usd:.2f}",
        )
        checks.append(check4)
        if not check4.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=4)

        # Barrier 5: Symbol allowlist
        check5 = SafetyCheckResult(
            barrier=5, name="symbol_allowed",
            passed=not permission.allowed_symbols or order.symbol in permission.allowed_symbols,
            detail=f"symbol={order.symbol}",
        )
        checks.append(check5)
        if not check5.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=5)

        # Barrier 6: Stop loss requirement
        check6 = SafetyCheckResult(
            barrier=6, name="stop_loss",
            passed=not permission.require_stop_loss or order.stop_loss is not None,
            detail=f"has_sl={order.stop_loss is not None}, required={permission.require_stop_loss}",
        )
        checks.append(check6)
        if not check6.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=6)

        # Barrier 7: Circuit breaker
        cb_active = await self._circuit_breaker.is_active()
        check7 = SafetyCheckResult(
            barrier=7, name="circuit_breaker",
            passed=not cb_active,
            detail=f"active={cb_active}",
        )
        checks.append(check7)
        if not check7.passed:
            return ExecutionResult(allowed=False, checks=checks, blocked_at=7)

        # Barrier 8: User confirmation (for CONFIRM trust level)
        needs_confirm = permission.trust_level == TrustLevel.CONFIRM
        check8 = SafetyCheckResult(
            barrier=8, name="user_confirmation",
            passed=True,  # Check passes, but execution waits for confirmation
            detail=f"needs_confirmation={needs_confirm}",
        )
        checks.append(check8)

        return ExecutionResult(
            allowed=True,
            checks=checks,
            needs_confirmation=needs_confirm,
        )

    async def _get_daily_order_count(self, agent_id: str, user_id: str) -> int:
        """Get today's order count for an agent+user pair."""
        key = f"keeltrader:daily_orders:{user_id}:{agent_id}"
        count = await self._redis.get(key)
        return int(count) if count else 0

    async def _get_daily_pnl(self, user_id: str) -> float:
        """Get today's P&L for a user."""
        key = f"keeltrader:daily_pnl:{user_id}"
        pnl = await self._redis.get(key)
        return float(pnl) if pnl else 0.0
