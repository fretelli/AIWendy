"""Analysis endpoints (stats + patterns)."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.cache_keys import analysis_patterns_key, analysis_stats_key
from core.cache_service import get_cache_service
from core.database import get_session
from domain.journal.models import Journal, TradeResult
from domain.journal.schemas import JournalStatistics
from domain.user.models import User

router = APIRouter()

Period = Literal["today", "week", "month", "year", "all"]


def _period_start(period: Period) -> Optional[datetime]:
    now = datetime.utcnow()
    if period == "all":
        return None
    if period == "today":
        return datetime.combine(date.today(), datetime.min.time())
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    if period == "year":
        return now - timedelta(days=365)
    return None


def _calculate_stats(journals: list[Journal]) -> JournalStatistics:
    stats = JournalStatistics()
    if not journals:
        return stats

    confidence_sum = 0.0
    confidence_count = 0
    stress_sum = 0.0
    stress_count = 0
    rule_violation_count = 0

    for journal in journals:
        stats.total_trades += 1

        if journal.pnl_amount is not None:
            stats.total_pnl += float(journal.pnl_amount)

        if journal.result == TradeResult.WIN:
            stats.winning_trades += 1
            if journal.pnl_amount is not None:
                pnl = float(journal.pnl_amount)
                stats.average_win = (
                    stats.average_win * (stats.winning_trades - 1) + pnl
                ) / stats.winning_trades
                stats.best_trade = max(stats.best_trade, pnl)

        elif journal.result == TradeResult.LOSS:
            stats.losing_trades += 1
            if journal.pnl_amount is not None:
                pnl = float(journal.pnl_amount)
                stats.average_loss = (
                    stats.average_loss * (stats.losing_trades - 1) + pnl
                ) / stats.losing_trades
                stats.worst_trade = min(stats.worst_trade, pnl)

        elif journal.result == TradeResult.BREAKEVEN:
            stats.breakeven_trades += 1
        elif journal.result == TradeResult.OPEN:
            stats.open_trades += 1

        if journal.confidence_level is not None:
            confidence_sum += journal.confidence_level
            confidence_count += 1

        if journal.stress_level is not None:
            stress_sum += journal.stress_level
            stress_count += 1

        if (not journal.followed_rules) or (
            journal.rule_violations and len(journal.rule_violations) > 0
        ):
            rule_violation_count += 1

    closed_trades = stats.winning_trades + stats.losing_trades + stats.breakeven_trades
    if closed_trades > 0:
        stats.win_rate = (stats.winning_trades / closed_trades) * 100

    if stats.average_loss != 0:
        stats.profit_factor = abs(stats.average_win / stats.average_loss)

    if confidence_count > 0:
        stats.average_confidence = confidence_sum / confidence_count

    if stress_count > 0:
        stats.average_stress = stress_sum / stress_count

    if stats.total_trades > 0:
        stats.rule_violation_rate = (rule_violation_count / stats.total_trades) * 100

    sorted_journals = sorted(
        [j for j in journals if j.result in [TradeResult.WIN, TradeResult.LOSS]],
        key=lambda x: x.trade_date or x.created_at,
    )

    current_streak = 0
    for journal in sorted_journals:
        if journal.result == TradeResult.WIN:
            current_streak = current_streak + 1 if current_streak >= 0 else 1
            stats.best_streak = max(stats.best_streak, current_streak)
        else:
            current_streak = current_streak - 1 if current_streak <= 0 else -1
            stats.worst_streak = min(stats.worst_streak, current_streak)

    stats.current_streak = current_streak
    return stats


@router.get("/stats", response_model=JournalStatistics)
async def get_stats(
    period: Period = Query("week"),
    project_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get basic trading statistics for a time period (optionally scoped to a project)."""
    cache = get_cache_service()
    cache_key = analysis_stats_key(
        str(current_user.id),
        str(project_id) if project_id else None,
        str(period),
    )
    cached = await cache.get_async(cache_key)
    if isinstance(cached, dict):
        return JournalStatistics(**cached)

    start_dt = _period_start(period)

    filters = [
        Journal.user_id == current_user.id,
        Journal.deleted_at.is_(None),
    ]
    if project_id is not None:
        filters.append(Journal.project_id == project_id)
    if start_dt is not None:
        filters.append(Journal.trade_date >= start_dt)

    result = await session.execute(select(Journal).where(and_(*filters)))
    journals = result.scalars().all()
    stats = _calculate_stats(journals)
    await cache.set_async(cache_key, stats.model_dump(), ttl=60)
    return stats


@router.get("/patterns")
async def get_patterns(
    period: Period = Query("month"),
    project_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get rule-violation + detected-pattern frequencies (optionally scoped to a project)."""
    cache = get_cache_service()
    cache_key = analysis_patterns_key(
        str(current_user.id),
        str(project_id) if project_id else None,
        str(period),
    )
    cached = await cache.get_async(cache_key)
    if isinstance(cached, dict):
        return cached

    start_dt = _period_start(period)

    filters = [
        Journal.user_id == current_user.id,
        Journal.deleted_at.is_(None),
    ]
    if project_id is not None:
        filters.append(Journal.project_id == project_id)
    if start_dt is not None:
        filters.append(Journal.trade_date >= start_dt)

    result = await session.execute(
        select(Journal.rule_violations, Journal.detected_patterns).where(and_(*filters))
    )
    violations_counter: Counter[str] = Counter()
    patterns_counter: Counter[str] = Counter()

    for rule_violations, detected_patterns in result.all():
        if rule_violations:
            violations_counter.update([str(v) for v in rule_violations])
        if detected_patterns:
            patterns_counter.update([str(p) for p in detected_patterns])

    payload = {
        "period": period,
        "project_id": str(project_id) if project_id else None,
        "rule_violations": [
            {"type": t, "count": c} for t, c in violations_counter.most_common(10)
        ],
        "detected_patterns": [
            {"pattern": p, "count": c} for p, c in patterns_counter.most_common(10)
        ],
    }
    await cache.set_async(cache_key, payload, ttl=60)
    return payload
