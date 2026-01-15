"""LLM Configuration Routes - Allow users to configure custom LLM providers."""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import RetryError

from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from core.exceptions import AppException
from core.i18n import get_request_locale, t
from domain.user.models import User

# Create encryption helper functions
_encryption_service = get_encryption_service()
encrypt_value = _encryption_service.encrypt
decrypt_value = _encryption_service.decrypt
from infrastructure.llm.base import LLMConfig as BaseLLMConfig
from infrastructure.llm.base import Message
from infrastructure.llm.custom_api_provider import APIFormat, AuthType, CustomAPIConfig
from infrastructure.llm.factory import (
    create_llm_provider,
    get_provider_info,
    list_providers,
    llm_factory,
)

router = APIRouter(prefix="/api/v1/llm-config", tags=["LLM Configuration"])


class LLMProviderConfig(BaseModel):
    """LLM Provider configuration."""

    id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(..., description="Display name for this configuration")
    provider_type: str = Field(
        ..., description="Provider type (openai, anthropic, custom, etc.)"
    )
    is_active: bool = Field(default=True)
    is_default: bool = Field(default=False)

    # Connection settings
    api_key: Optional[str] = Field(None, description="API key (will be encrypted)")
    base_url: Optional[str] = Field(None, description="Base URL for API")

    # Model settings
    default_model: Optional[str] = Field(None, description="Default model to use")
    available_models: Optional[List[str]] = Field(
        None, description="List of available models"
    )

    # Custom API settings (only for custom providers)
    api_format: Optional[str] = Field(
        default="openai", description="API format (openai, anthropic, google, custom)"
    )
    auth_type: Optional[str] = Field(
        default="bearer", description="Auth type (bearer, api_key, basic, none)"
    )
    auth_header_name: Optional[str] = Field(None, description="Custom auth header name")

    # Endpoints (for custom providers)
    chat_endpoint: Optional[str] = Field(default="/v1/chat/completions")
    completions_endpoint: Optional[str] = Field(default="/v1/completions")
    embeddings_endpoint: Optional[str] = Field(default="/v1/embeddings")
    models_endpoint: Optional[str] = Field(default="/v1/models")

    # Extra configuration
    extra_headers: Optional[Dict[str, str]] = Field(
        None, description="Extra headers to send"
    )
    extra_body_params: Optional[Dict[str, Any]] = Field(
        None, description="Extra body parameters"
    )

    # Features
    supports_streaming: bool = Field(default=True)
    supports_functions: bool = Field(default=False)
    supports_vision: bool = Field(default=False)
    supports_embeddings: bool = Field(default=True)

    # Limits
    max_tokens_limit: int = Field(default=4096)
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator("provider_type")
    def validate_provider_type(cls, v):
        valid_providers = list_providers()
        if v not in valid_providers and v != "custom":
            raise ValueError(
                f"Invalid provider type. Must be one of: {', '.join(valid_providers)} or 'custom'"
            )
        return v


class TestLLMRequest(BaseModel):
    """Request to test LLM configuration."""

    config_id: str = Field(..., description="Configuration ID to test")
    message: str = Field(
        default="Hello! Can you introduce yourself?", description="Test message"
    )
    model: Optional[str] = Field(None, description="Model to use (overrides default)")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=200, ge=10, le=4096)


class QuickTestRequest(BaseModel):
    """Request to quick test a provider without saving configuration."""

    provider_type: str = Field(
        ..., description="Provider type (e.g., openai, anthropic)"
    )
    api_key: str = Field(..., description="API key for the provider")
    base_url: Optional[str] = Field(
        None, description="Base URL for custom API endpoints"
    )
    model: Optional[str] = Field(None, description="Model to use for testing")


