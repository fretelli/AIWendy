"""Execution tools — place_order, cancel_order, close_position.

All execution tools are gated by the 8-layer safety barrier.
These tools are registered only on the Executor agent (trust_level >= CONFIRM).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

from ..exchange import create_adapter
from ..execution.permissions import ExecutionPermission, TrustLevel
from ..execution.service import ExecutionResult, ExecutionService, OrderRequest

logger = logging.getLogger(__name__)

# Module-level references initialized at startup
_redis: aioredis.Redis | None = None


def init_execution(redis: aioredis.Redis) -> None:
    """Initialize execution tools with Redis instance."""
    global _redis
    _redis = redis


async def place_order(
    agent_id: str,
    user_id: str,
    exchange_name: str,
    symbol: str,
    side: str,
    order_type: str,
    amount: float,
    price: float | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    reasoning: str = "",
    api_key: str = "",
    api_secret: str = "",
    passphrase: str | None = None,
    permission: ExecutionPermission | None = None,
    trading_mode: str = "swap",
) -> dict[str, Any]:
    """Place an order through the 8-layer safety barrier.

    Args:
        agent_id: ID of the requesting agent
        user_id: User ID
        exchange_name: Exchange name (binance, okx, bybit)
        symbol: Trading pair (e.g., "BTC/USDT")
        side: "buy" or "sell"
        order_type: "market" or "limit"
        amount: Order amount in base currency
        price: Limit price (required for limit orders)
        stop_loss: Stop loss price
        take_profit: Take profit price
        reasoning: Agent's reasoning for the trade
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase (OKX)
        permission: Agent's execution permission config

    Returns:
        Dict with execution result, safety check details, and order ID
    """
    if _redis is None:
        return {"success": False, "error": "Execution service not initialized"}

    # Build order request
    order = OrderRequest(
        agent_id=agent_id,
        user_id=user_id,
        exchange=exchange_name,
        symbol=symbol,
        side=side,
        order_type=order_type,
        amount=amount,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reasoning=reasoning,
        trading_mode=trading_mode,
    )

    # Use default permission if not provided
    if permission is None:
        permission = ExecutionPermission(
            agent_id=agent_id,
            trust_level=TrustLevel.CONFIRM,
            max_order_usd=1000.0,
            daily_limit=10,
            allowed_symbols=[],
            require_stop_loss=True,
            max_position_pct=10.0,
            daily_loss_limit_usd=500.0,
        )

    # Run safety checks
    service = ExecutionService(_redis)
    result: ExecutionResult = await service.check_order(order, permission)

    if not result.allowed:
        blocked_check = result.checks[result.blocked_at - 1] if result.blocked_at else None
        return {
            "success": False,
            "blocked": True,
            "blocked_at_barrier": result.blocked_at,
            "blocked_reason": blocked_check.detail if blocked_check else "Unknown",
            "checks": [
                {"barrier": c.barrier, "name": c.name, "passed": c.passed, "detail": c.detail}
                for c in result.checks
            ],
        }

    if result.needs_confirmation:
        # Store pending order for confirmation
        order_id = str(uuid4())
        import json
        await _redis.hset(f"keeltrader:pending_order:{order_id}", mapping={
            "agent_id": agent_id,
            "user_id": user_id,
            "exchange": exchange_name,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "amount": str(amount),
            "price": str(price or ""),
            "stop_loss": str(stop_loss or ""),
            "reasoning": reasoning,
            "status": "pending_confirmation",
        })
        await _redis.expire(f"keeltrader:pending_order:{order_id}", 600)

        return {
            "success": True,
            "needs_confirmation": True,
            "order_id": order_id,
            "message": "Order pending user confirmation via Telegram",
            "checks": [
                {"barrier": c.barrier, "name": c.name, "passed": c.passed, "detail": c.detail}
                for c in result.checks
            ],
        }

    # Execute immediately (AUTO trust level)
    return await _execute_order(
        order, api_key, api_secret, passphrase,
    )


async def _execute_order(
    order: OrderRequest,
    api_key: str,
    api_secret: str,
    passphrase: str | None,
) -> dict[str, Any]:
    """Actually execute an order on the exchange via adapter."""
    try:
        adapter = create_adapter(
            exchange_name=order.exchange,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            trading_mode=order.trading_mode,
            use_cache=False,  # Fresh instance per execution for safety
        )
        try:
            result = await adapter.create_order(
                symbol=order.symbol,
                order_type=order.order_type,
                side=order.side,
                amount=order.amount,
                price=order.price,
            )

            # Increment daily order count
            if _redis:
                key = f"keeltrader:daily_orders:{order.user_id}:{order.agent_id}"
                await _redis.incr(key)
                await _redis.expire(key, 86400)

            return {
                "success": True,
                "order_id": result.id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "amount": order.amount,
                "price": result.price,
                "status": result.status,
                "ccxt_response": {
                    "id": result.id,
                    "status": result.status,
                    "filled": result.filled,
                    "remaining": result.remaining,
                    "cost": result.cost,
                    "average": result.average,
                    "datetime": result.timestamp,
                },
            }
        finally:
            await adapter.close()

    except Exception as e:
        logger.error("Order execution failed: %s", e)
        return {"success": False, "error": str(e)}


async def cancel_order(
    exchange_name: str,
    order_id: str,
    symbol: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
    trading_mode: str = "swap",
) -> dict[str, Any]:
    """Cancel an open order.

    Args:
        exchange_name: Exchange name
        order_id: Exchange order ID to cancel
        symbol: Trading pair
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        trading_mode: "spot" or "swap"
    """
    try:
        adapter = create_adapter(
            exchange_name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            trading_mode=trading_mode,
            use_cache=False,
        )
        try:
            result = await adapter.cancel_order(order_id, symbol)
            return {
                "success": True,
                "order_id": order_id,
                "status": result.get("status", "cancelled"),
            }
        finally:
            await adapter.close()
    except Exception as e:
        logger.error("Cancel order failed: %s", e)
        return {"success": False, "error": str(e)}


async def close_position(
    exchange_name: str,
    symbol: str,
    side: str,
    amount: float | None = None,
    api_key: str = "",
    api_secret: str = "",
    passphrase: str | None = None,
    trading_mode: str = "swap",
) -> dict[str, Any]:
    """Close a position (full or partial) with a market order.

    Args:
        exchange_name: Exchange name
        symbol: Trading pair
        side: Current position side ("buy"/"long" -> sell to close, "sell"/"short" -> buy to close)
        amount: Amount to close (None = full position)
        api_key: Exchange API key
        api_secret: Exchange API secret
        passphrase: Exchange passphrase
        trading_mode: "spot" or "swap"
    """
    if trading_mode == "spot":
        return {"success": False, "error": "Spot mode has no positions to close. Use place_order with side='sell' to sell holdings."}

    # Determine close side
    close_side = "sell" if side in ("buy", "long") else "buy"

    try:
        adapter = create_adapter(
            exchange_name=exchange_name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            trading_mode=trading_mode,
            use_cache=False,
        )
        try:
            # If no amount specified, fetch current position size
            if amount is None:
                positions = await adapter.fetch_positions(symbol)
                for pos in positions:
                    if pos.symbol == symbol:
                        amount = abs(pos.size)
                        break
                if not amount:
                    return {"success": False, "error": "No open position found"}

            result = await adapter.create_order(
                symbol=symbol,
                order_type="market",
                side=close_side,
                amount=amount,
            )
            return {
                "success": True,
                "symbol": symbol,
                "close_side": close_side,
                "amount": amount,
                "order_id": result.id,
                "status": result.status,
            }
        finally:
            await adapter.close()
    except Exception as e:
        logger.error("Close position failed: %s", e)
        return {"success": False, "error": str(e)}
