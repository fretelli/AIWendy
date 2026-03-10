"""Settings tools: update_settings, get_pnl."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from domain.journal.models import Journal, TradeResult

logger = get_logger(__name__)


async def get_pnl(
    session: AsyncSession,
    user_id: UUID,
    period: str = "today",
) -> dict[str, Any]:
    """查询盈亏。"""
    now = datetime.utcnow()
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    elif period == "all":
        since = datetime(2020, 1, 1)
    else:
        since = now - timedelta(days=int(period) if period.isdigit() else 7)

    stmt = select(Journal).where(
        Journal.user_id == user_id,
        Journal.deleted_at.is_(None),
        Journal.trade_date >= since,
    )
    result = await session.execute(stmt)
    journals = result.scalars().all()

    closed = [j for j in journals if j.result in (TradeResult.WIN, TradeResult.LOSS)]
    total_pnl = sum(float(j.pnl or 0) for j in closed)
    wins = len([j for j in closed if j.result == TradeResult.WIN])
    losses = len([j for j in closed if j.result == TradeResult.LOSS])

    # Group by date
    daily_pnl: dict[str, float] = {}
    for j in closed:
        if j.trade_date:
            day = j.trade_date.strftime("%Y-%m-%d")
            daily_pnl[day] = daily_pnl.get(day, 0) + float(j.pnl or 0)

    return {
        "period": period,
        "total_pnl": round(total_pnl, 2),
        "wins": wins,
        "losses": losses,
        "trade_count": len(closed),
        "daily_pnl": [
            {"date": d, "pnl": round(v, 2)}
            for d, v in sorted(daily_pnl.items())
        ],
    }


async def update_settings(
    session: AsyncSession,
    user_id: UUID,
    settings: dict[str, Any],
) -> dict[str, Any]:
    """更新风控/策略参数。"""
    from domain.user.models import User

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "用户不存在"}

    # Store risk settings in user's api_keys_encrypted JSON field
    current = user.api_keys_encrypted or {}
    risk_settings = current.get("risk_settings", {})

    allowed_keys = {
        "max_order_value_usd", "max_daily_loss_usd", "max_positions",
        "require_confirmation", "push_morning_report", "push_evening_report",
        "push_trade_alerts", "push_risk_alerts",
    }

    updated = {}
    for key, value in settings.items():
        if key in allowed_keys:
            risk_settings[key] = value
            updated[key] = value

    current["risk_settings"] = risk_settings
    user.api_keys_encrypted = current
    session.add(user)
    await session.commit()

    return {
        "updated": updated,
        "current_settings": risk_settings,
        "message": "设置已更新",
    }
