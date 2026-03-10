"""Execution tools: place_order, cancel_order (with safety checks)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.exchange.models import ExchangeConnection
from tools.trade_tools import _build_adapter, _get_active_connections

logger = get_logger(__name__)

# Default risk limits
DEFAULT_RISK_LIMITS = {
    "max_order_value_usd": 5000.0,
    "max_daily_loss_usd": 500.0,
    "max_positions": 5,
    "require_confirmation": True,
}


async def place_order(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    side: str,
    amount: float,
    order_type: str = "market",
    price: Optional[float] = None,
    exchange: Optional[str] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    risk_limits: Optional[dict] = None,
    confirmed: bool = False,
) -> dict[str, Any]:
    """Place an order (requires confirmation)."""
    limits = {**DEFAULT_RISK_LIMITS, **(risk_limits or {})}

    # Step 1: Risk check
    safety_check = await _check_risk_limits(
        session, user_id, symbol, side, amount, order_type, price, limits
    )
    if not safety_check["passed"]:
        return {
            "status": "rejected",
            "reason": safety_check["reason"],
            "details": safety_check,
        }

    # Step 2: Return confirmation request if needed
    if limits["require_confirmation"] and not confirmed:
        return {
            "status": "pending_confirmation",
            "order": {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "order_type": order_type,
                "price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "estimated_value_usd": safety_check.get("estimated_value_usd", 0),
            },
            "message": f"Confirm order: {side} {amount} {symbol} ({order_type})?",
        }

    # Step 3: Execute order
    connections = await _get_active_connections(session, user_id, exchange)
    if not connections:
        return {"status": "error", "message": "No exchange connection configured"}

    conn = connections[0]
    adapter = _build_adapter(conn)
    try:
        params = {}
        if stop_loss:
            params["stopLoss"] = {"triggerPrice": stop_loss}
        if take_profit:
            params["takeProfit"] = {"triggerPrice": take_profit}

        order = await adapter.create_order(
            symbol=symbol,
            order_type=order_type,
            side=side,
            amount=amount,
            price=price,
            params=params if params else None,
        )

        return {
            "status": "executed",
            "order": {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "type": order.order_type,
                "amount": order.amount,
                "price": order.price,
                "filled": order.filled,
                "status": order.status,
                "cost": order.cost,
            },
            "message": f"Order executed: {side} {amount} {symbol}",
        }
    except Exception as e:
        logger.error("place_order_failed", symbol=symbol, error=str(e))
        return {"status": "error", "message": f"Order failed: {str(e)}"}
    finally:
        await adapter.close()


async def cancel_order(
    session: AsyncSession,
    user_id: UUID,
    order_id: str,
    symbol: str,
    exchange: Optional[str] = None,
) -> dict[str, Any]:
    """Cancel an order."""
    connections = await _get_active_connections(session, user_id, exchange)
    if not connections:
        return {"status": "error", "message": "No exchange connection configured"}

    conn = connections[0]
    adapter = _build_adapter(conn)
    try:
        result = await adapter.cancel_order(order_id, symbol)
        return {
            "status": "cancelled",
            "order_id": order_id,
            "message": f"Order {order_id} cancelled",
        }
    except Exception as e:
        logger.error("cancel_order_failed", order_id=order_id, error=str(e))
        return {"status": "error", "message": f"Cancel failed: {str(e)}"}
    finally:
        await adapter.close()


async def _check_risk_limits(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    side: str,
    amount: float,
    order_type: str,
    price: Optional[float],
    limits: dict,
) -> dict[str, Any]:
    """Risk limit check."""
    estimated_value = 0.0

    # Estimate order value
    if price:
        estimated_value = amount * price
    else:
        # Try to get current price for market orders
        connections = await _get_active_connections(session, user_id)
        if connections:
            try:
                adapter = _build_adapter(connections[0])
                ticker = await adapter.fetch_ticker(symbol)
                if ticker.last:
                    estimated_value = amount * ticker.last
                await adapter.close()
            except Exception:
                pass

    # Check max order value
    max_value = limits.get("max_order_value_usd", 5000.0)
    if estimated_value > max_value:
        return {
            "passed": False,
            "reason": f"Order value ${estimated_value:.2f} exceeds limit ${max_value:.2f}",
            "estimated_value_usd": estimated_value,
        }

    # Check max positions
    max_positions = limits.get("max_positions", 5)
    if connections:
        try:
            adapter = _build_adapter(connections[0])
            positions = await adapter.fetch_positions()
            if len(positions) >= max_positions and side == "buy":
                await adapter.close()
                return {
                    "passed": False,
                    "reason": f"Current positions {len(positions)} reached limit {max_positions}",
                    "estimated_value_usd": estimated_value,
                }
            await adapter.close()
        except Exception:
            pass

    return {
        "passed": True,
        "estimated_value_usd": estimated_value,
    }