class FetchModelsRequest(BaseModel):
    """Request to fetch models for a provider (server-side to avoid CORS)."""

    provider_type: str = Field(
        ..., description="Provider type (openai, openrouter, custom, etc.)"
    )
    api_key: Optional[str] = Field(None, description="API key (if required)")
    base_url: Optional[str] = Field(
        None, description="Override base URL for the provider"
    )
    api_format: Optional[str] = Field(
        default="openai", description="API format for custom providers"
    )
    auth_type: Optional[str] = Field(
        default="bearer", description="Auth type for custom providers"
    )
    auth_header_name: Optional[str] = Field(
        None, description="Custom auth header name for custom providers"
    )
    models_endpoint: Optional[str] = Field(
        None, description="Models endpoint path for custom providers"
    )
    extra_headers: Optional[Dict[str, str]] = Field(
        None, description="Extra headers to send"
    )


class ModelsResponse(BaseModel):
    """Response containing a list of models."""

    models: List[str]


def _clean_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None
    cleaned = base_url.strip()
    return cleaned or None


def _clean_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_models_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
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
    return cleaned


def _choose_preferred_model(
    models: List[str],
    *,
    provider_type: Optional[str] = None,
    api_format: Optional[str] = None,
) -> Optional[str]:
    """Choose a sensible default model from a list.

    This avoids picking alphabetically-first items like `aqa` that may exist but be unusable on some gateways.
    """

    cleaned = _clean_models_list(models)
    if not cleaned:
        return None

    preferred: List[str] = []
    if provider_type in {"anthropic"} or api_format == "anthropic":
        preferred = [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-2.1",
        ]
    elif provider_type in {"ollama", "ollama_advanced"}:
        preferred = [
            "llama3.2:latest",
            "llama3:latest",
        ]
    else:
        # OpenAI-compatible defaults
        preferred = [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]

    preferred_set = set(preferred)
    for model in cleaned:
        if model in preferred_set:
            return model

    # Heuristic fallbacks
    prefixes = []
    if provider_type in {"anthropic"} or api_format == "anthropic":
        prefixes = ["claude-"]
    elif provider_type in {"ollama", "ollama_advanced"}:
        prefixes = ["llama"]
    else:
        prefixes = [
            "gpt-",
            "claude-",
            "gemini",
            "deepseek",
            "qwen",
            "moonshot",
            "glm",
            "yi",
            "llama",
        ]

    for prefix in prefixes:
        for model in cleaned:
            if model.startswith(prefix):
                return model

    # Last resort: avoid known problematic placeholder if possible
    for model in cleaned:
        if model.lower() == "aqa":
            continue
        return model

    return cleaned[0]


def _mask_secrets(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"sk-ant-[A-Za-z0-9_-]{8,}", "sk-ant-***", text)
    text = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-***", text)
    text = re.sub(r"gsk_[A-Za-z0-9_-]{8,}", "gsk_***", text)
    return text


def _unwrap_retry_error(error: Exception) -> Exception:
    if isinstance(error, RetryError):
        try:
            inner = error.last_attempt.exception()
            if inner:
                return inner
        except Exception:
            return error
    return error


async def _list_models(provider: Any) -> List[str]:
    """Best-effort model listing across different provider implementations."""
    list_models_fn = getattr(provider, "list_models", None)
    if not list_models_fn:
        return []

    try:
        return await list_models_fn(force_refresh=True)
    except TypeError:
        # Providers that don't support force_refresh
        return await list_models_fn()


class LLMProviderInfo(BaseModel):
    """Information about an LLM provider."""

    type: str
    requires_api_key: bool
    supports_streaming: bool
    supports_functions: bool
    supports_vision: bool
    supports_embeddings: bool
    default_model: Optional[str]
    description: Optional[str]
    preset_available: bool


