"""Telegram inline keyboard callback handlers — with Redis event bus integration."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from uuid import uuid4

import redis.asyncio as aioredis
from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..i18n import t

logger = logging.getLogger(__name__)
router = Router(name="callbacks")


async def _get_redis() -> aioredis.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/3")
    return aioredis.from_url(url)


async def _emit_event(event_type: str, user_id: str, payload: dict) -> None:
    """Emit an event to the Redis Streams event bus."""
    r = await _get_redis()
    try:
        event_id = str(uuid4())
        await r.xadd("keeltrader:events", {
            "id": event_id,
            "type": event_type,
            "source": "telegram",
            "user_id": user_id,
            "agent_id": "",
            "payload": json.dumps(payload),
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": str(uuid4()),
            "causation_id": "",
        }, maxlen=10000)
    finally:
        await r.aclose()


# --- Order confirmation callbacks ---

@router.callback_query(F.data.startswith("confirm_order:"))
async def on_confirm_order(callback: CallbackQuery) -> None:
    """User confirmed a trade order — emit order.approved event."""
    confirmation_id = callback.data.split(":", 1)[1]
    uid = callback.from_user.id
    user_id = str(uid)

    # Update confirmation status in Redis
    r = await _get_redis()
    try:
        redis_key = f"keeltrader:confirmation:{confirmation_id}"
        await r.hset(redis_key, mapping={
            "status": "approved",
            "responded_at": datetime.utcnow().isoformat(),
        })
    finally:
        await r.aclose()

    await _emit_event("order.approved", user_id, {
        "confirmation_id": confirmation_id,
        "action": "approved",
    })

    await callback.answer(t("cb.order_confirmed", uid))
    await callback.message.edit_text(
        callback.message.text + t("cb.order_confirmed_text", uid)
    )
    logger.info("Order %s confirmed by user %s", confirmation_id, user_id)


@router.callback_query(F.data.startswith("reject_order:"))
async def on_reject_order(callback: CallbackQuery) -> None:
    """User rejected a trade order — emit order.rejected event."""
    confirmation_id = callback.data.split(":", 1)[1]
    uid = callback.from_user.id
    user_id = str(uid)

    r = await _get_redis()
    try:
        redis_key = f"keeltrader:confirmation:{confirmation_id}"
        await r.hset(redis_key, mapping={
            "status": "rejected",
            "responded_at": datetime.utcnow().isoformat(),
        })
    finally:
        await r.aclose()

    await _emit_event("order.rejected", user_id, {
        "confirmation_id": confirmation_id,
        "action": "rejected",
    })

    await callback.answer(t("cb.order_rejected", uid))
    await callback.message.edit_text(
        callback.message.text + t("cb.order_rejected_text", uid)
    )
    logger.info("Order %s rejected by user %s", confirmation_id, user_id)


# Legacy confirm/reject without ID (backward compat)
@router.callback_query(F.data == "confirm_order")
async def on_confirm_order_legacy(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    await callback.answer(t("cb.order_confirmed", uid))
    await callback.message.edit_text(
        callback.message.text + t("cb.order_confirmed_text", uid)
    )


@router.callback_query(F.data == "reject_order")
async def on_reject_order_legacy(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    await callback.answer(t("cb.order_rejected", uid))
    await callback.message.edit_text(
        callback.message.text + t("cb.order_rejected_text", uid)
    )


# --- Guardian alert callbacks ---

@router.callback_query(F.data == "pause_trading")
async def on_pause_trading(callback: CallbackQuery) -> None:
    """User chose to pause trading — emit trading.blocked event."""
    uid = callback.from_user.id
    user_id = str(uid)

    await _emit_event("trading.blocked", user_id, {
        "duration_minutes": 30,
        "reason": "User requested pause",
        "source": "telegram",
    })

    await callback.answer(t("cb.trading_paused", uid))
    await callback.message.edit_text(
        callback.message.text + t("cb.trading_paused_text", uid)
    )
    logger.info("Trading paused by user %s", user_id)


@router.callback_query(F.data == "talk_to_coach")
async def on_talk_to_coach(callback: CallbackQuery) -> None:
    """User wants to chat with Psychology Coach."""
    uid = callback.from_user.id
    user_id = str(uid)

    await _emit_event("user.message", user_id, {
        "text": t("cb.coach_event_text", uid),
        "target_agent": "psychology",
    })

    await callback.answer()
    await callback.message.answer(t("cb.coach_intro", uid))


# --- Analysis/detail callbacks ---

@router.callback_query(F.data == "view_details")
async def on_view_details(callback: CallbackQuery) -> None:
    """User wants to see detailed analysis."""
    uid = callback.from_user.id
    await callback.answer()
    await callback.message.answer(t("cb.view_details", uid))


# --- Ghost trading callbacks ---

@router.callback_query(F.data == "agent:ghost")
async def on_ghost_status(callback: CallbackQuery) -> None:
    """Show ghost trading portfolio."""
    from ..renderer import render_ghost_portfolio

    uid = callback.from_user.id
    user_id = str(uid)

    r = await _get_redis()
    try:
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(user_id)
        text = render_ghost_portfolio(summary, uid)
    except Exception as e:
        text = f"{t('cb.ghost_no_data', uid)}\n\n<i>{e}</i>"
    finally:
        await r.aclose()

    await callback.answer()
    await callback.message.answer(text)


# --- Generic callbacks ---

@router.callback_query(F.data.startswith("agent:"))
async def on_agent_action(callback: CallbackQuery) -> None:
    """Generic agent action callback."""
    uid = callback.from_user.id
    action = callback.data.replace("agent:", "")
    await callback.answer(t("cb.action_exec", uid, action=action))
    logger.info("Agent action %s by user %s", action, uid)
