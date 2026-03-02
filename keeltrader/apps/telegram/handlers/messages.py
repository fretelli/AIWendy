"""Telegram natural language message handler — routes to Orchestrator."""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import Message

from ..i18n import t

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
    uid = message.from_user.id
    await message.answer(t("msg.processing", uid))
