"""Communication tools — Telegram messaging, user confirmation, agent delegation.

These tools allow agents to communicate with users via Telegram
and delegate tasks to other agents.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# Global references set during bot startup
_bot = None  # aiogram Bot instance
_redis: aioredis.Redis | None = None


def init_communication(bot: Any, redis: aioredis.Redis) -> None:
    """Initialize communication tools with bot and redis instances."""
    global _bot, _redis
    _bot = bot
    _redis = redis


async def send_telegram(
    user_id: int,
    message: str,
    parse_mode: str = "HTML",
    keyboard: list[list[dict]] | None = None,
) -> dict[str, Any]:
    """Send a Telegram message to a user.

    Args:
        user_id: Telegram user ID
        message: Message text (HTML or Markdown)
        parse_mode: Parse mode (HTML or Markdown)
        keyboard: Optional inline keyboard buttons

    Returns:
        Dict with success status and message_id
    """
    if _bot is None:
        return {"success": False, "error": "Bot not initialized"}

    try:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = None
        if keyboard:
            rows = []
            for row in keyboard:
                buttons = [
                    InlineKeyboardButton(
                        text=btn.get("text", ""),
                        callback_data=btn.get("callback_data", ""),
                    )
                    for btn in row
                ]
                rows.append(buttons)
            reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)

        msg = await _bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )
        return {"success": True, "message_id": msg.message_id}
    except Exception as e:
        logger.error("send_telegram failed for user %s: %s", user_id, e)
        return {"success": False, "error": str(e)}


async def request_confirmation(
    user_id: int,
    action_description: str,
    action_data: dict[str, Any],
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Request user confirmation via Telegram inline buttons.

    Sends a confirmation message and waits for the user to approve/reject.

    Args:
        user_id: Telegram user ID
        action_description: Human-readable description of the action
        action_data: Data to store with the confirmation request
        timeout_seconds: How long to wait for response

    Returns:
        Dict with action (approved/rejected/timeout) and details
    """
    if _bot is None or _redis is None:
        return {"action": "error", "error": "Bot or Redis not initialized"}

    confirmation_id = str(uuid4())
    redis_key = f"keeltrader:confirmation:{confirmation_id}"

    # Store confirmation request in Redis
    await _redis.hset(redis_key, mapping={
        "user_id": str(user_id),
        "description": action_description,
        "status": "pending",
    })
    await _redis.expire(redis_key, timeout_seconds + 60)

    # Send confirmation message with buttons
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ 确认执行",
                callback_data=f"confirm_order:{confirmation_id}",
            ),
            InlineKeyboardButton(
                text="❌ 拒绝",
                callback_data=f"reject_order:{confirmation_id}",
            ),
        ]
    ])

    try:
        msg = await _bot.send_message(
            chat_id=user_id,
            text=action_description,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await _redis.hset(redis_key, "message_id", str(msg.message_id))
    except Exception as e:
        logger.error("Failed to send confirmation: %s", e)
        return {"action": "error", "error": str(e)}

    # Poll for response
    elapsed = 0
    poll_interval = 2
    while elapsed < timeout_seconds:
        status = await _redis.hget(redis_key, "status")
        if status and status != "pending":
            return {
                "action": status,  # "approved" or "rejected"
                "confirmation_id": confirmation_id,
            }
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    # Timeout
    await _redis.hset(redis_key, "status", "timeout")
    return {"action": "timeout", "confirmation_id": confirmation_id}


async def delegate_to_agent(
    agent_type: str,
    context: dict[str, Any],
    user_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Delegate a task to another agent via the event bus.

    Used by Orchestrator to route tasks to specialized agents.

    Args:
        agent_type: Target agent type (technical, sentiment, fundamental, guardian, executor)
        context: Context/payload for the delegated task
        user_id: User ID for the task
        correlation_id: Correlation ID for event chain tracking

    Returns:
        Dict with delegation status
    """
    if _redis is None:
        return {"success": False, "error": "Redis not initialized"}

    from ..engine.event_types import Event, EventType

    event = Event(
        type=EventType.AGENT_ANALYSIS if agent_type != "executor" else EventType.ORDER_REQUESTED,
        source=f"delegation:{agent_type}",
        user_id=user_id,
        payload={
            "target_agent": agent_type,
            "context": context,
        },
        correlation_id=correlation_id or str(uuid4()),
    )

    try:
        stream_data = event.to_stream_dict()
        await _redis.xadd("keeltrader:events", stream_data, maxlen=10000)
        return {
            "success": True,
            "event_id": str(event.id),
            "target_agent": agent_type,
        }
    except Exception as e:
        logger.error("delegate_to_agent failed: %s", e)
        return {"success": False, "error": str(e)}
