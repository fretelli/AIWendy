"""Ghost Trading service — simulated paper trading against real market prices.

Ghost trades are stored in Redis for fast access and periodically persisted
to the ghost_trades PostgreSQL table. They track against live prices but
never hit real exchanges.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

GHOST_TRADE_PREFIX = "keeltrader:ghost_trade:"
GHOST_INDEX_KEY = "keeltrader:ghost_trades:{user_id}:{status}"


class GhostTradingService:
    """Simulated trading service for strategy validation."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def open_trade(
        self,
        agent_id: str,
        user_id: str,
        symbol: str,
        side: str,
        amount: float,
        entry_price: float | None = None,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        reasoning: str = "",
    ) -> dict[str, Any]:
        """Open a new ghost trade.

        Args:
            agent_id: Agent that initiated the trade
            user_id: User ID
            symbol: Trading pair
            side: "buy" or "sell"
            amount: Position size
            entry_price: Entry price (None = fetch from Redis prices cache)
            stop_loss: Stop loss price
            take_profit: Take profit price
            reasoning: Trade reasoning

        Returns:
            Dict with trade ID and details
        """
        trade_id = str(uuid4())

        # Get current price if not specified
        if entry_price is None:
            cached_price = await self._redis.hget("keeltrader:prices", symbol)
            if cached_price:
                entry_price = float(cached_price)
            else:
                return {"success": False, "error": f"No price data for {symbol}"}

        now = datetime.utcnow().isoformat()
        trade = {
            "id": trade_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "entry_price": entry_price,
            "entry_time": now,
            "stop_loss": stop_loss or 0,
            "take_profit": take_profit or 0,
            "unrealized_pnl": 0,
            "realized_pnl": 0,
            "reasoning": reasoning,
            "status": "open",
            "created_at": now,
        }

        # Store trade
        key = f"{GHOST_TRADE_PREFIX}{trade_id}"
        await self._redis.hset(key, mapping={k: str(v) for k, v in trade.items()})

        # Index by user + status
        await self._redis.sadd(
            GHOST_INDEX_KEY.format(user_id=user_id, status="open"),
            trade_id,
        )

        logger.info(
            "Ghost trade opened: %s %s %s %.4f @ %.2f (SL=%.2f, TP=%.2f)",
            trade_id, side, symbol, amount, entry_price,
            stop_loss or 0, take_profit or 0,
        )

        return {"success": True, "trade": trade}

    async def close_trade(
        self,
        trade_id: str,
        exit_price: float | None = None,
    ) -> dict[str, Any]:
        """Close a ghost trade.

        Args:
            trade_id: Trade ID
            exit_price: Exit price (None = fetch from Redis prices cache)

        Returns:
            Dict with realized P&L
        """
        key = f"{GHOST_TRADE_PREFIX}{trade_id}"
        trade_data = await self._redis.hgetall(key)
        if not trade_data:
            return {"success": False, "error": f"Trade {trade_id} not found"}

        trade = {k.decode(): v.decode() for k, v in trade_data.items()}

        if trade.get("status") != "open":
            return {"success": False, "error": f"Trade {trade_id} is already {trade.get('status')}"}

        symbol = trade["symbol"]

        # Get exit price
        if exit_price is None:
            cached_price = await self._redis.hget("keeltrader:prices", symbol)
            if cached_price:
                exit_price = float(cached_price)
            else:
                return {"success": False, "error": f"No price data for {symbol}"}

        entry_price = float(trade["entry_price"])
        amount = float(trade["amount"])
        side = trade["side"]

        # Calculate P&L
        if side == "buy":
            pnl = (exit_price - entry_price) * amount
        else:
            pnl = (entry_price - exit_price) * amount

        now = datetime.utcnow().isoformat()

        # Update trade
        await self._redis.hset(key, mapping={
            "exit_price": str(exit_price),
            "exit_time": now,
            "realized_pnl": str(round(pnl, 4)),
            "unrealized_pnl": "0",
            "status": "closed",
        })

        # Move from open to closed index
        user_id = trade["user_id"]
        await self._redis.srem(
            GHOST_INDEX_KEY.format(user_id=user_id, status="open"),
            trade_id,
        )
        await self._redis.sadd(
            GHOST_INDEX_KEY.format(user_id=user_id, status="closed"),
            trade_id,
        )

        logger.info(
            "Ghost trade closed: %s %s @ %.2f → %.2f, P&L=%.4f",
            trade_id, symbol, entry_price, exit_price, pnl,
        )

        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "amount": amount,
            "pnl": round(pnl, 4),
            "pnl_pct": round(pnl / (entry_price * amount) * 100, 2) if entry_price * amount else 0,
        }

    async def update_unrealized_pnl(self, trade_id: str) -> dict[str, Any]:
        """Update unrealized P&L for an open trade using current price."""
        key = f"{GHOST_TRADE_PREFIX}{trade_id}"
        trade_data = await self._redis.hgetall(key)
        if not trade_data:
            return {}

        trade = {k.decode(): v.decode() for k, v in trade_data.items()}
        if trade.get("status") != "open":
            return {}

        symbol = trade["symbol"]
        cached_price = await self._redis.hget("keeltrader:prices", symbol)
        if not cached_price:
            return {}

        current_price = float(cached_price)
        entry_price = float(trade["entry_price"])
        amount = float(trade["amount"])
        side = trade["side"]

        if side == "buy":
            pnl = (current_price - entry_price) * amount
        else:
            pnl = (entry_price - current_price) * amount

        await self._redis.hset(key, "unrealized_pnl", str(round(pnl, 4)))

        # Check stop loss / take profit
        stop_loss = float(trade.get("stop_loss", 0))
        take_profit = float(trade.get("take_profit", 0))

        sl_triggered = False
        tp_triggered = False

        if stop_loss > 0:
            if (side == "buy" and current_price <= stop_loss) or \
               (side == "sell" and current_price >= stop_loss):
                sl_triggered = True

        if take_profit > 0:
            if (side == "buy" and current_price >= take_profit) or \
               (side == "sell" and current_price <= take_profit):
                tp_triggered = True

        return {
            "trade_id": trade_id,
            "symbol": symbol,
            "current_price": current_price,
            "unrealized_pnl": round(pnl, 4),
            "stop_loss_triggered": sl_triggered,
            "take_profit_triggered": tp_triggered,
        }

    async def list_trades(
        self,
        user_id: str,
        status: str = "open",
    ) -> list[dict[str, Any]]:
        """List ghost trades for a user.

        Args:
            user_id: User ID
            status: "open", "closed", or "all"
        """
        trades = []
        statuses = ["open", "closed"] if status == "all" else [status]

        for s in statuses:
            index_key = GHOST_INDEX_KEY.format(user_id=user_id, status=s)
            trade_ids = await self._redis.smembers(index_key)
            for tid in trade_ids:
                tid_str = tid.decode() if isinstance(tid, bytes) else tid
                key = f"{GHOST_TRADE_PREFIX}{tid_str}"
                data = await self._redis.hgetall(key)
                if data:
                    trade = {k.decode(): v.decode() for k, v in data.items()}
                    trades.append(trade)

        return trades

    async def portfolio_summary(self, user_id: str) -> dict[str, Any]:
        """Get ghost trading portfolio summary."""
        open_trades = await self.list_trades(user_id, "open")
        closed_trades = await self.list_trades(user_id, "closed")

        # Update unrealized P&L for open trades
        total_unrealized = 0.0
        for trade in open_trades:
            result = await self.update_unrealized_pnl(trade["id"])
            if result:
                total_unrealized += result.get("unrealized_pnl", 0)

        total_realized = sum(
            float(t.get("realized_pnl", 0)) for t in closed_trades
        )

        win_trades = [t for t in closed_trades if float(t.get("realized_pnl", 0)) > 0]
        loss_trades = [t for t in closed_trades if float(t.get("realized_pnl", 0)) < 0]

        return {
            "open_positions": len(open_trades),
            "closed_trades": len(closed_trades),
            "total_unrealized_pnl": round(total_unrealized, 4),
            "total_realized_pnl": round(total_realized, 4),
            "total_pnl": round(total_unrealized + total_realized, 4),
            "win_count": len(win_trades),
            "loss_count": len(loss_trades),
            "win_rate": round(len(win_trades) / len(closed_trades) * 100, 1) if closed_trades else 0,
            "open_trades": [
                {
                    "id": t["id"],
                    "symbol": t["symbol"],
                    "side": t["side"],
                    "entry_price": float(t["entry_price"]),
                    "amount": float(t["amount"]),
                    "unrealized_pnl": float(t.get("unrealized_pnl", 0)),
                }
                for t in open_trades
            ],
        }

    async def check_stops(self, user_id: str) -> list[dict[str, Any]]:
        """Check all open trades for SL/TP triggers.

        Returns list of triggered trades (for event emission).
        """
        open_trades = await self.list_trades(user_id, "open")
        triggered = []

        for trade in open_trades:
            result = await self.update_unrealized_pnl(trade["id"])
            if not result:
                continue

            if result.get("stop_loss_triggered"):
                triggered.append({
                    "trade_id": trade["id"],
                    "type": "stop_loss",
                    **result,
                })
            elif result.get("take_profit_triggered"):
                triggered.append({
                    "trade_id": trade["id"],
                    "type": "take_profit",
                    **result,
                })

        return triggered
