"""Maintenance/background tasks (Celery)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from celery import Task
from core.database import SessionLocal
from core.logging import get_logger
from domain.user.models import SubscriptionTier, User, UserSession
from sqlalchemy import and_
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
