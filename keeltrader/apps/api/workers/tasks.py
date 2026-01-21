"""Maintenance/background tasks (Celery)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import UUID

from celery import Task
from sqlalchemy import and_, select

from core.database import SessionLocal
from core.logging import get_logger
from domain.user.models import SubscriptionTier, User, UserSession
from domain.journal.models import Journal
from domain.analytics.ml_analytics import MLAnalytics
from tasks.notification_tasks import send_pattern_alert_task, send_risk_alert_task
from services.trade_sync_service import TradeSyncService
from workers.celery_app import celery_app

logger = get_logger(__name__)


class DatabaseTask(Task):
    """Celery task base with best-effort DB lifecycle helpers."""

    def _get_db(self):
        return SessionLocal()


@celery_app.task(bind=True, base=DatabaseTask)
def cleanup_expired_user_sessions(self) -> Dict[str, Any]:
    """Delete expired/revoked user sessions."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        deleted = (
            db.query(UserSession)
            .filter(
                and_(
                    UserSession.user_id.isnot(None),
                    (UserSession.expires_at < now)
                    | (UserSession.revoked_at.isnot(None)),
                )
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("cleanup_expired_user_sessions_done", deleted=int(deleted or 0))
        return {
            "status": "success",
            "deleted": int(deleted or 0),
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        db.rollback()
        logger.error("cleanup_expired_user_sessions_failed", error=str(e))
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()


@celery_app.task(bind=True, base=DatabaseTask)
def update_subscription_status(self) -> Dict[str, Any]:
    """Downgrade users whose subscriptions are expired."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        expired_users = (
            db.query(User)
            .filter(
                and_(
                    User.subscription_tier != SubscriptionTier.free,
                    User.subscription_expires_at.isnot(None),
                    User.subscription_expires_at < now,
                )
            )
            .all()
        )

        updated = 0
        for user in expired_users:
            user.subscription_tier = SubscriptionTier.free
            user.subscription_expires_at = None
            updated += 1

        db.commit()
        logger.info("update_subscription_status_done", updated=updated)
        return {"status": "success", "updated": updated, "timestamp": now.isoformat()}
    except Exception as e:
        db.rollback()
        logger.error("update_subscription_status_failed", error=str(e))
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()


@celery_app.task(bind=True, base=DatabaseTask)
def monitor_trading_patterns(self) -> Dict[str, Any]:
    """Monitor recent trades for behavioral patterns and send alerts."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        # Find active users with recent trades (last 24 hours)
        cutoff_time = now - timedelta(hours=24)

        # Query users who have traded recently
        recent_trades_query = (
            select(Journal.user_id)
            .where(Journal.created_at >= cutoff_time)
            .distinct()
        )
        result = db.execute(recent_trades_query)
        active_user_ids = [row[0] for row in result.fetchall()]

        patterns_detected = 0
        alerts_sent = 0

        for user_id in active_user_ids:
            try:
                # Get recent trades for this user
                journals = (
                    db.query(Journal)
                    .filter(
                        and_(
                            Journal.user_id == user_id,
                            Journal.created_at >= cutoff_time,
                        )
                    )
                    .order_by(Journal.created_at.desc())
                    .limit(50)  # Analyze last 50 trades
                    .all()
                )

                if len(journals) < 3:
                    # Need at least 3 trades for meaningful pattern detection
                    continue

                # Run ML analysis
                ml_analytics = MLAnalytics()
                patterns = ml_analytics.detect_patterns(journals)

                # Send alerts for detected patterns
                for pattern in patterns:
                    patterns_detected += 1

                    # Only send alert for high-confidence patterns
                    if pattern.confidence >= 0.7:
                        try:
                            # Prepare alert data
                            pattern_type = pattern.pattern_type.value
                            description = pattern.description or f"Detected {pattern_type} pattern"
                            confidence = pattern.confidence
                            recommendations = pattern.recommendations or []

                            # Send pattern alert asynchronously
                            send_pattern_alert_task.delay(
                                user_id=str(user_id),
                                pattern_type=pattern_type,
                                description=description,
                                confidence=confidence,
                                recommendations=recommendations,
                            )
                            alerts_sent += 1

                            logger.info(
                                "pattern_alert_queued",
                                user_id=str(user_id),
                                pattern=pattern_type,
                                confidence=confidence,
                            )
                        except Exception as alert_error:
                            logger.error(
                                "failed_to_send_pattern_alert",
                                user_id=str(user_id),
                                error=str(alert_error),
                            )

            except Exception as user_error:
                logger.error(
                    "pattern_detection_failed_for_user",
                    user_id=str(user_id),
                    error=str(user_error),
                )
                continue

        logger.info(
            "monitor_trading_patterns_done",
            users_checked=len(active_user_ids),
            patterns_detected=patterns_detected,
            alerts_sent=alerts_sent,
        )
        return {
            "status": "success",
            "users_checked": len(active_user_ids),
            "patterns_detected": patterns_detected,
            "alerts_sent": alerts_sent,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error("monitor_trading_patterns_failed", error=str(e), exc_info=True)
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()


@celery_app.task(bind=True, base=DatabaseTask)
def monitor_risk_alerts(self) -> Dict[str, Any]:
    """Monitor for risk conditions and send alerts."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        # Find users with recent trades in the last hour
        cutoff_time = now - timedelta(hours=1)

        recent_trades_query = (
            select(Journal.user_id)
            .where(Journal.created_at >= cutoff_time)
            .distinct()
        )
        result = db.execute(recent_trades_query)
        active_user_ids = [row[0] for row in result.fetchall()]

        alerts_sent = 0

        for user_id in active_user_ids:
            try:
                # Get today's trades
                today_start = datetime.combine(now.date(), datetime.min.time())
                journals_today = (
                    db.query(Journal)
                    .filter(
                        and_(
                            Journal.user_id == user_id,
                            Journal.created_at >= today_start,
                        )
                    )
                    .all()
                )

                if not journals_today:
                    continue

                # Calculate total P&L for today
                total_pnl = sum(
                    float(j.profit_loss) for j in journals_today if j.profit_loss
                )

                # Check for excessive losses (more than 5% of account)
                # Note: This is simplified - in production you'd get actual account balance
                if total_pnl < -1000:  # Example threshold
                    send_risk_alert_task.delay(
                        user_id=str(user_id),
                        risk_level="HIGH",
                        message=f"Daily loss limit approaching: ${total_pnl:.2f}",
                        action_required="Consider stopping trading for today",
                    )
                    alerts_sent += 1

                # Check for overtrading (more than 20 trades in a day)
                if len(journals_today) > 20:
                    send_risk_alert_task.delay(
                        user_id=str(user_id),
                        risk_level="MEDIUM",
                        message=f"Overtrading detected: {len(journals_today)} trades today",
                        action_required="Take a break and review your trading plan",
                    )
                    alerts_sent += 1

            except Exception as user_error:
                logger.error(
                    "risk_monitoring_failed_for_user",
                    user_id=str(user_id),
                    error=str(user_error),
                )
                continue

        logger.info(
            "monitor_risk_alerts_done",
            users_checked=len(active_user_ids),
            alerts_sent=alerts_sent,
        )
        return {
            "status": "success",
            "users_checked": len(active_user_ids),
            "alerts_sent": alerts_sent,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        db.rollback()
        logger.error("monitor_risk_alerts_failed", error=str(e), exc_info=True)
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()


@celery_app.task(bind=True, base=DatabaseTask)
def sync_exchange_trades(self) -> Dict[str, Any]:
    """Sync exchange trades into raw storage and journals."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        service = TradeSyncService(db)
        result = service.sync_all_connections()
        logger.info("sync_exchange_trades_done", result=result)
        return {
            "status": "success",
            "result": result,
            "timestamp": now.isoformat(),
        }
    except Exception as e:
        db.rollback()
        logger.error("sync_exchange_trades_failed", error=str(e), exc_info=True)
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()