@router.get("/providers")
async def list_available_providers() -> Dict[str, Any]:
    """List all available LLM provider types and presets."""

    providers = list_providers()
    provider_info = []

    for provider in providers:
        info = get_provider_info(provider)
        provider_info.append(
            LLMProviderInfo(
                type=provider,
                requires_api_key=info["requires_api_key"],
                supports_streaming=info["supports_streaming"],
                supports_functions=info["supports_functions"],
                supports_vision=info["supports_vision"],
                supports_embeddings=info["supports_embeddings"],
                default_model=info["default_model"],
                description=info["description"],
                preset_available=provider != "custom",
            )
        )

    return {
        "providers": provider_info,
        "presets": {
            "cloud": [
                "openai",
                "anthropic",
                "groq",
                "together",
                "anyscale",
                "perplexity",
                "deepinfra",
                "openrouter",
                "moonshot",
                "zhipu",
                "baichuan",
                "qwen",
                "deepseek",
            ],
            "local": ["ollama", "vllm", "localai", "xinference"],
            "proxy": ["oneapi", "api2d"],
        },
    }


@router.get("/user-configs")
async def get_user_configs(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[LLMProviderConfig]:
    """Get user's LLM configurations."""

    # Get configs from user's api_keys_encrypted field
    # We'll use this JSON field to store LLM configurations
    configs = (
        current_user.api_keys_encrypted.get("llm_configs", [])
        if current_user.api_keys_encrypted
        else []
    )

    # Decrypt API keys before returning
    decrypted_configs = []
    for config in configs:
        config_dict = config.copy()
        if config_dict.get("api_key"):
            try:
                # Decrypt the API key
                config_dict["api_key"] = "sk-...****"  # Mask for security
            except Exception:
                pass
        decrypted_configs.append(LLMProviderConfig(**config_dict))

    return decrypted_configs


@router.get("/user-configs/{config_id}/models", response_model=ModelsResponse)
async def get_models_for_user_config(
    config_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> ModelsResponse:
    """Fetch models for a saved user configuration (uses encrypted key server-side)."""
    locale = get_request_locale(http_request)

    if (
        not current_user.api_keys_encrypted
        or "llm_configs" not in current_user.api_keys_encrypted
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.no_llm_configurations_found", locale),
        )

    config = next(
        (
            c
            for c in current_user.api_keys_encrypted["llm_configs"]
            if c.get("id") == config_id
        ),
        None,
    )
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.llm_configuration_not_found", locale),
        )

    # Decrypt API key
    api_key: Optional[str] = None
    if config.get("api_key"):
        try:
            api_key = decrypt_value(config["api_key"])
        except Exception:
            # If it isn't encrypted (legacy), treat it as plain text
            api_key = config["api_key"]

    provider_type = config.get("provider_type")
    base_url = _clean_base_url(config.get("base_url"))

    # For OpenAI we want server-side model listing via OpenAI-compatible endpoint
    if provider_type == "openai" and not base_url:
        base_url = "https://api.openai.com"

    try:
        if provider_type == "custom":
            if not base_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=t("errors.base_url_required_for_custom_provider", locale),
                )
            config_dict = config.copy()
            config_dict["api_key"] = api_key
            provider = llm_factory.create_custom_provider_from_dict(config_dict)
        else:
            provider = create_llm_provider(
                provider=provider_type,
                api_key=api_key,
                base_url=base_url,
                model=config.get("default_model") or None,
            )

        models = await _list_models(provider)
    except HTTPException:
        raise
    except Exception as e:
        unwrapped = _unwrap_retry_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t(
                "errors.fetch_models_failed",
                locale,
                detail=_mask_secrets(str(unwrapped)),
            ),
        )

    # Deduplicate + drop empties, preserve order, then apply best-effort fallbacks
    normalized = _clean_models_list(models)
    if not normalized:
        normalized = _clean_models_list(config.get("available_models") or [])
    if not normalized:
        default_model = _clean_str(config.get("default_model"))
        if default_model:
            normalized = [default_model]
    return ModelsResponse(models=normalized)


