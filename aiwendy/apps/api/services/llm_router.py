"""Lightweight LLM router wrapper used by services.

This module provides a simplified interface for service-layer callers that
build a single prompt string (e.g., journal analysis) rather than a structured
chat message list.
"""

from __future__ import annotations

from typing import Optional

from config import get_settings
from core.logging import get_logger
from domain.user.models import User
from infrastructure.llm.base import LLMConfig, Message
from infrastructure.llm.router import get_llm_router

settings = get_settings()
logger = get_logger(__name__)


class LLMRouter:
    """Service-layer LLM router with a simple `chat(prompt)` API."""

    def __init__(self, user: Optional[User] = None):
        self._user = user
        self._router = get_llm_router(user=user) if user else get_llm_router()

    async def chat(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        messages: list[Message] = []
        if system:
            messages.append(Message(role="system", content=system))
        messages.append(Message(role="user", content=prompt))

        config = LLMConfig(
            model=model or settings.llm_default_model,
            temperature=(
                settings.llm_temperature if temperature is None else temperature
            ),
            max_tokens=settings.llm_max_tokens if max_tokens is None else max_tokens,
            stream=False,
        )

        preferred_provider = provider or settings.llm_default_provider
        return await self._router.chat_with_fallback(
            messages=messages,
            config=config,
            preferred_provider=preferred_provider,
        )
