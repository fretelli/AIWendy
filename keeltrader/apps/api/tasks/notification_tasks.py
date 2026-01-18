"""Celery tasks for sending notifications."""

import asyncio
from uuid import UUID
from typing import Dict, Any, List, Optional

from celery import shared_task
import structlog

from keeltrader.apps.api.core.database import get_db_context
from keeltrader.apps.api.services.notification_service import NotificationService
from keeltrader.apps.api.services.notification_websocket import notification_ws_service
from keeltrader.apps.api.domain.notification.models import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)

logger = structlog.get_logger()


@shared_task(name="send_notification_task")
def send_notification_task(
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    channel: str = "push",
    priority: str = "normal",
    data: Optional[Dict[str, Any]] = None,
):
    """Celery task to send notification asynchronously."""
    try:
        async def _send():
            async with get_db_context() as db:
                service = NotificationService(db)
                await service.send_notification(
                    user_id=UUID(user_id),
                    type=NotificationType(notification_type),
                    title=title,
                    body=body,
                    channel=NotificationChannel(channel),
                    priority=NotificationPriority(priority),
                    data=data,
                )

        import asyncio
        asyncio.run(_send())

        logger.info(
            "notification_sent",
            user_id=user_id,
            type=notification_type,
        )
    except Exception as e:
        logger.error(
            "notification_task_failed",
            user_id=user_id,
            error=str(e),
        )
        raise


@shared_task(name="send_pattern_alert_task")
def send_pattern_alert_task(
    user_id: str,
    pattern_type: str,
    description: str,
    confidence: float,
    recommendations: List[str],
):
    """Send pattern detection alert."""
    try:
        async def _send():
            # Send via database notification service
            async with get_db_context() as db:
                service = NotificationService(db)
                await service.send_pattern_alert(
                    user_id=UUID(user_id),
                    pattern_type=pattern_type,
                    description=description,
                    confidence=confidence,
                    recommendations=recommendations,
                )

            # Send via WebSocket for real-time push
            await notification_ws_service.send_pattern_alert(
                user_id=UUID(user_id),
                pattern_type=pattern_type,
                description=description,
                confidence=confidence,
                recommendations=recommendations,
            )

        asyncio.run(_send())

        logger.info(
            "pattern_alert_sent",
            user_id=user_id,
            pattern_type=pattern_type,
        )
    except Exception as e:
        logger.error(
            "pattern_alert_task_failed",
            user_id=user_id,
            error=str(e),
        )
        raise


@shared_task(name="send_risk_alert_task")
def send_risk_alert_task(
    user_id: str,
    risk_level: str,
    message: str,
    action_required: Optional[str] = None,
):
    """Send risk alert notification."""
    try:
        async def _send():
            # Send via database notification service
            async with get_db_context() as db:
                service = NotificationService(db)
                await service.send_risk_alert(
                    user_id=UUID(user_id),
                    risk_level=risk_level,
                    message=message,
                    action_required=action_required,
                )

            # Send via WebSocket for real-time push
            await notification_ws_service.send_risk_alert(
                user_id=UUID(user_id),
                risk_level=risk_level,
                message=message,
                action_required=action_required,
            )

        asyncio.run(_send())

        logger.info(
            "risk_alert_sent",
            user_id=user_id,
            risk_level=risk_level,
        )
    except Exception as e:
        logger.error(
            "risk_alert_task_failed",
            user_id=user_id,
            error=str(e),
        )
        raise


@shared_task(name="send_daily_summary_task")
def send_daily_summary_task(user_id: str, stats: Dict[str, Any]):
    """Send daily trading summary."""
    try:
        async def _send():
            # Send via database notification service
            async with get_db_context() as db:
                service = NotificationService(db)
                await service.send_daily_summary(
                    user_id=UUID(user_id),
                    stats=stats,
                )

            # Send via WebSocket for real-time push
            await notification_ws_service.send_daily_summary(
                user_id=UUID(user_id),
                stats=stats,
            )

        asyncio.run(_send())

        logger.info(
            "daily_summary_sent",
            user_id=user_id,
        )
    except Exception as e:
        logger.error(
            "daily_summary_task_failed",
            user_id=user_id,
            error=str(e),
        )
        raise