@router.post("/models", response_model=ModelsResponse)
async def fetch_models_server_side(
    request: FetchModelsRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> ModelsResponse:
    """Fetch models for a provider server-side (avoids browser CORS limits)."""
    locale = get_request_locale(http_request)

    provider_type = request.provider_type
    base_url = _clean_base_url(request.base_url)

    # Default OpenAI base URL when not provided
    if provider_type == "openai" and not base_url:
        base_url = "https://api.openai.com"

    try:
        if provider_type == "custom":
            if not base_url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=t("errors.base_url_required_for_custom_provider", locale),
                )

            from infrastructure.llm.custom_api_provider import CustomAPIProvider

            custom_config = CustomAPIConfig(
                name="custom",
                base_url=base_url,
                api_key=request.api_key,
                api_format=APIFormat(request.api_format or "openai"),
                auth_type=AuthType(request.auth_type or "bearer"),
                auth_header_name=request.auth_header_name,
                models_endpoint=request.models_endpoint or "/v1/models",
                extra_headers=request.extra_headers,
                available_models=None,
            )
            provider = CustomAPIProvider(custom_config)
        else:
            provider = create_llm_provider(
                provider=provider_type,
                api_key=request.api_key,
                base_url=base_url,
            )

        models = await _list_models(provider)
        normalized = _clean_models_list(models)
        return ModelsResponse(models=normalized)

    except HTTPException:
        raise
    except Exception as e:
        unwrapped = _unwrap_retry_error(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t(
                "errors.fetch_models_failed",
                locale,
                detail=_mask_secrets(str(unwrapped)),
            ),
        )


