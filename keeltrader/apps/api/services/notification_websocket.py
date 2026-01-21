"""WebSocket service for real-time notification streaming."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class NotificationWebSocketService:
    """Service for managing WebSocket connections for real-time notifications."""

    def __init__(self):
        # Track active connections by user_id
        self.user_connections: Dict[str, Set[WebSocket]] = {}

        # Track all active connections
        self.active_connections: Set[WebSocket] = set()

        logger.info("Notification WebSocket service initialized")

    async def connect(self, websocket: WebSocket, user_id: UUID):
        """Connect a client and subscribe to user notifications."""
        user_id_str = str(user_id)

        # Add to user subscriptions
        if user_id_str not in self.user_connections:
            self.user_connections[user_id_str] = set()
        self.user_connections[user_id_str].add(websocket)

        # Add to active connections
        self.active_connections.add(websocket)

        logger.info(f"Client connected for user {user_id_str}")

        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Successfully connected to notification stream",
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def disconnect(self, websocket: WebSocket):
        """Disconnect a client."""
        # Remove from all user subscriptions
        for user_id in list(self.user_connections.keys()):
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)

                # Clean up empty sets
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        logger.info("Client disconnected")

    async def send_notification_to_user(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str,
        priority: str,
        data: Optional[Dict[str, Any]] = None,
        notification_id: Optional[UUID] = None,
    ):
        """Send a notification to all connected clients for a user."""
        user_id_str = str(user_id)

        if user_id_str not in self.user_connections:
            logger.debug(f"No active connections for user {user_id_str}")
            return 0

        # Format notification message
        message = {
            "type": "notification",
            "notification_id": str(notification_id) if notification_id else None,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "priority": priority,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Send to all connected clients for this user
        disconnected = set()
        sent_count = 0

        for client in self.user_connections[user_id_str]:
            try:
                await client.send_json(message)
                sent_count += 1
                logger.debug(f"Notification sent to client for user {user_id_str}")
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            await self.disconnect(client)

        logger.info(
            f"Notification sent to {sent_count} clients for user {user_id_str}",
            extra={
                "user_id": user_id_str,
                "notification_type": notification_type,
                "clients": sent_count,
            },
        )

        return sent_count

    async def send_pattern_alert(
        self,
        user_id: UUID,
        pattern_type: str,
        description: str,
        confidence: float,
        recommendations: list,
    ):
        """Send pattern alert notification via WebSocket."""
        await self.send_notification_to_user(
            user_id=user_id,
            notification_type="PATTERN_DETECTED",
            title=f"⚠️ Pattern Detected: {pattern_type}",
            body=f"{description}\n\nConfidence: {confidence:.0%}",
            priority="HIGH",
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
        """Send risk alert notification via WebSocket."""
        body = message
        if action_required:
            body += f"\n\nAction: {action_required}"

        await self.send_notification_to_user(
            user_id=user_id,
            notification_type="RISK_ALERT",
            title=f"🚨 Risk Alert: {risk_level}",
            body=body,
            priority="URGENT",
            data={
                "risk_level": risk_level,
                "action_required": action_required,
            },
        )

    async def send_daily_summary(
        self,
        user_id: UUID,
        stats: Dict[str, Any],
    ):
        """Send daily summary notification via WebSocket."""
        body = (
            f"Trades: {stats.get('total_trades', 0)}\n"
            f"P&L: ${stats.get('total_pnl', 0):.2f}\n"
            f"Win Rate: {stats.get('win_rate', 0):.1%}"
        )

        await self.send_notification_to_user(
            user_id=user_id,
            notification_type="DAILY_SUMMARY",
            title="📊 Daily Trading Summary",
            body=body,
            priority="LOW",
            data=stats,
        )

    async def broadcast_system_message(self, message: str, priority: str = "NORMAL"):
        """Broadcast a system message to all connected clients."""
        broadcast_message = {
            "type": "system_message",
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
        }

        disconnected = set()
        sent_count = 0

        for client in list(self.active_connections):
            try:
                await client.send_json(broadcast_message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(client)

        # Clean up disconnected clients
        for client in disconnected:
            await self.disconnect(client)

        logger.info(f"System message broadcast to {sent_count} clients")
        return sent_count

    async def send_heartbeat(self, websocket: WebSocket):
        """Send heartbeat to keep connection alive."""
        try:
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            await self.disconnect(websocket)

    async def get_connected_users_count(self) -> int:
        """Get count of users with active connections."""
        return len(self.user_connections)

    async def get_total_connections_count(self) -> int:
        """Get total count of active connections."""
        return len(self.active_connections)

    async def close(self):
        """Close all connections."""
        for websocket in list(self.active_connections):
            try:
                await websocket.close()
            except Exception:
                pass

        self.active_connections.clear()
        self.user_connections.clear()

        logger.info("Notification WebSocket service closed")


# Global instance
notification_ws_service = NotificationWebSocketService()
