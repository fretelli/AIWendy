"""LLM provider router for intelligent routing between providers."""

from enum import Enum
from typing import AsyncIterator, Dict, List, Optional

from config import get_settings
from core.encryption import get_encryption_service
from core.exceptions import LLMProviderError
from core.logging import get_logger

from .anthropic_provider import AnthropicProvider
from .base import LLMConfig, LLMProvider, Message
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

settings = get_settings()
logger = get_logger(__name__)
encryption = get_encryption_service()


class ProviderPriority(Enum):
    """Provider priority for routing."""

    PRIMARY = 1
    FALLBACK = 2
    EMERGENCY = 3


class LLMRouter:
    """Routes LLM requests to appropriate providers with fallback."""

    def __init__(self, user=None):
        """Initialize LLM router with available providers.

        Args:
            user: Optional user object with encrypted API keys
        """
        self.providers: Dict[str, LLMProvider] = {}
        self.user = user
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available LLM providers."""
        # Try user-specific keys first, then fall back to system keys
        openai_key = None
        anthropic_key = None

        # Check for user-specific keys
        if self.user:
            # Decrypt user's OpenAI key if available
            if hasattr(self.user, "openai_api_key") and self.user.openai_api_key:
                decrypted = encryption.decrypt(self.user.openai_api_key)
                if decrypted:
                    openai_key = decrypted
                    logger.info(f"Using user-specific OpenAI key for {self.user.email}")

            # Decrypt user's Anthropic key if available
            if hasattr(self.user, "anthropic_api_key") and self.user.anthropic_api_key:
                decrypted = encryption.decrypt(self.user.anthropic_api_key)
                if decrypted:
                    anthropic_key = decrypted
                    logger.info(
                        f"Using user-specific Anthropic key for {self.user.email}"
                    )

        # Fall back to system keys if user keys not available
        if (
            not openai_key
            and settings.openai_api_key
            and not settings.openai_api_key.startswith("your_")
        ):
            openai_key = settings.openai_api_key
            logger.info("Using system OpenAI key")

        if (
            not anthropic_key
            and settings.anthropic_api_key
            and not settings.anthropic_api_key.startswith("your_")
        ):
            anthropic_key = settings.anthropic_api_key
            logger.info("Using system Anthropic key")

        # Initialize OpenAI provider if key available
        if openai_key:
            try:
                self.providers["openai"] = OpenAIProvider(api_key=openai_key)
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.error("Failed to initialize OpenAI provider", error=str(e))

        # Initialize Anthropic provider if key available
        if anthropic_key:
            try:
                self.providers["anthropic"] = AnthropicProvider(api_key=anthropic_key)
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.error("Failed to initialize Anthropic provider", error=str(e))

        # Initialize Ollama provider (always available for local models)
        try:
            ollama_provider = OllamaProvider()
            import asyncio

            try:
                asyncio.get_running_loop()
                # We're already in an async context; skip the health check.
                self.providers["ollama"] = ollama_provider
                logger.info(
                    "Ollama provider initialized (health check skipped in async context)"
                )
            except RuntimeError:
                # No running loop (e.g., Celery worker). Do a best-effort health check.
                is_healthy = asyncio.run(ollama_provider.check_health())
                if is_healthy:
                    self.providers["ollama"] = ollama_provider
                    logger.info("Ollama provider initialized and healthy")
                else:
                    logger.info("Ollama service not running - provider not initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama provider: {e}")

        # Log if no providers are configured
        if not self.providers:
            logger.warning("No LLM providers configured - no valid API keys available")

    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Get a specific provider by name."""
        return self.providers.get(provider_name)

    async def chat_with_fallback(
        self,
        messages: List[Message],
        config: LLMConfig,
        preferred_provider: Optional[str] = None,
    ) -> str:
        """Send chat request with automatic fallback."""
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)

        last_error = None
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            try:
                logger.info(f"Attempting chat with {provider_name}")
                return await provider.chat(messages, config)

            except Exception as e:
                logger.warning(
                    f"Provider {provider_name} failed",
                    error=str(e),
                )
                last_error = e
                continue

        # All providers failed
        raise LLMProviderError(
            "All providers",
            f"All LLM providers failed. Last error: {last_error}",
        )

    async def chat_stream_with_fallback(
        self,
        messages: List[Message],
        config: LLMConfig,
        preferred_provider: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Stream chat response with automatic fallback."""
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)

        last_error = None
        for provider_name in provider_order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            try:
                logger.info(f"Attempting stream with {provider_name}")
                async for chunk in provider.chat_stream(messages, config):
                    yield chunk
                return  # Success

            except Exception as e:
                logger.warning(
                    f"Provider {provider_name} failed",
                    error=str(e),
                )
                last_error = e
                continue

        # All providers failed
        raise LLMProviderError(
            "All providers",
            f"All LLM providers failed. Last error: {last_error}",
        )

    def _get_provider_order(
        self, preferred_provider: Optional[str] = None
    ) -> List[str]:
        """Get provider order for fallback."""
        order = []

        # Add preferred provider first
        if preferred_provider and preferred_provider in self.providers:
            order.append(preferred_provider)

        # Add other providers
        for name in self.providers.keys():
            if name not in order:
                order.append(name)

        return order

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings using available provider."""
        # Try OpenAI first for embeddings
        if "openai" in self.providers:
            return await self.providers["openai"].embed(text, model)

        # Fall back to Ollama if available
        if "ollama" in self.providers:
            return await self.providers["ollama"].embed(text, model)

        raise LLMProviderError(
            "Embedding",
            "No embedding provider available",
        )


# Global router instance (for system-wide keys only)
_llm_router: Optional[LLMRouter] = None


def get_llm_router(user=None) -> LLMRouter:
    """Get or create LLM router instance.

    Args:
        user: Optional user object with API keys.
              If provided, creates a user-specific router instance.

    Returns:
        LLMRouter instance with appropriate API keys
    """
    global _llm_router

    # If user is provided, create a user-specific router
    if user:
        return LLMRouter(user=user)

    # Otherwise, return the global instance (system keys only)
    if _llm_router is None:
        _llm_router = LLMRouter()
    return _llm_router