@router.post("/user-configs")
async def create_user_config(
    config: LLMProviderConfig,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Create a new LLM configuration for the user."""
    locale = get_request_locale(http_request)

    # Initialize api_keys_encrypted if not exists
    if not current_user.api_keys_encrypted:
        current_user.api_keys_encrypted = {}

    if "llm_configs" not in current_user.api_keys_encrypted:
        current_user.api_keys_encrypted["llm_configs"] = []

    config_dict = config.dict()
    config_dict["base_url"] = _clean_base_url(config_dict.get("base_url"))
    config_dict["default_model"] = _clean_str(config_dict.get("default_model"))
    config_dict["available_models"] = _clean_models_list(
        config_dict.get("available_models")
    )
    if not config_dict["default_model"] and config_dict["available_models"]:
        config_dict["default_model"] = _choose_preferred_model(
            config_dict["available_models"],
            provider_type=config_dict.get("provider_type"),
            api_format=config_dict.get("api_format"),
        )

    if config_dict.get("provider_type") == "custom":
        config_dict["chat_endpoint"] = (
            _clean_str(config_dict.get("chat_endpoint")) or "/v1/chat/completions"
        )
        config_dict["completions_endpoint"] = (
            _clean_str(config_dict.get("completions_endpoint")) or "/v1/completions"
        )
        config_dict["embeddings_endpoint"] = (
            _clean_str(config_dict.get("embeddings_endpoint")) or "/v1/embeddings"
        )
        config_dict["models_endpoint"] = (
            _clean_str(config_dict.get("models_endpoint")) or "/v1/models"
        )

    # Encrypt API key
    if config_dict.get("api_key"):
        config_dict["api_key"] = encrypt_value(config_dict["api_key"])

    # Add timestamps
    config_dict["created_at"] = datetime.utcnow().isoformat()
    config_dict["updated_at"] = datetime.utcnow().isoformat()

    # If this is set as default, unset other defaults
    if config.is_default:
        for existing_config in current_user.api_keys_encrypted["llm_configs"]:
            existing_config["is_default"] = False

    # Add to user configs
    current_user.api_keys_encrypted["llm_configs"].append(config_dict)

    # Mark api_keys_encrypted as modified for SQLAlchemy to detect change
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(current_user, "api_keys_encrypted")

    await session.commit()

    return {
        "status": "success",
        "message": t("messages.llm_configuration_created", locale),
        "config_id": config_dict["id"],
    }


@router.put("/user-configs/{config_id}")
async def update_user_config(
    config_id: str,
    config: LLMProviderConfig,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Update an existing LLM configuration."""
    locale = get_request_locale(http_request)

    if (
        not current_user.api_keys_encrypted
        or "llm_configs" not in current_user.api_keys_encrypted
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.no_llm_configurations_found", locale),
        )

    # Find the config
    config_index = None
    for i, existing_config in enumerate(current_user.api_keys_encrypted["llm_configs"]):
        if existing_config["id"] == config_id:
            config_index = i
            break

    if config_index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.llm_configuration_not_found", locale),
        )

    # Update config
    config_dict = config.dict()
    config_dict["base_url"] = _clean_base_url(config_dict.get("base_url"))
    config_dict["default_model"] = _clean_str(config_dict.get("default_model"))
    config_dict["available_models"] = _clean_models_list(
        config_dict.get("available_models")
    )
    if not config_dict["default_model"] and config_dict["available_models"]:
        config_dict["default_model"] = _choose_preferred_model(
            config_dict["available_models"],
            provider_type=config_dict.get("provider_type"),
            api_format=config_dict.get("api_format"),
        )

    if config_dict.get("provider_type") == "custom":
        config_dict["chat_endpoint"] = (
            _clean_str(config_dict.get("chat_endpoint")) or "/v1/chat/completions"
        )
        config_dict["completions_endpoint"] = (
            _clean_str(config_dict.get("completions_endpoint")) or "/v1/completions"
        )
        config_dict["embeddings_endpoint"] = (
            _clean_str(config_dict.get("embeddings_endpoint")) or "/v1/embeddings"
        )
        config_dict["models_endpoint"] = (
            _clean_str(config_dict.get("models_endpoint")) or "/v1/models"
        )

    if config_dict.get("api_key") and not config_dict["api_key"].startswith("sk-..."):
        config_dict["api_key"] = encrypt_value(config_dict["api_key"])
    else:
        # Keep existing encrypted key
        config_dict["api_key"] = current_user.api_keys_encrypted["llm_configs"][
            config_index
        ].get("api_key")

    config_dict["updated_at"] = datetime.utcnow().isoformat()

    # If this is set as default, unset other defaults
    if config.is_default:
        for i, existing_config in enumerate(
            current_user.api_keys_encrypted["llm_configs"]
        ):
            if i != config_index:
                existing_config["is_default"] = False

    current_user.api_keys_encrypted["llm_configs"][config_index] = config_dict

    # Mark api_keys_encrypted as modified
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(current_user, "api_keys_encrypted")

    await session.commit()

    return {
        "status": "success",
        "message": t("messages.llm_configuration_updated", locale),
    }


