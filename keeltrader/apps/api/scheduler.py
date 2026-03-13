"""Asyncio scheduler — replaces Celery worker/beat.

Tasks:
- Every 60s trade sync
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
    sync_counter = 0
    last_rpg_refresh = None

    while True:
        try:
            now_cst = datetime.now(CST)
            today = now_cst.date()

            # Every 60s trade sync
            sync_counter += 1
            if sync_counter >= 6:  # 6 * 10s = 60s
                sync_counter = 0
                asyncio.create_task(_run_trade_sync())

            # Daily 00:05 RPG refresh (recalculate attributes, refresh quests, update leaderboard)
            if (
                now_cst.hour == 0
                and now_cst.minute >= 5
                and now_cst.minute < 10
                and last_rpg_refresh != today
            ):
                last_rpg_refresh = today
                asyncio.create_task(_run_rpg_daily_refresh())

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


async def _run_rpg_daily_refresh():
    """Daily RPG refresh: recalculate character attributes, refresh quests, update leaderboard."""
    logger.info("rpg_daily_refresh_start")
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
                    from domain.rpg.engine import recalculate_character, refresh_daily_quests, update_leaderboard
                    await recalculate_character(session, user.id)
                    await refresh_daily_quests(session, user.id)
                    await update_leaderboard(session, user.id)
                except Exception as e:
                    logger.error("rpg_refresh_user_failed", user_id=str(user.id), error=str(e))

            await session.commit()
            logger.info("rpg_daily_refresh_done", users=len(users))

    except Exception as e:
        logger.error("rpg_daily_refresh_failed", error=str(e))
