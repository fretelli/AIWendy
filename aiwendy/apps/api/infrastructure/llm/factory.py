"""Factory for creating LLM providers with support for custom APIs."""

from enum import Enum
from typing import Any, Dict, List, Optional

from config import get_settings
from core.logging import get_logger
from infrastructure.llm.anthropic_provider import AnthropicProvider
from infrastructure.llm.base import LLMProvider
from infrastructure.llm.custom_api_provider import (
    APIFormat,
    AuthType,
    CustomAPIConfig,
    CustomAPIProvider,
    create_custom_provider,
)
from infrastructure.llm.ollama_advanced import AdvancedOllamaProvider
from infrastructure.llm.ollama_provider import OllamaProvider
from infrastructure.llm.openai_provider import OpenAIProvider

logger = get_logger(__name__)
settings = get_settings()


def _clean_str(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_str_list(value: Any) -> Optional[List[str]]:
    if not isinstance(value, list):
        return None
    cleaned: List[str] = []
    seen = set()
    for item in value:
        item_clean = _clean_str(item)
        if not item_clean:
            continue
        if item_clean in seen:
            continue
        seen.add(item_clean)
        cleaned.append(item_clean)
    return cleaned or None


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    OLLAMA_ADVANCED = "ollama_advanced"
    DEEPSEEK = "deepseek"

    # Custom API presets
    AZURE_OPENAI = "azure_openai"
    GROQ = "groq"
    TOGETHER = "together"
    ANYSCALE = "anyscale"
    PERPLEXITY = "perplexity"
    DEEPINFRA = "deepinfra"
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    VLLM = "vllm"
    LOCALAI = "localai"
    ONEAPI = "oneapi"
    API2D = "api2d"
    XINFERENCE = "xinference"
    MOONSHOT = "moonshot"
    ZHIPU = "zhipu"
    BAICHUAN = "baichuan"
    QWEN = "qwen"

    # Generic custom
    CUSTOM = "custom"


class LLMFactory:
    """Factory for creating LLM providers."""

    def __init__(self):
        self.providers_cache: Dict[str, LLMProvider] = {}
        self.custom_configs: Dict[str, CustomAPIConfig] = {}

    def create_provider(
        self,
        provider_type: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> LLMProvider:
        """Create an LLM provider instance.

        Args:
            provider_type: Type of provider (openai, anthropic, custom, etc.)
            api_key: API key for the provider
            model: Default model to use
            base_url: Base URL for custom endpoints
            **kwargs: Additional provider-specific configuration

        Returns:
            LLMProvider instance
        """

        cache_key = f"{provider_type}:{api_key}:{base_url}"

        # Return cached provider if available
        if cache_key in self.providers_cache:
            logger.debug(f"Using cached provider: {provider_type}")
            return self.providers_cache[cache_key]

        # Create new provider
        provider = self._create_provider_instance(
            provider_type, api_key, model, base_url, **kwargs
        )

        # Cache the provider
        self.providers_cache[cache_key] = provider
        logger.info(f"Created new provider: {provider_type}")

        return provider

    def _create_provider_instance(
        self,
        provider_type: str,
        api_key: Optional[str],
        model: Optional[str],
        base_url: Optional[str],
        **kwargs,
    ) -> LLMProvider:
        """Create a new provider instance."""

        # Get API key from settings if not provided
        if not api_key:
            api_key = self._get_default_api_key(provider_type)

        # Standard providers
        if provider_type == ProviderType.OPENAI:
            if base_url:
                # Custom OpenAI-compatible endpoint
                return create_custom_provider(
                    provider_name="custom_openai",
                    api_key=api_key,
                    base_url=base_url,
                    api_format=APIFormat.OPENAI,
                    default_model=model or "gpt-3.5-turbo",
                    **kwargs,
                )
            else:
                return OpenAIProvider(api_key=api_key)

        elif provider_type == ProviderType.ANTHROPIC:
            if base_url:
                # Custom Anthropic-compatible endpoint
                return create_custom_provider(
                    provider_name="custom_anthropic",
                    api_key=api_key,
                    base_url=base_url,
                    api_format=APIFormat.ANTHROPIC,
                    default_model=model or "claude-3-haiku-20240307",
                    **kwargs,
                )
            else:
                return AnthropicProvider(api_key=api_key)

        elif provider_type == ProviderType.OLLAMA:
            return OllamaProvider(base_url=base_url or "http://localhost:11434")

        elif provider_type == ProviderType.OLLAMA_ADVANCED:
            return AdvancedOllamaProvider(base_url=base_url or "http://localhost:11434")

        elif provider_type == ProviderType.DEEPSEEK:
            # DeepSeek uses OpenAI-compatible API format
            config = CustomAPIConfig(
                api_base_url="https://api.deepseek.com",
                api_key=api_key,
                model=model or "deepseek-chat",
                api_format=APIFormat.OPENAI,
                auth_type=AuthType.BEARER,
            )
            return CustomAPIProvider(config)

        # Custom API presets
        elif provider_type in [
            ProviderType.AZURE_OPENAI,
            ProviderType.GROQ,
            ProviderType.TOGETHER,
            ProviderType.ANYSCALE,
            ProviderType.PERPLEXITY,
            ProviderType.DEEPINFRA,
            ProviderType.OPENROUTER,
            ProviderType.HUGGINGFACE,
            ProviderType.VLLM,
            ProviderType.LOCALAI,
            ProviderType.ONEAPI,
            ProviderType.API2D,
            ProviderType.XINFERENCE,
            ProviderType.MOONSHOT,
            ProviderType.ZHIPU,
            ProviderType.BAICHUAN,
            ProviderType.QWEN,
        ]:
            return CustomAPIProvider.from_preset(
                preset_name=provider_type, api_key=api_key or "", base_url=base_url
            )

        # Generic custom provider
        elif provider_type == ProviderType.CUSTOM:
            if not base_url:
                raise ValueError("base_url is required for custom provider")

            # Check if custom config exists
            if provider_type in self.custom_configs:
                config = self.custom_configs[provider_type]
                config.api_key = api_key
                if base_url:
                    config.base_url = base_url
            else:
                # Create new custom config
                config = CustomAPIConfig(
                    name=kwargs.get("name", "custom_api"),
                    base_url=base_url,
                    api_key=api_key,
                    api_format=APIFormat(kwargs.get("api_format", "openai")),
                    auth_type=AuthType(kwargs.get("auth_type", "bearer")),
                    default_model=model or kwargs.get("default_model", "gpt-3.5-turbo"),
                    chat_endpoint=kwargs.get("chat_endpoint", "/v1/chat/completions"),
                    supports_streaming=kwargs.get("supports_streaming", True),
                    supports_functions=kwargs.get("supports_functions", False),
                    supports_vision=kwargs.get("supports_vision", False),
                    supports_embeddings=kwargs.get("supports_embeddings", True),
                    extra_headers=kwargs.get("extra_headers"),
                    extra_body_params=kwargs.get("extra_body_params"),
                )

            return CustomAPIProvider(config)

        else:
            # Try to treat unknown provider as custom preset
            try:
                return CustomAPIProvider.from_preset(
                    preset_name=provider_type, api_key=api_key or "", base_url=base_url
                )
            except ValueError:
                raise ValueError(
                    f"Unknown provider type: {provider_type}. "
                    f"Available: {', '.join([e.value for e in ProviderType])}"
                )

    def register_custom_config(self, name: str, config: CustomAPIConfig):
        """Register a custom API configuration for reuse."""
        self.custom_configs[name] = config
        logger.info(f"Registered custom config: {name}")

    def create_custom_provider_from_dict(
        self, config_dict: Dict[str, Any]
    ) -> CustomAPIProvider:
        """Create custom provider from dictionary configuration."""

        base_url = _clean_str(config_dict.get("base_url"))
        if not base_url:
            raise ValueError("base_url is required for custom provider")

        config = CustomAPIConfig(
            name=config_dict.get("name", "custom"),
            base_url=base_url,
            api_key=config_dict.get("api_key"),
            api_format=APIFormat(config_dict.get("api_format", "openai")),
            auth_type=AuthType(config_dict.get("auth_type", "bearer")),
            auth_header_name=config_dict.get("auth_header_name"),
            default_model=_clean_str(config_dict.get("default_model"))
            or "gpt-3.5-turbo",
            available_models=_clean_str_list(config_dict.get("available_models")),
            chat_endpoint=_clean_str(config_dict.get("chat_endpoint"))
            or "/v1/chat/completions",
            completions_endpoint=_clean_str(config_dict.get("completions_endpoint"))
            or "/v1/completions",
            embeddings_endpoint=_clean_str(config_dict.get("embeddings_endpoint"))
            or "/v1/embeddings",
            models_endpoint=_clean_str(config_dict.get("models_endpoint"))
            or "/v1/models",
            extra_headers=config_dict.get("extra_headers"),
            extra_body_params=config_dict.get("extra_body_params"),
            response_mapping=config_dict.get("response_mapping"),
            max_retries=config_dict.get("max_retries", 3),
            timeout=config_dict.get("timeout", 60),
            max_tokens_limit=config_dict.get("max_tokens_limit", 4096),
            supports_streaming=config_dict.get("supports_streaming", True),
            supports_functions=config_dict.get("supports_functions", False),
            supports_vision=config_dict.get("supports_vision", False),
            supports_embeddings=config_dict.get("supports_embeddings", True),
            requests_per_minute=config_dict.get("requests_per_minute"),
            tokens_per_minute=config_dict.get("tokens_per_minute"),
        )

        return CustomAPIProvider(config)

    def _get_default_api_key(self, provider_type: str) -> Optional[str]:
        """Get default API key from settings."""

        key_mapping = {
            ProviderType.OPENAI: settings.openai_api_key,
            ProviderType.ANTHROPIC: settings.anthropic_api_key,
            ProviderType.DEEPSEEK: getattr(settings, "deepseek_api_key", None),
            ProviderType.GROQ: getattr(settings, "groq_api_key", None),
            ProviderType.TOGETHER: getattr(settings, "together_api_key", None),
            ProviderType.AZURE_OPENAI: getattr(settings, "azure_api_key", None),
            ProviderType.MOONSHOT: getattr(settings, "moonshot_api_key", None),
            ProviderType.ZHIPU: getattr(settings, "zhipu_api_key", None),
        }

        return key_mapping.get(provider_type)

    def list_available_providers(self) -> List[str]:
        """List all available provider types."""
        return [e.value for e in ProviderType]

    def get_provider_info(self, provider_type: str) -> Dict[str, Any]:
        """Get information about a provider."""

        info = {
            "type": provider_type,
            "requires_api_key": True,
            "supports_streaming": True,
            "supports_functions": False,
            "supports_vision": False,
            "supports_embeddings": False,
            "default_model": None,
            "description": None,
        }

        # Provider-specific info
        if provider_type == ProviderType.OPENAI:
            info.update(
                {
                    "supports_functions": True,
                    "supports_vision": True,
                    "supports_embeddings": True,
                    "default_model": "gpt-4o-mini",
                    "description": "OpenAI GPT models",
                }
            )
        elif provider_type == ProviderType.ANTHROPIC:
            info.update(
                {
                    "supports_vision": True,
                    "default_model": "claude-3-haiku-20240307",
                    "description": "Anthropic Claude models",
                }
            )
        elif provider_type == ProviderType.OLLAMA:
            info.update(
                {
                    "requires_api_key": False,
                    "default_model": "llama3.2:latest",
                    "description": "Local Ollama models",
                }
            )
        elif provider_type == ProviderType.OLLAMA_ADVANCED:
            info.update(
                {
                    "requires_api_key": False,
                    "default_model": "llama3.2:latest",
                    "description": "Local Ollama models (advanced features)",
                }
            )
        elif provider_type == ProviderType.GROQ:
            info.update(
                {
                    "default_model": "mixtral-8x7b-32768",
                    "description": "Groq Cloud - Fast inference",
                }
            )
        elif provider_type == ProviderType.TOGETHER:
            info.update(
                {
                    "supports_embeddings": True,
                    "default_model": "meta-llama/Llama-3-70b-chat-hf",
                    "description": "Together AI - Open source models",
                }
            )
        elif provider_type == ProviderType.VLLM:
            info.update(
                {"requires_api_key": False, "description": "Self-hosted vLLM server"}
            )
        elif provider_type == ProviderType.LOCALAI:
            info.update(
                {
                    "requires_api_key": False,
                    "supports_embeddings": True,
                    "description": "LocalAI - Local OpenAI alternative",
                }
            )

        return info


# Global factory instance
llm_factory = LLMFactory()


# Convenience functions
def create_llm_provider(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """Create an LLM provider.

    Examples:
        # Standard providers
        provider = create_llm_provider("openai", api_key="sk-...")
        provider = create_llm_provider("anthropic", api_key="sk-ant-...")
        provider = create_llm_provider("ollama", base_url="http://localhost:11434")

        # Custom API presets
        provider = create_llm_provider("groq", api_key="gsk_...")
        provider = create_llm_provider("together", api_key="...")
        provider = create_llm_provider("moonshot", api_key="...")

        # Fully custom API
        provider = create_llm_provider(
            "custom",
            base_url="https://api.example.com",
            api_key="...",
            api_format="openai",
            chat_endpoint="/v1/chat",
            default_model="custom-model"
        )
    """
    return llm_factory.create_provider(provider, api_key, model, base_url, **kwargs)


def list_providers() -> List[str]:
    """List available provider types."""
    return llm_factory.list_available_providers()


def get_provider_info(provider: str) -> Dict[str, Any]:
    """Get information about a provider."""
    return llm_factory.get_provider_info(provider)
