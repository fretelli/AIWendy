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
    """下单（需用户确认）。"""
    limits = {**DEFAULT_RISK_LIMITS, **(risk_limits or {})}

    # Step 1: 风控检查
    safety_check = await _check_risk_limits(
        session, user_id, symbol, side, amount, order_type, price, limits
    )
    if not safety_check["passed"]:
        return {
            "status": "rejected",
            "reason": safety_check["reason"],
            "details": safety_check,
        }

    # Step 2: 如果需要确认且未确认，返回确认请求
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
            "message": f"确认下单: {side} {amount} {symbol} ({order_type})?",
        }

    # Step 3: 执行下单
    connections = await _get_active_connections(session, user_id, exchange)
    if not connections:
        return {"status": "error", "message": "没有配置交易所连接"}

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
            "message": f"订单已执行: {side} {amount} {symbol}",
        }
    except Exception as e:
        logger.error("place_order_failed", symbol=symbol, error=str(e))
        return {"status": "error", "message": f"下单失败: {str(e)}"}
    finally:
        await adapter.close()


async def cancel_order(
    session: AsyncSession,
    user_id: UUID,
    order_id: str,
    symbol: str,
    exchange: Optional[str] = None,
) -> dict[str, Any]:
    """撤单。"""
    connections = await _get_active_connections(session, user_id, exchange)
    if not connections:
        return {"status": "error", "message": "没有配置交易所连接"}

    conn = connections[0]
    adapter = _build_adapter(conn)
    try:
        result = await adapter.cancel_order(order_id, symbol)
        return {
            "status": "cancelled",
            "order_id": order_id,
            "message": f"订单 {order_id} 已撤销",
        }
    except Exception as e:
        logger.error("cancel_order_failed", order_id=order_id, error=str(e))
        return {"status": "error", "message": f"撤单失败: {str(e)}"}
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
    """风控检查。"""
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
            "reason": f"订单金额 ${estimated_value:.2f} 超过上限 ${max_value:.2f}",
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
                    "reason": f"当前持仓数 {len(positions)} 已达上限 {max_positions}",
                    "estimated_value_usd": estimated_value,
                }
            await adapter.close()
        except Exception:
            pass

    return {
        "passed": True,
        "estimated_value_usd": estimated_value,
    }