@router.delete("/user-configs/{config_id}")
async def delete_user_config(
    config_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Delete an LLM configuration."""
    locale = get_request_locale(http_request)

    if (
        not current_user.api_keys_encrypted
        or "llm_configs" not in current_user.api_keys_encrypted
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.no_llm_configurations_found", locale),
        )

    # Find and remove the config
    original_length = len(current_user.api_keys_encrypted["llm_configs"])
    current_user.api_keys_encrypted["llm_configs"] = [
        c
        for c in current_user.api_keys_encrypted["llm_configs"]
        if c["id"] != config_id
    ]

    if len(current_user.api_keys_encrypted["llm_configs"]) == original_length:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.llm_configuration_not_found", locale),
        )

    # Mark api_keys_encrypted as modified
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(current_user, "api_keys_encrypted")

    await session.commit()

    return {
        "status": "success",
        "message": t("messages.llm_configuration_deleted", locale),
    }


@router.post("/test")
async def test_llm_config(
    request: TestLLMRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Test an LLM configuration with a sample message."""
    locale = get_request_locale(http_request)

    if (
        not current_user.api_keys_encrypted
        or "llm_configs" not in current_user.api_keys_encrypted
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.no_llm_configurations_found", locale),
        )

    # Find the config
    config = None
    for existing_config in current_user.api_keys_encrypted["llm_configs"]:
        if existing_config["id"] == request.config_id:
            config = existing_config
            break

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.llm_configuration_not_found", locale),
        )

    # Decrypt API key
    api_key = None
    if config.get("api_key"):
        try:
            api_key = decrypt_value(config["api_key"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=t("errors.failed_to_decrypt_api_key", locale),
            )

    # Create provider
    try:
        if config["provider_type"] == "custom":
            # Create custom provider
            from infrastructure.llm.custom_api_provider import CustomAPIConfig

            default_model = _clean_str(config.get("default_model")) or "gpt-3.5-turbo"
            custom_config = CustomAPIConfig(
                name=config["name"],
                base_url=config["base_url"],
                api_key=api_key,
                api_format=APIFormat(config.get("api_format", "openai")),
                auth_type=AuthType(config.get("auth_type", "bearer")),
                auth_header_name=config.get("auth_header_name"),
                default_model=default_model,
                available_models=config.get("available_models"),
                chat_endpoint=config.get("chat_endpoint", "/v1/chat/completions"),
                completions_endpoint=config.get(
                    "completions_endpoint", "/v1/completions"
                ),
                embeddings_endpoint=config.get("embeddings_endpoint", "/v1/embeddings"),
                models_endpoint=config.get("models_endpoint", "/v1/models"),
                extra_headers=config.get("extra_headers"),
                extra_body_params=config.get("extra_body_params"),
                supports_streaming=config.get("supports_streaming", True),
                supports_functions=config.get("supports_functions", False),
                supports_vision=config.get("supports_vision", False),
                supports_embeddings=config.get("supports_embeddings", True),
                max_tokens_limit=config.get("max_tokens_limit", 4096),
                requests_per_minute=config.get("requests_per_minute"),
                tokens_per_minute=config.get("tokens_per_minute"),
            )

            from infrastructure.llm.custom_api_provider import CustomAPIProvider

            provider = CustomAPIProvider(custom_config)
        else:
            # Create standard or preset provider
            provider = create_llm_provider(
                provider=config["provider_type"],
                api_key=api_key,
                base_url=config.get("base_url"),
                model=_clean_str(config.get("default_model")),
            )

        requested_model = _clean_str(request.model)
        configured_model = _clean_str(config.get("default_model"))
        if (
            configured_model
            and configured_model.lower() == "aqa"
            and not requested_model
        ):
            configured_model = None
        model_to_use = requested_model or configured_model

        if not model_to_use:
            stored_models = config.get("available_models") or []
            if isinstance(stored_models, list):
                model_to_use = _choose_preferred_model(
                    _clean_models_list(stored_models),
                    provider_type=config.get("provider_type"),
                    api_format=config.get("api_format"),
                )

        if not model_to_use:
            try:
                provider_models = await _list_models(provider)
                if provider_models:
                    model_to_use = _choose_preferred_model(
                        _clean_models_list(provider_models),
                        provider_type=config.get("provider_type"),
                        api_format=config.get("api_format"),
                    )
            except Exception:
                model_to_use = None

        if not model_to_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=t("errors.no_model_specified", locale),
            )

        # Test the provider
        messages = [
            Message(
                role="system",
                content=t("llm_test.system_prompt", locale),
            ),
            Message(role="user", content=request.message),
        ]

        llm_config = BaseLLMConfig(
            model=model_to_use,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )

        # Get response with timing
        import time

        start_time = time.time()
        response = await asyncio.wait_for(
            provider.chat(messages, llm_config), timeout=30.0
        )
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "status": "success",
            "response": response,
            "provider": config["provider_type"],
            "model": llm_config.model,
            "latency_ms": latency_ms,
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=t("errors.request_timed_out", locale, seconds=30),
        )
    except Exception as e:
        unwrapped = _unwrap_retry_error(e)
        if isinstance(unwrapped, AppException):
            raise HTTPException(
                status_code=unwrapped.status_code, detail=_mask_secrets(str(unwrapped))
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t(
                "errors.llm_test_failed", locale, detail=_mask_secrets(str(unwrapped))
            ),
        )


