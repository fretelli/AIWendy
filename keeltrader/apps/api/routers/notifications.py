"""Notification API routes."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from domain.user.models import User
from domain.notification.models import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


# Request/Response models
class DeviceTokenRequest(BaseModel):
    token: str
    platform: str  # ios, android, web
    device_name: Optional[str] = None


class DeviceTokenResponse(BaseModel):
    id: UUID
    platform: str
    device_name: Optional[str]
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    channel: str
    priority: str
    is_read: bool
    is_sent: bool
    sent_at: Optional[str]
    read_at: Optional[str]
    created_at: str
    data: Optional[dict]

    class Config:
        from_attributes = True


class SendNotificationRequest(BaseModel):
    type: NotificationType
    title: str
    body: str
    channel: NotificationChannel = NotificationChannel.PUSH
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: Optional[dict] = None


@router.post("/device-tokens", response_model=DeviceTokenResponse)
async def register_device_token(
    request: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a device token for push notifications."""
    service = NotificationService(db)
    token = await service.register_device_token(
        user_id=current_user.id,
        token=request.token,
        platform=request.platform,
        device_name=request.device_name,
    )
    return DeviceTokenResponse(
        id=token.id,
        platform=token.platform,
        device_name=token.device_name,
        is_active=token.is_active,
        created_at=token.created_at.isoformat(),
    )


@router.delete("/device-tokens/{token}")
async def unregister_device_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unregister a device token."""
    service = NotificationService(db)
    success = await service.unregister_device_token(token)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found",
        )
    return {"message": "Device token unregistered successfully"}


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user notifications."""
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )

    return [
        NotificationResponse(
            id=n.id,
            type=n.type.value,
            title=n.title,
            body=n.body,
            channel=n.channel.value,
            priority=n.priority.value,
            is_read=n.is_read,
            is_sent=n.is_sent,
            sent_at=n.sent_at.isoformat() if n.sent_at else None,
            read_at=n.read_at.isoformat() if n.read_at else None,
            created_at=n.created_at.isoformat(),
            data=n.data,
        )
        for n in notifications
    ]


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    success = await service.mark_as_read(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return {"message": "Notification marked as read"}


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    request: SendNotificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a notification (admin/testing endpoint)."""
    service = NotificationService(db)
    notification = await service.send_notification(
        user_id=current_user.id,
        type=request.type,
        title=request.title,
        body=request.body,
        channel=request.channel,
        priority=request.priority,
        data=request.data,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notification not sent (user preferences or configuration issue)",
        )

    return NotificationResponse(
        id=notification.id,
        type=notification.type.value,
        title=notification.title,
        body=notification.body,
        channel=notification.channel.value,
        priority=notification.priority.value,
        is_read=notification.is_read,
        is_sent=notification.is_sent,
        sent_at=notification.sent_at.isoformat() if notification.sent_at else None,
        read_at=notification.read_at.isoformat() if notification.read_at else None,
        created_at=notification.created_at.isoformat(),
        data=notification.data,
    )
