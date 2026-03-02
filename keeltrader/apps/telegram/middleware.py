"""Telegram bot middleware — auth, logging, rate limiting."""

from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log all incoming updates."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        text = ""
        if isinstance(event, Message):
            user = event.from_user
            text = (event.text or "")[:50]
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            text = event.data or ""

        if user:
            logger.info(
                "TG update: user=%s (%s) text=%s",
                user.id, user.username or "?", text,
            )

        return await handler(event, data)


class AuthMiddleware(BaseMiddleware):
    """Authenticate Telegram users against KeelTrader accounts.

    For now, uses a simple allowlist from env vars.
    TODO: Proper user binding via /start flow.
    """

    def __init__(self):
        # Allowed Telegram user IDs (comma-separated)
        allowed = os.environ.get("TELEGRAM_ALLOWED_USERS", "")
        self._allowed_ids: set[int] = set()
        if allowed:
            self._allowed_ids = {int(uid.strip()) for uid in allowed.split(",") if uid.strip()}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # If no allowlist configured, allow all (dev mode)
        if not self._allowed_ids:
            return await handler(event, data)

        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if user and user.id not in self._allowed_ids:
            logger.warning("Unauthorized Telegram user: %s (%s)", user.id, user.username)
            if isinstance(event, Message):
                await event.answer("⛔ 未授权。请联系管理员。")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ 未授权", show_alert=True)
            return None

        return await handler(event, data)
