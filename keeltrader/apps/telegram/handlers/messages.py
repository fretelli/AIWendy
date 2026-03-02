"""Telegram natural language message handler — routes to Orchestrator."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router(name="messages")


@router.message()
async def on_message(message: Message) -> None:
    """Handle free-text messages — route to Orchestrator agent."""
    if not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    logger.info("User %s message: %s", message.from_user.id, text[:100])

    # TODO: Route to Orchestrator agent via event bus
    # For now, echo back with placeholder
    await message.answer(
        f"🔄 <b>处理中...</b>\n\n"
        f"正在将你的消息路由到 Orchestrator Agent...\n\n"
        f"<i>Agent Matrix 功能开发中。</i>"
    )
