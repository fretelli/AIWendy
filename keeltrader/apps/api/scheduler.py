"""Asyncio scheduler — replaces Celery worker/beat.

Tasks:
- 08:30 Morning report
- 21:00 Evening summary
- Every 60s trade sync
- Every 5min market monitoring
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from core.database import get_db_context
from core.logging import get_logger

logger = get_logger(__name__)

# Beijing timezone offset
CST = timezone(timedelta(hours=8))

_scheduler_task: Optional[asyncio.Task] = None


async def start_scheduler():
    """Start the background scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = asyncio.create_task(_scheduler_loop())
    logger.info("Scheduler started")


async def stop_scheduler():
    """Stop the background scheduler."""
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Scheduler stopped")


async def _scheduler_loop():
    """Main scheduler loop."""
    last_morning = None
    last_evening = None
    sync_counter = 0

    while True:
        try:
            now_cst = datetime.now(CST)
            today = now_cst.date()

            # 08:30 Morning report
            if (
                now_cst.hour == 8
                and now_cst.minute >= 30
                and now_cst.minute < 35
                and last_morning != today
            ):
                last_morning = today
                asyncio.create_task(_run_morning_report())

            # 21:00 Evening summary
            if (
                now_cst.hour == 21
                and now_cst.minute < 5
                and last_evening != today
            ):
                last_evening = today
                asyncio.create_task(_run_evening_report())

            # Every 60s trade sync
            sync_counter += 1
            if sync_counter >= 6:  # 6 * 10s = 60s
                sync_counter = 0
                asyncio.create_task(_run_trade_sync())

            await asyncio.sleep(10)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("scheduler_error", error=str(e))
            await asyncio.sleep(30)


async def _run_trade_sync():
    """Sync trades from all active exchange connections."""
    try:
        from core.database import SessionLocal
        from services.trade_sync_service import TradeSyncService

        db = SessionLocal()
        try:
            service = TradeSyncService(db)
            result = service.sync_all_connections()
            connections = result.get("connections", [])
            total_inserted = sum(c.get("trades_inserted", 0) for c in connections)
            if total_inserted > 0:
                logger.info("trade_sync_completed", inserted=total_inserted)
        finally:
            db.close()
    except Exception as e:
        logger.error("trade_sync_failed", error=str(e))


async def _run_morning_report():
    """Generate and push morning report."""
    logger.info("generating_morning_report")
    try:
        from sqlalchemy import select
        from domain.user.models import User

        async with get_db_context() as session:
            # Get all active users
            result = await session.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()

            for user in users:
                try:
                    await _generate_report_for_user(session, user, "morning")
                except Exception as e:
                    logger.error("morning_report_user_failed", user_id=str(user.id), error=str(e))

    except Exception as e:
        logger.error("morning_report_failed", error=str(e))


async def _run_evening_report():
    """Generate and push evening report."""
    logger.info("generating_evening_report")
    try:
        from sqlalchemy import select
        from domain.user.models import User

        async with get_db_context() as session:
            result = await session.execute(
                select(User).where(User.is_active == True)
            )
            users = result.scalars().all()

            for user in users:
                try:
                    await _generate_report_for_user(session, user, "evening")
                except Exception as e:
                    logger.error("evening_report_user_failed", user_id=str(user.id), error=str(e))

    except Exception as e:
        logger.error("evening_report_failed", error=str(e))


async def _generate_report_for_user(session, user, report_type: str):
    """Generate a report for a specific user and push it."""
    from tools.trade_tools import get_positions
    from tools.settings_tools import get_pnl
    from tools.analysis_tools import analyze_performance
    from services.push_service import push_message

    if report_type == "morning":
        # Positions + overnight changes + today's plan
        positions = await get_positions(session, user.id)
        pnl = await get_pnl(session, user.id, period="today")

        pos_count = positions.get("count", 0)
        total_upnl = positions.get("total_unrealized_pnl", 0)

        message = f"""Morning Report ({datetime.now(CST).strftime('%Y-%m-%d')})

Positions: {pos_count} open, unrealized PnL ${total_upnl:+.2f}
"""
        if positions.get("positions"):
            for p in positions["positions"][:5]:
                if "error" not in p:
                    message += f"  - {p['symbol']}: {p['side']} {p['size']} | unrealized ${p['unrealized_pnl']:+.2f}\n"

        message += f"\nYesterday's PnL: ${pnl.get('total_pnl', 0):+.2f}"

    else:  # evening
        pnl = await get_pnl(session, user.id, period="today")
        perf = await analyze_performance(session, user.id, days=1)
        stats = perf.get("stats", {})

        message = f"""Evening Summary ({datetime.now(CST).strftime('%Y-%m-%d')})

Today's PnL: ${pnl.get('total_pnl', 0):+.2f}
Trades: {stats.get('total_trades', 0)}, win rate {stats.get('win_rate', 0)}%
"""

    # Save as system message in chat
    from domain.coach.models import ChatMessage as ChatMessageDB, ChatSession

    # Find or create a report session
    from sqlalchemy import select
    result = await session.execute(
        select(ChatSession).where(
            ChatSession.user_id == user.id,
            ChatSession.coach_id == "keeltrader-ai",
        ).order_by(ChatSession.updated_at.desc()).limit(1)
    )
    chat_session = result.scalar_one_or_none()

    if chat_session:
        msg = ChatMessageDB(
            session_id=chat_session.id,
            role="assistant",
            content=message,
        )
        session.add(msg)
        chat_session.message_count = (chat_session.message_count or 0) + 1
        chat_session.updated_at = datetime.utcnow()

    await session.commit()

    # Push to external channels
    await push_message(user.id, message, channel="all")
