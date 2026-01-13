"""Anthropic Claude LLM provider implementation."""

from typing import AsyncIterator, List, Optional

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import get_settings
from core.exceptions import LLMProviderError
from core.logging import get_logger

from .base import LLMConfig, LLMProvider, Message

settings = get_settings()
logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Anthropic provider."""
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self.client = AsyncAnthropic(api_key=self.api_key)

    def _format_message(self, msg: Message) -> dict:
        """Format a single message for Anthropic API."""
        if msg.is_multimodal():
            return msg.to_anthropic_format()
        else:
            return {"role": msg.role, "content": msg.content}

    def _prepare_messages(self, messages: List[Message]) -> tuple:
        """Separate system message and format other messages."""
        system_message = None
        chat_messages = []

        for msg in messages:
            if msg.role == "system":
                # System messages are always text-only
                system_message = (
                    msg.get_text_content() if msg.is_multimodal() else msg.content
                )
            else:
                chat_messages.append(self._format_message(msg))

        return system_message, chat_messages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def chat(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> str:
        """Send chat request to Anthropic."""
        try:
            system_message, chat_messages = self._prepare_messages(messages)

            response = await self.client.messages.create(
                model=config.model,
                system=system_message,
                messages=chat_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
            )

            content = response.content[0].text
            if not content:
                raise LLMProviderError("Anthropic", "Empty response")

            # Log token usage
            logger.info(
                "anthropic_chat_completed",
                model=config.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            return content

        except Exception as e:
            logger.error("Anthropic chat failed", error=str(e))
            raise LLMProviderError("Anthropic", str(e))

    async def chat_stream(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        """Stream chat response from Anthropic."""
        try:
            system_message, chat_messages = self._prepare_messages(messages)

            async with self.client.messages.stream(
                model=config.model,
                system=system_message,
                messages=chat_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            logger.error("Anthropic stream failed", error=str(e))
            raise LLMProviderError("Anthropic", str(e))

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings.

        Note: Anthropic doesn't provide embedding models,
        so this would need to use a different provider.
        """
        raise NotImplementedError("Anthropic doesn't provide embedding models")

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens for Claude models."""
        # Rough approximation - Claude uses a similar tokenizer to GPT
        # In production, you'd want to use the actual Claude tokenizer
        return len(text.split()) * 1.3  # Rough approximation
