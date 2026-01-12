"""OpenAI LLM provider implementation."""

from typing import AsyncIterator, List, Optional

import tiktoken
from config import get_settings
from core.exceptions import LLMProviderError
from core.logging import get_logger
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import LLMConfig, LLMProvider, Message

settings = get_settings()
logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider."""
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(api_key=self.api_key)

    def _format_messages(self, messages: List[Message]) -> List[dict]:
        """Format messages for OpenAI API, supporting multimodal content."""
        formatted = []
        for m in messages:
            if m.is_multimodal():
                formatted.append(m.to_openai_format())
            else:
                formatted.append({"role": m.role, "content": m.content})
        return formatted

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def chat(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> str:
        """Send chat request to OpenAI."""
        try:
            formatted_messages = self._format_messages(messages)

            response = await self.client.chat.completions.create(
                model=config.model,
                messages=formatted_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stream=False,
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMProviderError("OpenAI", "Empty response")

            # Log token usage
            if response.usage:
                logger.info(
                    "openai_chat_completed",
                    model=config.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            return content

        except Exception as e:
            logger.error("OpenAI chat failed", error=str(e))
            raise LLMProviderError("OpenAI", str(e))

    async def chat_stream(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        """Stream chat response from OpenAI."""
        try:
            formatted_messages = self._format_messages(messages)

            stream = await self.client.chat.completions.create(
                model=config.model,
                messages=formatted_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
                frequency_penalty=config.frequency_penalty,
                presence_penalty=config.presence_penalty,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("OpenAI stream failed", error=str(e))
            raise LLMProviderError("OpenAI", str(e))

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model=model or "text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding

        except Exception as e:
            logger.error("OpenAI embedding failed", error=str(e))
            raise LLMProviderError("OpenAI", str(e))

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens using tiktoken."""
        try:
            encoding = tiktoken.encoding_for_model(model or "gpt-4o-mini")
            return len(encoding.encode(text))
        except Exception:
            # Fallback to cl100k_base encoding
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
