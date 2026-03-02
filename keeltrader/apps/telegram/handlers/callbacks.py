"""Telegram inline keyboard callback handlers."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)
router = Router(name="callbacks")


@router.callback_query(F.data == "confirm_order")
async def on_confirm_order(callback: CallbackQuery) -> None:
    """User confirmed a trade order."""
    await callback.answer("订单已确认")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>已确认</b> — 正在执行..."
    )
    # TODO: Emit order.approved event
    logger.info("Order confirmed by user %s", callback.from_user.id)


@router.callback_query(F.data == "reject_order")
async def on_reject_order(callback: CallbackQuery) -> None:
    """User rejected a trade order."""
    await callback.answer("订单已拒绝")
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>已拒绝</b>"
    )
    # TODO: Emit order.rejected event
    logger.info("Order rejected by user %s", callback.from_user.id)


@router.callback_query(F.data == "pause_trading")
async def on_pause_trading(callback: CallbackQuery) -> None:
    """User chose to pause trading (from Guardian recommendation)."""
    await callback.answer("交易已暂停 30 分钟")
    await callback.message.edit_text(
        callback.message.text + "\n\n⏸ <b>交易已暂停 30 分钟</b>"
    )
    # TODO: Emit trading.blocked event with 30min duration


@router.callback_query(F.data == "talk_to_coach")
async def on_talk_to_coach(callback: CallbackQuery) -> None:
    """User wants to chat with Psychology Coach."""
    await callback.answer()
    await callback.message.answer(
        "🧠 <b>Psychology Coach</b>\n\n"
        "我是你的交易心理教练。说说你现在的感受？"
    )
    # TODO: Start Psychology Coach session


@router.callback_query(F.data == "view_details")
async def on_view_details(callback: CallbackQuery) -> None:
    """User wants to see detailed analysis."""
    await callback.answer()
    await callback.message.answer(
        "📊 <b>详细分析</b>\n\n"
        "<i>正在生成图表...</i>"
    )
    # TODO: Generate and send chart image


@router.callback_query(F.data.startswith("agent:"))
async def on_agent_action(callback: CallbackQuery) -> None:
    """Generic agent action callback."""
    action = callback.data.replace("agent:", "")
    await callback.answer(f"执行: {action}")
    logger.info("Agent action %s by user %s", action, callback.from_user.id)
