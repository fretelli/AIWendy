"""Backtest tools: backtest_strategy, replay_my_trades."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.journal.models import Journal

logger = get_logger(__name__)


async def backtest_strategy(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    strategy: str,
    params: Optional[dict] = None,
    days: int = 90,
    timeframe: str = "1d",
) -> dict[str, Any]:
    """对话式回测：描述策略 → 历史数据回测。"""
    from tools.market_tools import get_market_data

    params = params or {}

    # Fetch historical data
    limit = {"1h": 24, "4h": 6, "1d": 1}.get(timeframe, 1) * days
    limit = min(limit, 1000)

    market_data = await get_market_data(session, user_id, symbol, timeframe, limit)
    if "error" in market_data:
        return market_data

    ohlcv = market_data.get("ohlcv", [])
    if len(ohlcv) < 30:
        return {"error": "数据不足，至少需要 30 根 K 线"}

    closes = np.array([c[4] for c in ohlcv])
    highs = np.array([c[2] for c in ohlcv])
    lows = np.array([c[3] for c in ohlcv])
    timestamps = [c[0] for c in ohlcv]

    # Run strategy
    if strategy in ("ma_crossover", "均线突破", "均线交叉"):
        result = _backtest_ma_crossover(closes, timestamps, params)
    elif strategy in ("rsi", "rsi_reversal", "RSI反转"):
        result = _backtest_rsi(closes, timestamps, params)
    elif strategy in ("breakout", "突破", "区间突破"):
        result = _backtest_breakout(closes, highs, lows, timestamps, params)
    else:
        return {"error": f"不支持的策略: {strategy}。支持: ma_crossover, rsi, breakout"}

    return {
        "symbol": symbol,
        "strategy": strategy,
        "params": params,
        "period_days": days,
        "timeframe": timeframe,
        "data_points": len(ohlcv),
        **result,
    }


async def replay_my_trades(
    session: AsyncSession,
    user_id: UUID,
    journal_id: Optional[str] = None,
    days: int = 7,
    what_if: Optional[dict] = None,
) -> dict[str, Any]:
    """交易回放 what-if 分析。"""
    if journal_id:
        stmt = select(Journal).where(
            Journal.id == journal_id,
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
        result = await session.execute(stmt)
        journal = result.scalar_one_or_none()
        if not journal:
            return {"error": "日志不存在"}
        journals = [journal]
    else:
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(Journal)
            .where(
                Journal.user_id == user_id,
                Journal.deleted_at.is_(None),
                Journal.trade_date >= since,
            )
            .order_by(desc(Journal.trade_date))
            .limit(20)
        )
        result = await session.execute(stmt)
        journals = result.scalars().all()

    if not journals:
        return {"message": "没有找到交易记录"}

    what_if = what_if or {}
    replays = []

    for j in journals:
        actual_pnl = float(j.pnl or 0)
        entry = float(j.entry_price or 0)
        exit_price = float(j.exit_price or 0)
        size = float(j.position_size or 0)

        replay_entry = {
            "journal_id": str(j.id),
            "symbol": j.symbol,
            "direction": j.direction.value if j.direction else None,
            "actual": {
                "entry": entry,
                "exit": exit_price,
                "size": size,
                "pnl": actual_pnl,
            },
        }

        # What-if scenarios
        scenarios = []

        # Scenario 1: different exit
        if "exit_price" in what_if and entry > 0 and size > 0:
            wif_exit = float(what_if["exit_price"])
            direction = 1 if j.direction and j.direction.value == "long" else -1
            wif_pnl = (wif_exit - entry) * size * direction
            scenarios.append({
                "name": f"如果在 {wif_exit} 出场",
                "exit_price": wif_exit,
                "pnl": round(wif_pnl, 2),
                "pnl_diff": round(wif_pnl - actual_pnl, 2),
            })

        # Scenario 2: different size
        if "position_size" in what_if and entry > 0 and exit_price > 0:
            wif_size = float(what_if["position_size"])
            direction = 1 if j.direction and j.direction.value == "long" else -1
            wif_pnl = (exit_price - entry) * wif_size * direction
            scenarios.append({
                "name": f"如果仓位是 {wif_size}",
                "position_size": wif_size,
                "pnl": round(wif_pnl, 2),
                "pnl_diff": round(wif_pnl - actual_pnl, 2),
            })

        # Scenario 3: hold to now (fetch current price)
        # Skipped for now to avoid API calls per trade

        replay_entry["what_if"] = scenarios
        replays.append(replay_entry)

    total_actual = sum(float(j.pnl or 0) for j in journals)

    return {
        "replays": replays,
        "total_actual_pnl": round(total_actual, 2),
        "trade_count": len(replays),
    }


def _backtest_ma_crossover(
    closes: np.ndarray, timestamps: list, params: dict
) -> dict:
    """MA crossover backtest."""
    fast = params.get("fast_period", 10)
    slow = params.get("slow_period", 20)

    if len(closes) < slow + 1:
        return {"error": f"数据不足，需要至少 {slow + 1} 根K线"}

    # Calculate MAs
    trades = []
    position = 0  # 0=flat, 1=long
    entry_price = 0.0
    entry_time = 0

    for i in range(slow, len(closes)):
        fast_ma = np.mean(closes[i - fast + 1: i + 1])
        slow_ma = np.mean(closes[i - slow + 1: i + 1])
        prev_fast = np.mean(closes[i - fast: i])
        prev_slow = np.mean(closes[i - slow: i])

        # Golden cross: buy
        if prev_fast <= prev_slow and fast_ma > slow_ma and position == 0:
            position = 1
            entry_price = closes[i]
            entry_time = timestamps[i]

        # Death cross: sell
        elif prev_fast >= prev_slow and fast_ma < slow_ma and position == 1:
            pnl_pct = (closes[i] - entry_price) / entry_price * 100
            trades.append({
                "entry_time": entry_time,
                "exit_time": timestamps[i],
                "entry_price": float(entry_price),
                "exit_price": float(closes[i]),
                "pnl_pct": round(pnl_pct, 2),
            })
            position = 0

    return _calc_backtest_stats(trades, closes)


def _backtest_rsi(
    closes: np.ndarray, timestamps: list, params: dict
) -> dict:
    """RSI reversal backtest."""
    period = params.get("period", 14)
    oversold = params.get("oversold", 30)
    overbought = params.get("overbought", 70)

    if len(closes) < period + 2:
        return {"error": f"数据不足，需要至少 {period + 2} 根K线"}

    # Calculate RSI
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    trades = []
    position = 0
    entry_price = 0.0
    entry_time = 0

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        idx = i + 1  # closes index

        if rsi < oversold and position == 0:
            position = 1
            entry_price = closes[idx]
            entry_time = timestamps[idx]
        elif rsi > overbought and position == 1:
            pnl_pct = (closes[idx] - entry_price) / entry_price * 100
            trades.append({
                "entry_time": entry_time,
                "exit_time": timestamps[idx],
                "entry_price": float(entry_price),
                "exit_price": float(closes[idx]),
                "pnl_pct": round(pnl_pct, 2),
            })
            position = 0

    return _calc_backtest_stats(trades, closes)


def _backtest_breakout(
    closes: np.ndarray, highs: np.ndarray, lows: np.ndarray,
    timestamps: list, params: dict,
) -> dict:
    """Breakout backtest (Donchian channel)."""
    period = params.get("period", 20)
    if len(closes) < period + 1:
        return {"error": f"数据不足"}

    trades = []
    position = 0
    entry_price = 0.0
    entry_time = 0

    for i in range(period, len(closes)):
        upper = np.max(highs[i - period: i])
        lower = np.min(lows[i - period: i])

        if closes[i] > upper and position == 0:
            position = 1
            entry_price = closes[i]
            entry_time = timestamps[i]
        elif closes[i] < lower and position == 1:
            pnl_pct = (closes[i] - entry_price) / entry_price * 100
            trades.append({
                "entry_time": entry_time,
                "exit_time": timestamps[i],
                "entry_price": float(entry_price),
                "exit_price": float(closes[i]),
                "pnl_pct": round(pnl_pct, 2),
            })
            position = 0

    return _calc_backtest_stats(trades, closes)


def _calc_backtest_stats(trades: list[dict], closes: np.ndarray) -> dict:
    """Calculate backtest statistics."""
    if not trades:
        return {"trades": [], "stats": {"total_trades": 0, "message": "无交易信号"}}

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # Calculate equity curve
    equity = [100.0]
    for pnl in pnls:
        equity.append(equity[-1] * (1 + pnl / 100))

    # Max drawdown
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "trades": trades[-20:],  # Last 20 trades
        "stats": {
            "total_trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(trades) * 100, 1),
            "total_return_pct": round(equity[-1] - 100, 2),
            "avg_win_pct": round(np.mean(wins), 2) if wins else 0,
            "avg_loss_pct": round(np.mean(losses), 2) if losses else 0,
            "max_drawdown_pct": round(max_dd, 2),
            "profit_factor": round(
                abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf"), 2
            ) if wins else 0,
            "sharpe_ratio": round(
                np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0, 2
            ),
        },
        "equity_curve": [round(e, 2) for e in equity],
    }
