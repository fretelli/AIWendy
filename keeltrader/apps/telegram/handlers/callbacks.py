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
    user_id = str(callback.from_user.id)

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

    await callback.answer("✅ 订单已确认")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>已确认</b> — 正在执行..."
    )
    logger.info("Order %s confirmed by user %s", confirmation_id, user_id)


@router.callback_query(F.data.startswith("reject_order:"))
async def on_reject_order(callback: CallbackQuery) -> None:
    """User rejected a trade order — emit order.rejected event."""
    confirmation_id = callback.data.split(":", 1)[1]
    user_id = str(callback.from_user.id)

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

    await callback.answer("❌ 订单已拒绝")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>已拒绝</b>"
    )
    logger.info("Order %s rejected by user %s", confirmation_id, user_id)


# Legacy confirm/reject without ID (backward compat)
@router.callback_query(F.data == "confirm_order")
async def on_confirm_order_legacy(callback: CallbackQuery) -> None:
    await callback.answer("✅ 订单已确认")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>已确认</b> — 正在执行..."
    )


@router.callback_query(F.data == "reject_order")
async def on_reject_order_legacy(callback: CallbackQuery) -> None:
    await callback.answer("❌ 订单已拒绝")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>已拒绝</b>"
    )


# --- Guardian alert callbacks ---

@router.callback_query(F.data == "pause_trading")
async def on_pause_trading(callback: CallbackQuery) -> None:
    """User chose to pause trading — emit trading.blocked event."""
    user_id = str(callback.from_user.id)

    await _emit_event("trading.blocked", user_id, {
        "duration_minutes": 30,
        "reason": "User requested pause",
        "source": "telegram",
    })

    await callback.answer("⏸ 交易已暂停 30 分钟")
    await callback.message.edit_text(
        callback.message.text + "\n\n⏸ <b>交易已暂停 30 分钟</b>"
    )
    logger.info("Trading paused by user %s", user_id)


@router.callback_query(F.data == "talk_to_coach")
async def on_talk_to_coach(callback: CallbackQuery) -> None:
    """User wants to chat with Psychology Coach."""
    user_id = str(callback.from_user.id)

    await _emit_event("user.message", user_id, {
        "text": "我需要和教练聊聊交易心理",
        "target_agent": "psychology",
    })

    await callback.answer()
    await callback.message.answer(
        "🧠 <b>Psychology Coach</b>\n\n"
        "我是你的交易心理教练。说说你现在的感受？\n\n"
        "<i>直接发送消息即可开始对话。</i>"
    )


# --- Analysis/detail callbacks ---

@router.callback_query(F.data == "view_details")
async def on_view_details(callback: CallbackQuery) -> None:
    """User wants to see detailed analysis."""
    await callback.answer()
    await callback.message.answer(
        "📊 <b>详细分析</b>\n\n"
        "<i>使用 /ask 命令查看详细分析。</i>\n"
        "例如: /ask BTC 多时间框架分析"
    )


# --- Ghost trading callbacks ---

@router.callback_query(F.data == "agent:ghost")
async def on_ghost_status(callback: CallbackQuery) -> None:
    """Show ghost trading portfolio."""
    from ..renderer import render_ghost_portfolio

    user_id = str(callback.from_user.id)

    r = await _get_redis()
    try:
        from ...execution.ghost import GhostTradingService
        ghost = GhostTradingService(r)
        summary = await ghost.portfolio_summary(user_id)
        text = render_ghost_portfolio(summary)
    except Exception as e:
        text = f"👻 <b>Ghost Trading</b>\n\n暂无数据\n\n<i>{e}</i>"
    finally:
        await r.aclose()

    await callback.answer()
    await callback.message.answer(text)


# --- Generic callbacks ---

@router.callback_query(F.data.startswith("agent:"))
async def on_agent_action(callback: CallbackQuery) -> None:
    """Generic agent action callback."""
    action = callback.data.replace("agent:", "")
    await callback.answer(f"执行: {action}")
    logger.info("Agent action %s by user %s", action, callback.from_user.id)
