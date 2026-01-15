"""Dashboard API endpoints with caching."""

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from apps.api.core.auth import get_current_user
from apps.api.core.cache_service import cache_async, get_cache_service, invalidate_cache
from apps.api.core.database import get_async_db
from apps.api.core.logging import get_logger
from apps.api.domain.coach.models import ChatSession
from apps.api.domain.journal.models import Journal
from apps.api.domain.report.models import Report, ReportType
from apps.api.domain.user.models import User
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
logger = get_logger(__name__)


@router.get("/stats")
@cache_async("dashboard:stats", ttl=300)  # 5 minutes cache
async def get_dashboard_stats(
    period: str = Query("week", description="Period: day, week, month, year"),
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Get dashboard statistics for the current user.
    Results are cached for 5 minutes.
    """
    user_id = current_user.id

    # Calculate period boundaries
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)  # Default to week

    # Build base query conditions
    journal_conditions = [Journal.user_id == user_id, Journal.trade_date >= start_date]
    if project_id:
        journal_conditions.append(Journal.project_id == project_id)

    # Get trading statistics
    trading_stats = await db.execute(
        select(
            func.count(Journal.id).label("total_trades"),
            func.count(func.nullif(Journal.pnl_amount > 0, False)).label(
                "winning_trades"
            ),
            func.count(func.nullif(Journal.pnl_amount < 0, False)).label(
                "losing_trades"
            ),
            func.sum(Journal.pnl_amount).label("total_pnl"),
            func.avg(Journal.pnl_amount).label("avg_pnl"),
            func.max(Journal.pnl_amount).label("max_profit"),
            func.min(Journal.pnl_amount).label("max_loss"),
        ).where(and_(*journal_conditions))
    )
    stats = trading_stats.one()

    # Calculate win rate
    win_rate = 0.0
    if stats.total_trades and stats.winning_trades:
        win_rate = (stats.winning_trades / stats.total_trades) * 100

    # Get psychological metrics
    psych_metrics = await db.execute(
        select(
            func.avg(Journal.emotion_before).label("avg_mood_before"),
            func.avg(Journal.emotion_after).label("avg_mood_after"),
        ).where(and_(*journal_conditions))
    )
    psych = psych_metrics.one()

    # Get recent chat sessions count
    chat_conditions = [
        ChatSession.user_id == user_id,
        ChatSession.created_at >= start_date,
    ]
    if project_id:
        chat_conditions.append(ChatSession.project_id == project_id)

    chat_count = await db.execute(
        select(func.count(ChatSession.id)).where(and_(*chat_conditions))
    )
    total_chats = chat_count.scalar()

    # Get recent reports count
    report_conditions = [Report.user_id == user_id, Report.created_at >= start_date]
    if project_id:
        report_conditions.append(Report.project_id == project_id)

    report_count = await db.execute(
        select(func.count(Report.id)).where(and_(*report_conditions))
    )
    total_reports = report_count.scalar()

    return {
        "period": period,
        "period_start": start_date.isoformat(),
        "period_end": now.isoformat(),
        "project_id": str(project_id) if project_id else None,
        "trading": {
            "total_trades": stats.total_trades or 0,
            "winning_trades": stats.winning_trades or 0,
            "losing_trades": stats.losing_trades or 0,
            "win_rate": round(win_rate, 2),
            "total_pnl": float(stats.total_pnl or 0),
            "avg_pnl": float(stats.avg_pnl or 0),
            "max_profit": float(stats.max_profit or 0),
            "max_loss": float(stats.max_loss or 0),
        },
        "psychological": {
            "avg_mood_before": float(psych.avg_mood_before or 0),
            "avg_mood_after": float(psych.avg_mood_after or 0),
            "mood_improvement": float(
                (psych.avg_mood_after or 0) - (psych.avg_mood_before or 0)
            ),
        },
        "activity": {
            "total_chats": total_chats or 0,
            "total_reports": total_reports or 0,
            "total_journals": stats.total_trades or 0,
        },
        "cached_at": datetime.utcnow().isoformat(),
    }


@router.get("/recent-activity")
@cache_async("dashboard:activity", ttl=60)  # 1 minute cache
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Get recent activity for the dashboard.
    Results are cached for 1 minute.
    """
    user_id = current_user.id

    # Get recent journals
    journal_query = select(
        Journal.id,
        Journal.trade_date,
        Journal.symbol,
        Journal.pnl_amount,
        Journal.trade_type,
    ).where(Journal.user_id == user_id)

    if project_id:
        journal_query = journal_query.where(Journal.project_id == project_id)

    journal_query = journal_query.order_by(Journal.trade_date.desc()).limit(limit)
    journals_result = await db.execute(journal_query)
    journals = journals_result.all()

    # Get recent chat sessions
    chat_query = select(
        ChatSession.id,
        ChatSession.title,
        ChatSession.coach_id,
        ChatSession.created_at,
        ChatSession.message_count,
    ).where(ChatSession.user_id == user_id)

    if project_id:
        chat_query = chat_query.where(ChatSession.project_id == project_id)

    chat_query = chat_query.order_by(ChatSession.created_at.desc()).limit(limit)
    chats_result = await db.execute(chat_query)
    chats = chats_result.all()

    # Get recent reports
    report_query = select(
        Report.id,
        Report.title,
        Report.report_type,
        Report.created_at,
        Report.status,
    ).where(Report.user_id == user_id)

    if project_id:
        report_query = report_query.where(Report.project_id == project_id)

    report_query = report_query.order_by(Report.created_at.desc()).limit(limit)
    reports_result = await db.execute(report_query)
    reports = reports_result.all()

    return {
        "recent_journals": [
            {
                "id": str(j.id),
                "trade_date": j.trade_date.isoformat(),
                "symbol": j.symbol,
                "pnl_amount": float(j.pnl_amount) if j.pnl_amount else None,
                "trade_type": j.trade_type,
            }
            for j in journals
        ],
        "recent_chats": [
            {
                "id": str(c.id),
                "title": c.title,
                "coach_id": str(c.coach_id) if c.coach_id else None,
                "created_at": c.created_at.isoformat(),
                "message_count": c.message_count,
            }
            for c in chats
        ],
        "recent_reports": [
            {
                "id": str(r.id),
                "title": r.title,
                "report_type": r.report_type.value if r.report_type else None,
                "created_at": r.created_at.isoformat(),
                "status": r.status.value if r.status else None,
            }
            for r in reports
        ],
        "cached_at": datetime.utcnow().isoformat(),
    }


@router.get("/performance-trend")
@cache_async("dashboard:performance", ttl=600)  # 10 minutes cache
async def get_performance_trend(
    days: int = Query(30, ge=7, le=365),
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Get performance trend data for charts.
    Results are cached for 10 minutes.
    """
    user_id = current_user.id
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Build query conditions
    conditions = [
        Journal.user_id == user_id,
        Journal.trade_date >= datetime.combine(start_date, datetime.min.time()),
        Journal.trade_date <= datetime.combine(end_date, datetime.max.time()),
    ]
    if project_id:
        conditions.append(Journal.project_id == project_id)

    # Get daily PnL data
    daily_pnl = await db.execute(
        select(
            func.date(Journal.trade_date).label("date"),
            func.sum(Journal.pnl_amount).label("daily_pnl"),
            func.count(Journal.id).label("trade_count"),
        )
        .where(and_(*conditions))
        .group_by(func.date(Journal.trade_date))
        .order_by(func.date(Journal.trade_date))
    )

    pnl_data = daily_pnl.all()

    # Calculate cumulative PnL
    cumulative_pnl = 0.0
    trend_data = []

    for row in pnl_data:
        cumulative_pnl += float(row.daily_pnl or 0)
        trend_data.append(
            {
                "date": row.date.isoformat(),
                "daily_pnl": float(row.daily_pnl or 0),
                "cumulative_pnl": cumulative_pnl,
                "trade_count": row.trade_count,
            }
        )

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": days,
        },
        "trend_data": trend_data,
        "summary": {
            "total_pnl": cumulative_pnl,
            "avg_daily_pnl": cumulative_pnl / len(trend_data) if trend_data else 0,
            "total_trading_days": len(trend_data),
        },
        "cached_at": datetime.utcnow().isoformat(),
    }


@router.post("/clear-cache")
@invalidate_cache("dashboard:*")
async def clear_dashboard_cache(
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Clear all dashboard cache for the current user.
    This is called automatically when data changes.
    """
    cache_service = get_cache_service()

    # Clear user-specific cache patterns
    patterns = [
        f"dashboard:stats:{current_user.id}:*",
        f"dashboard:activity:{current_user.id}:*",
        f"dashboard:performance:{current_user.id}:*",
    ]

    total_cleared = 0
    for pattern in patterns:
        cleared = await cache_service.clear_pattern_async(pattern)
        total_cleared += cleared

    logger.info(f"Cleared {total_cleared} cache entries for user {current_user.id}")

    return {
        "status": "success",
        "message": f"Cleared {total_cleared} cache entries",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/cache-status")
async def get_cache_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get cache status information for debugging.
    Admin only endpoint.
    """
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    cache_service = get_cache_service()

    # Get Redis info
    try:
        client = await cache_service.async_client
        info = await client.info()

        return {
            "redis_version": info.get("redis_version"),
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed"),
            "keyspace": info.get("db0", {}),
            "status": "connected",
        }
    except Exception as e:
        logger.error(f"Failed to get cache status: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }
