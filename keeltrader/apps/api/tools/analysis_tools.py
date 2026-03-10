"""Analysis tools: analyze_performance, detect_patterns, analyze_market."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.analysis.models import BehaviorPattern
from domain.journal.models import Journal, TradeResult

logger = get_logger(__name__)


async def analyze_performance(
    session: AsyncSession,
    user_id: UUID,
    days: int = 30,
    symbol: Optional[str] = None,
) -> dict[str, Any]:
    """Analyze trading performance (win rate, profit factor, etc.)."""
    since = datetime.utcnow() - timedelta(days=days)
    conditions = [
        Journal.user_id == user_id,
        Journal.deleted_at.is_(None),
        Journal.trade_date >= since,
    ]
    if symbol:
        conditions.append(Journal.symbol.ilike(f"%{symbol}%"))

    stmt = select(Journal).where(and_(*conditions)).order_by(desc(Journal.trade_date))
    result = await session.execute(stmt)
    journals = result.scalars().all()

    if not journals:
        return {"message": f"No trades found in the last {days} days", "stats": {}}

    # Calculate stats
    total = len(journals)
    wins = [j for j in journals if j.result == TradeResult.WIN]
    losses = [j for j in journals if j.result == TradeResult.LOSS]
    open_trades = [j for j in journals if j.result == TradeResult.OPEN]

    total_pnl = sum(float(j.pnl or 0) for j in journals)
    avg_win = (
        sum(float(j.pnl or 0) for j in wins) / len(wins) if wins else 0
    )
    avg_loss = (
        sum(float(j.pnl or 0) for j in losses) / len(losses) if losses else 0
    )
    win_rate = len(wins) / (len(wins) + len(losses)) if (wins or losses) else 0
    profit_factor = (
        abs(sum(float(j.pnl or 0) for j in wins) / sum(float(j.pnl or 0) for j in losses))
        if losses and sum(float(j.pnl or 0) for j in losses) != 0
        else float("inf") if wins else 0
    )

    # Streak calculation
    max_win_streak = max_loss_streak = current_streak = 0
    current_type = None
    for j in sorted(journals, key=lambda x: x.trade_date or datetime.min):
        if j.result == TradeResult.WIN:
            if current_type == "win":
                current_streak += 1
            else:
                current_streak = 1
                current_type = "win"
            max_win_streak = max(max_win_streak, current_streak)
        elif j.result == TradeResult.LOSS:
            if current_type == "loss":
                current_streak += 1
            else:
                current_streak = 1
                current_type = "loss"
            max_loss_streak = max(max_loss_streak, current_streak)

    # Symbol breakdown
    symbols: dict[str, dict] = {}
    for j in journals:
        s = j.symbol or "unknown"
        if s not in symbols:
            symbols[s] = {"trades": 0, "pnl": 0, "wins": 0, "losses": 0}
        symbols[s]["trades"] += 1
        symbols[s]["pnl"] += float(j.pnl or 0)
        if j.result == TradeResult.WIN:
            symbols[s]["wins"] += 1
        elif j.result == TradeResult.LOSS:
            symbols[s]["losses"] += 1

    return {
        "period_days": days,
        "stats": {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "open": len(open_trades),
            "win_rate": round(win_rate * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else "∞",
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
        },
        "by_symbol": symbols,
    }


async def detect_patterns(
    session: AsyncSession,
    user_id: UUID,
    days: int = 14,
) -> dict[str, Any]:
    """Detect behavior patterns (FOMO, revenge trading, etc.)."""
    from domain.analytics.ml_analytics import MLAnalytics

    since = datetime.utcnow() - timedelta(days=days)
    stmt = (
        select(Journal)
        .where(
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
            Journal.trade_date >= since,
        )
        .order_by(desc(Journal.trade_date))
        .limit(50)
    )
    result = await session.execute(stmt)
    journals = result.scalars().all()

    if len(journals) < 3:
        return {"patterns": [], "message": "Not enough trades, need at least 3 for analysis"}

    ml = MLAnalytics()
    patterns = ml.detect_patterns(journals)

    # Also fetch recent DB-stored patterns
    pattern_stmt = (
        select(BehaviorPattern)
        .where(
            BehaviorPattern.user_id == user_id,
            BehaviorPattern.detected_at >= since,
            BehaviorPattern.resolved_at.is_(None),
        )
        .order_by(desc(BehaviorPattern.detected_at))
        .limit(10)
    )
    pattern_result = await session.execute(pattern_stmt)
    db_patterns = pattern_result.scalars().all()

    return {
        "detected_patterns": [
            {
                "type": p.pattern_type.value,
                "description": p.description,
                "confidence": round(p.confidence, 2),
                "affected_trades": p.affected_trades,
                "recommendations": p.recommendations,
            }
            for p in patterns
            if p.confidence >= 0.5
        ],
        "historical_patterns": [
            {
                "type": p.pattern_type.value,
                "confidence": float(p.confidence_score) if p.confidence_score else 0,
                "severity": p.severity,
                "detected_at": p.detected_at.isoformat() if p.detected_at else None,
                "intervention": p.intervention_suggested,
            }
            for p in db_patterns
        ],
    }


async def analyze_market(
    session: AsyncSession,
    user_id: UUID,
    symbol: str,
    timeframe: str = "4h",
) -> dict[str, Any]:
    """AI technical analysis of market (using LLM)."""
    from tools.market_tools import get_market_data

    # Fetch market data
    market_data = await get_market_data(
        session=session,
        user_id=user_id,
        symbol=symbol,
        timeframe=timeframe,
        limit=100,
    )

    if "error" in market_data:
        return market_data

    ohlcv = market_data.get("ohlcv", [])
    ticker = market_data.get("ticker", {})

    if not ohlcv:
        return {"error": f"Unable to fetch market data for {symbol}"}

    # Calculate basic indicators
    closes = [c[4] for c in ohlcv if len(c) >= 5]
    if len(closes) < 20:
        return {"error": "Insufficient data to calculate technical indicators"}

    import numpy as np
    closes_arr = np.array(closes)

    # MA
    ma20 = float(np.mean(closes_arr[-20:]))
    ma50 = float(np.mean(closes_arr[-50:])) if len(closes) >= 50 else None

    # RSI
    deltas = np.diff(closes_arr[-15:])
    gains = np.where(deltas > 0, deltas, 0)
    losses_arr = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses_arr) if len(losses_arr) > 0 else 1
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))

    # Volatility
    returns = np.diff(closes_arr[-21:]) / closes_arr[-21:-1]
    volatility = float(np.std(returns) * 100) if len(returns) > 0 else 0

    current_price = ticker.get("last") or closes[-1]
    trend = "bullish" if current_price > ma20 else "bearish"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": current_price,
        "analysis": {
            "trend": trend,
            "ma20": round(ma20, 4),
            "ma50": round(ma50, 4) if ma50 else None,
            "rsi": round(float(rsi), 1),
            "volatility_pct": round(volatility, 2),
            "price_vs_ma20_pct": round((current_price - ma20) / ma20 * 100, 2),
        },
        "signals": _generate_signals(current_price, ma20, ma50, float(rsi)),
    }


def _generate_signals(
    price: float, ma20: float, ma50: Optional[float], rsi: float
) -> list[str]:
    signals = []
    if rsi > 70:
        signals.append("RSI overbought (>70), potential pullback")
    elif rsi < 30:
        signals.append("RSI oversold (<30), potential bounce")

    if price > ma20:
        signals.append("Price above MA20, short-term bullish")
    else:
        signals.append("Price below MA20, short-term bearish")

    if ma50:
        if ma20 > ma50:
            signals.append("MA20 > MA50, medium-term uptrend")
        else:
            signals.append("MA20 < MA50, medium-term downtrend")

    return signals
