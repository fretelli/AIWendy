"""Notification service for sending push notifications, emails, and SMS."""

import json
from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.notification.models import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    DeviceToken,
)
from domain.user.models import User
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class NotificationService:
    """Service for managing and sending notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.PUSH,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create a notification record."""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            channel=channel,
            priority=priority,
            data=data,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def send_notification(
        self,
        user_id: UUID,
        type: NotificationType,
        title: str,
        body: str,
        channel: NotificationChannel = NotificationChannel.PUSH,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """Create and send a notification."""
        # Check user preferences
        user = await self.db.get(User, user_id)
        if not user or not self._should_send(user, channel):
            logger.info("notification_skipped", user_id=str(user_id), channel=channel)
            return None

        # Create notification record
        notification = await self.create_notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            channel=channel,
            priority=priority,
            data=data,
        )

        # Send via appropriate channel
        try:
            if channel == NotificationChannel.PUSH:
                await self._send_push(notification)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif channel == NotificationChannel.SMS:
                await self._send_sms(notification)

            notification.is_sent = True
            notification.sent_at = datetime.utcnow()
        except Exception as e:
            logger.error(
                "notification_send_failed",
                notification_id=str(notification.id),
                error=str(e),
            )
            notification.error_message = str(e)

        await self.db.commit()
        return notification

    async def send_pattern_alert(
        self,
        user_id: UUID,
        pattern_type: str,
        description: str,
        confidence: float,
        recommendations: List[str],
    ):
        """Send alert when a trading pattern is detected."""
        title = f"⚠️ Pattern Detected: {pattern_type}"
        body = f"{description}\n\nConfidence: {confidence:.0%}"

        await self.send_notification(
            user_id=user_id,
            type=NotificationType.PATTERN_DETECTED,
            title=title,
            body=body,
            priority=NotificationPriority.HIGH,
            data={
                "pattern_type": pattern_type,
                "confidence": confidence,
                "recommendations": recommendations,
            },
        )

    async def send_risk_alert(
        self,
        user_id: UUID,
        risk_level: str,
        message: str,
        action_required: Optional[str] = None,
    ):
        """Send risk alert notification."""
        title = f"🚨 Risk Alert: {risk_level}"
        body = message
        if action_required:
            body += f"\n\nAction: {action_required}"

        await self.send_notification(
            user_id=user_id,
            type=NotificationType.RISK_ALERT,
            title=title,
            body=body,
            priority=NotificationPriority.URGENT,
            data={"risk_level": risk_level, "action_required": action_required},
        )

    async def send_daily_summary(
        self,
        user_id: UUID,
        stats: Dict[str, Any],
    ):
        """Send daily trading summary."""
        title = "📊 Daily Trading Summary"
        body = (
            f"Trades: {stats.get('total_trades', 0)}\n"
            f"P&L: ${stats.get('total_pnl', 0):.2f}\n"
            f"Win Rate: {stats.get('win_rate', 0):.1%}"
        )

        await self.send_notification(
            user_id=user_id,
            type=NotificationType.DAILY_SUMMARY,
            title=title,
            body=body,
            priority=NotificationPriority.LOW,
            data=stats,
        )

    async def mark_as_read(self, notification_id: UUID) -> bool:
        """Mark notification as read."""
        notification = await self.db.get(Notification, notification_id)
        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get user notifications."""
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(Notification.is_read == False)

        query = query.order_by(Notification.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def register_device_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
        device_name: Optional[str] = None,
    ) -> DeviceToken:
        """Register a device token for push notifications."""
        # Check if token already exists
        query = select(DeviceToken).where(DeviceToken.token == token)
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.is_active = True
            existing.last_used_at = datetime.utcnow()
            await self.db.commit()
            return existing

        # Create new token
        device_token = DeviceToken(
            user_id=user_id,
            token=token,
            platform=platform,
            device_name=device_name,
            last_used_at=datetime.utcnow(),
        )
        self.db.add(device_token)
        await self.db.commit()
        await self.db.refresh(device_token)
        return device_token

    async def unregister_device_token(self, token: str) -> bool:
        """Unregister a device token."""
        query = select(DeviceToken).where(DeviceToken.token == token)
        result = await self.db.execute(query)
        device_token = result.scalar_one_or_none()

        if not device_token:
            return False

        device_token.is_active = False
        await self.db.commit()
        return True

    def _should_send(self, user: User, channel: NotificationChannel) -> bool:
        """Check if notification should be sent based on user preferences."""
        prefs = user.notification_preferences or {}

        if channel == NotificationChannel.PUSH:
            return prefs.get("push_notifications", True)
        elif channel == NotificationChannel.EMAIL:
            return prefs.get("email_notifications", True)
        elif channel == NotificationChannel.SMS:
            return prefs.get("sms_alerts", False)

        return True

    async def _send_push(self, notification: Notification):
        """Send push notification via FCM."""
        # Get user's device tokens
        query = select(DeviceToken).where(
            DeviceToken.user_id == notification.user_id,
            DeviceToken.is_active == True,
        )
        result = await self.db.execute(query)
        tokens = list(result.scalars().all())

        if not tokens:
            logger.warning(
                "no_device_tokens",
                user_id=str(notification.user_id),
            )
            return

        # Send to FCM
        fcm_server_key = getattr(settings, "FCM_SERVER_KEY", None)
        if not fcm_server_key:
            logger.warning("fcm_not_configured")
            return

        for token in tokens:
            try:
                await self._send_fcm_message(
                    token=token.token,
                    title=notification.title,
                    body=notification.body,
                    data=notification.data or {},
                    priority=notification.priority,
                )
                token.last_used_at = datetime.utcnow()
            except Exception as e:
                logger.error(
                    "fcm_send_failed",
                    token_id=str(token.id),
                    error=str(e),
                )
                # Deactivate invalid tokens
                if "invalid" in str(e).lower() or "not registered" in str(e).lower():
                    token.is_active = False

        await self.db.commit()

    async def _send_fcm_message(
        self,
        token: str,
        title: str,
        body: str,
        data: Dict[str, Any],
        priority: NotificationPriority,
    ):
        """Send message via Firebase Cloud Messaging."""
        fcm_server_key = getattr(settings, "FCM_SERVER_KEY", None)
        if not fcm_server_key:
            raise ValueError("FCM_SERVER_KEY not configured")

        url = "https://fcm.googleapis.com/fcm/send"
        headers = {
            "Authorization": f"Bearer {fcm_server_key}",
            "Content-Type": "application/json",
        }

        # Map priority
        fcm_priority = "high" if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT] else "normal"

        payload = {
            "to": token,
            "priority": fcm_priority,
            "notification": {
                "title": title,
                "body": body,
                "sound": "default",
            },
            "data": data,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            response.raise_for_status()

            result = response.json()
            if result.get("failure", 0) > 0:
                error = result.get("results", [{}])[0].get("error", "Unknown error")
                raise Exception(f"FCM error: {error}")

    async def _send_email(self, notification: Notification):
        """Send email notification."""
        # TODO: Implement email sending via SMTP or email service
        logger.info("email_notification", notification_id=str(notification.id))
        pass

    async def _send_sms(self, notification: Notification):
        """Send SMS notification."""
        # TODO: Implement SMS sending via Twilio or similar
        logger.info("sms_notification", notification_id=str(notification.id))
        pass