@router.post("/quick-test")
async def quick_test_provider(
    request: QuickTestRequest,
    http_request: Request,
) -> Dict[str, Any]:
    """Quick test a provider without saving configuration."""
    locale = get_request_locale(http_request)

    try:
        requested_model = _clean_str(request.model)
        # Create provider
        provider = create_llm_provider(
            provider=request.provider_type,
            api_key=request.api_key,
            base_url=request.base_url,
            model=requested_model,
        )

        model_to_use = requested_model
        if not model_to_use:
            try:
                provider_models = await _list_models(provider)
                if provider_models:
                    model_to_use = _choose_preferred_model(
                        _clean_models_list(provider_models),
                        provider_type=request.provider_type,
                    )
            except Exception:
                model_to_use = None

        if not model_to_use:
            defaults = {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-haiku-20240307",
                "ollama": "llama3.2:latest",
            }
            model_to_use = defaults.get(request.provider_type)

        if not model_to_use:
            return {
                "status": "error",
                "connected": False,
                "error": t("errors.no_model_specified", locale),
                "provider": request.provider_type,
            }

        # Test with simple message
        messages = [
            Message(
                role="user",
                content="Say 'Hello! I'm working!' if you can receive this message.",
            )
        ]

        llm_config = BaseLLMConfig(
            model=model_to_use, temperature=0.1, max_tokens=50, stream=False
        )

        # Get response
        response = await asyncio.wait_for(
            provider.chat(messages, llm_config), timeout=15.0
        )

        return {
            "status": "success",
            "connected": True,
            "response": response,
            "provider": request.provider_type,
            "model": model_to_use,
        }

    except asyncio.TimeoutError:
        return {
            "status": "error",
            "connected": False,
            "error": t("errors.connection_timed_out", locale, seconds=15),
            "provider": request.provider_type,
        }
    except Exception as e:
        unwrapped = _unwrap_retry_error(e)
        return {
            "status": "error",
            "connected": False,
            "error": _mask_secrets(str(unwrapped)),
            "provider": request.provider_type,
        }


@router.get("/templates")
async def get_config_templates() -> Dict[str, Any]:
    """Get configuration templates for popular providers."""

    templates = {
        "openai_compatible": {
            "name": "OpenAI Compatible API",
            "provider_type": "custom",
            "api_format": "openai",
            "auth_type": "bearer",
            "chat_endpoint": "/v1/chat/completions",
            "completions_endpoint": "/v1/completions",
            "embeddings_endpoint": "/v1/embeddings",
            "models_endpoint": "/v1/models",
            "supports_streaming": True,
            "supports_functions": False,
            "supports_vision": False,
            "supports_embeddings": True,
        },
        "anthropic_compatible": {
            "name": "Anthropic Compatible API",
            "provider_type": "custom",
            "api_format": "anthropic",
            "auth_type": "api_key",
            "auth_header_name": "x-api-key",
            "chat_endpoint": "/v1/messages",
            "supports_streaming": True,
            "supports_vision": True,
        },
        "local_server": {
            "name": "Local Model Server",
            "provider_type": "custom",
            "base_url": "http://localhost:8000",
            "api_format": "openai",
            "auth_type": "none",
            "chat_endpoint": "/v1/chat/completions",
            "supports_streaming": True,
        },
        "huggingface_tgi": {
            "name": "Hugging Face TGI",
            "provider_type": "custom",
            "api_format": "openai",
            "auth_type": "bearer",
            "chat_endpoint": "/v1/chat/completions",
            "base_url": "http://localhost:8080",
        },
    }

    return {"templates": templates}
