"""Custom Third-Party API Provider for LLM Integration.

Supports any OpenAI-compatible API endpoints including:
- Azure OpenAI Service
- Groq Cloud
- Together AI
- Anyscale
- Perplexity AI
- DeepInfra
- Replicate
- Hugging Face Inference API
- Self-hosted vLLM
- Text Generation Inference (TGI)
- LocalAI
- FastChat
- Xinference
- One API (统一接口)
- API2D
- OpenRouter
- Custom endpoints
"""

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from core.exceptions import LLMError
from core.logging import get_logger
from infrastructure.llm.base import LLMConfig, LLMProvider, Message

logger = get_logger(__name__)


class APIFormat(str, Enum):
    """Supported API formats."""

    OPENAI = "openai"  # OpenAI compatible format
    ANTHROPIC = "anthropic"  # Anthropic Claude format
    GOOGLE = "google"  # Google Gemini format
    CUSTOM = "custom"  # Custom format with mapping


class AuthType(str, Enum):
    """Authentication types."""

    BEARER = "bearer"  # Bearer token
    API_KEY = "api_key"  # X-API-Key header
    BASIC = "basic"  # Basic authentication
    CUSTOM_HEADER = "custom_header"  # Custom header
    NONE = "none"  # No authentication


@dataclass
class CustomAPIConfig:
    """Configuration for custom API provider."""

    # Basic settings
    name: str
    base_url: str
    api_format: APIFormat = APIFormat.OPENAI

    # Authentication
    auth_type: AuthType = AuthType.BEARER
    api_key: Optional[str] = None
    auth_header_name: Optional[str] = None  # For custom header

    # Model settings
    default_model: str = "gpt-3.5-turbo"
    available_models: List[str] = None

    # Endpoints
    chat_endpoint: str = "/v1/chat/completions"
    completions_endpoint: str = "/v1/completions"
    embeddings_endpoint: str = "/v1/embeddings"
    models_endpoint: str = "/v1/models"

    # Request customization
    extra_headers: Dict[str, str] = None
    extra_body_params: Dict[str, Any] = None

    # Response mapping (for custom formats)
    response_mapping: Dict[str, str] = None

    # Limits and timeouts
    max_retries: int = 3
    timeout: int = 60
    max_tokens_limit: int = 4096

    # Feature flags
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    supports_embeddings: bool = True

    # Rate limiting
    requests_per_minute: Optional[int] = None
    tokens_per_minute: Optional[int] = None


class CustomAPIProvider(LLMProvider):
    """Provider for custom third-party APIs."""

    # Preset configurations for popular services
    PRESETS = {
        "azure_openai": {
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.API_KEY,
            "auth_header_name": "api-key",
            "chat_endpoint": "/openai/deployments/{model}/chat/completions?api-version=2024-02-15-preview",
            "supports_functions": True,
            "supports_vision": True,
        },
        "groq": {
            "base_url": "https://api.groq.com/openai",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "default_model": "mixtral-8x7b-32768",
            "available_models": [
                "mixtral-8x7b-32768",
                "llama3-70b-8192",
                "llama3-8b-8192",
                "gemma-7b-it",
            ],
            "max_tokens_limit": 32768,
        },
        "together": {
            "base_url": "https://api.together.xyz",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "default_model": "meta-llama/Llama-3-70b-chat-hf",
        },
        "anyscale": {
            "base_url": "https://api.endpoints.anyscale.com",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
        },
        "perplexity": {
            "base_url": "https://api.perplexity.ai",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "default_model": "pplx-70b-online",
        },
        "deepinfra": {
            "base_url": "https://api.deepinfra.com",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/openai/chat/completions",
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "extra_headers": {
                "HTTP-Referer": "https://aiwendy.com",
                "X-Title": "AIWendy Trading Coach",
            },
        },
        "huggingface": {
            "base_url": "https://api-inference.huggingface.co",
            "api_format": APIFormat.CUSTOM,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/models/{model}",
            "response_mapping": {"content": "generated_text", "role": "assistant"},
        },
        "vllm": {
            "base_url": "http://localhost:8000",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.NONE,
            "chat_endpoint": "/v1/chat/completions",
            "supports_streaming": True,
        },
        "localai": {
            "base_url": "http://localhost:8080",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.NONE,
            "chat_endpoint": "/v1/chat/completions",
            "models_endpoint": "/v1/models",
        },
        "oneapi": {
            "base_url": "http://localhost:3000",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "supports_functions": True,
        },
        "api2d": {
            "base_url": "https://api.api2d.com",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "extra_headers": {"User-Agent": "AIWendy/2.0"},
        },
        "xinference": {
            "base_url": "http://localhost:9997",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.NONE,
            "chat_endpoint": "/v1/chat/completions",
        },
        "moonshot": {
            "base_url": "https://api.moonshot.cn",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "default_model": "moonshot-v1-8k",
        },
        "zhipu": {
            "base_url": "https://open.bigmodel.cn/api/paas",
            "api_format": APIFormat.CUSTOM,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v4/chat/completions",
            "default_model": "glm-4",
        },
        "baichuan": {
            "base_url": "https://api.baichuan-ai.com",
            "api_format": APIFormat.OPENAI,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/chat/completions",
            "default_model": "Baichuan2-Turbo",
        },
        "qwen": {
            "base_url": "https://dashscope.aliyuncs.com/api",
            "api_format": APIFormat.CUSTOM,
            "auth_type": AuthType.BEARER,
            "chat_endpoint": "/v1/services/aigc/text-generation/generation",
            "default_model": "qwen-turbo",
        },
    }

    def __init__(self, config: CustomAPIConfig):
        """Initialize custom API provider."""
        self.config = config
        self.client = self._create_client()
        self._rate_limiter = RateLimiter(
            requests_per_minute=config.requests_per_minute,
            tokens_per_minute=config.tokens_per_minute,
        )

    @classmethod
    def from_preset(
        cls, preset_name: str, api_key: str, base_url: Optional[str] = None
    ) -> "CustomAPIProvider":
        """Create provider from preset configuration."""
        if preset_name not in cls.PRESETS:
            raise ValueError(
                f"Unknown preset: {preset_name}. Available: {list(cls.PRESETS.keys())}"
            )

        preset = cls.PRESETS[preset_name].copy()

        # Override base URL if provided
        if base_url:
            preset["base_url"] = base_url

        # Create config
        config = CustomAPIConfig(name=preset_name, api_key=api_key, **preset)

        return cls(config)

    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client with authentication."""
        headers = {}

        # Set authentication headers
        if self.config.auth_type == AuthType.BEARER:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.auth_type == AuthType.API_KEY:
            header_name = self.config.auth_header_name or "X-API-Key"
            headers[header_name] = self.config.api_key
        elif (
            self.config.auth_type == AuthType.CUSTOM_HEADER
            and self.config.auth_header_name
        ):
            headers[self.config.auth_header_name] = self.config.api_key
        elif self.config.auth_type == AuthType.BASIC:
            import base64

            auth_string = base64.b64encode(f":{self.config.api_key}".encode()).decode()
            headers["Authorization"] = f"Basic {auth_string}"

        # Add extra headers
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)

        return httpx.AsyncClient(
            base_url=self.config.base_url, headers=headers, timeout=self.config.timeout
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def chat(self, messages: List[Message], config: LLMConfig, **kwargs) -> str:
        """Send chat completion request."""

        # Apply rate limiting
        await self._rate_limiter.acquire()

        # Prepare request based on API format
        if self.config.api_format == APIFormat.OPENAI:
            request_data = self._prepare_openai_request(messages, config, **kwargs)
        elif self.config.api_format == APIFormat.ANTHROPIC:
            request_data = self._prepare_anthropic_request(messages, config, **kwargs)
        elif self.config.api_format == APIFormat.GOOGLE:
            request_data = self._prepare_google_request(messages, config, **kwargs)
        else:
            request_data = self._prepare_custom_request(messages, config, **kwargs)

        # Add extra body parameters
        if self.config.extra_body_params:
            request_data.update(self.config.extra_body_params)

        # Build endpoint URL
        endpoint = self._build_endpoint(self.config.chat_endpoint, config.model)

        try:
            response = await self.client.post(endpoint, json=request_data)
            response.raise_for_status()

            # Parse response based on format
            return self._parse_response(response.json(), self.config.api_format)

        except httpx.HTTPStatusError as e:
            error_text = None
            try:
                error_text = e.response.text
            except Exception:
                error_text = None

            if error_text:
                error_text = error_text.strip()
                if len(error_text) > 1000:
                    error_text = error_text[:1000] + "..."

            logger.error(f"HTTP error from {self.config.name}: {e} | {error_text}")
            message = f"API request failed: {e}"
            if error_text:
                message = f"{message} | Response: {error_text}"
            raise LLMError(message)
        except Exception as e:
            logger.error(f"Error calling {self.config.name}: {e}")
            raise LLMError(f"Unexpected error: {e}")

    async def stream_chat(
        self, messages: List[Message], config: LLMConfig, **kwargs
    ) -> AsyncIterator[str]:
        """Stream chat completion response."""

        if not self.config.supports_streaming:
            # Fallback to non-streaming
            response = await self.chat(messages, config, **kwargs)
            yield response
            return

        # Apply rate limiting
        await self._rate_limiter.acquire()

        # Prepare request
        if self.config.api_format == APIFormat.OPENAI:
            request_data = self._prepare_openai_request(
                messages, config, stream=True, **kwargs
            )
        else:
            # Fallback to non-streaming for non-OpenAI formats
            response = await self.chat(messages, config, **kwargs)
            yield response
            return

        # Add extra body parameters
        if self.config.extra_body_params:
            request_data.update(self.config.extra_body_params)

        # Build endpoint URL
        endpoint = self._build_endpoint(self.config.chat_endpoint, config.model)

        try:
            async with self.client.stream(
                "POST", endpoint, json=request_data
            ) as response:
                if response.status_code >= 400:
                    error_text = None
                    try:
                        error_bytes = await response.aread()
                        error_text = error_bytes.decode(errors="replace")
                    except Exception:
                        error_text = None

                    if error_text:
                        error_text = error_text.strip()
                        if len(error_text) > 1000:
                            error_text = error_text[:1000] + "..."

                    message = f"API request failed: HTTP {response.status_code} for url '{response.url}'"
                    if error_text:
                        message = f"{message} | Response: {error_text}"
                    raise LLMError(message)

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            logger.error(f"Stream error from {self.config.name}: {e}")
            raise LLMError(f"Stream failed: {e}")

    async def get_embeddings(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """Get embeddings for texts."""

        if not self.config.supports_embeddings:
            raise NotImplementedError(f"{self.config.name} does not support embeddings")

        model = model or self.config.default_model
        endpoint = self._build_endpoint(self.config.embeddings_endpoint, model)

        embeddings = []

        for text in texts:
            request_data = {"input": text, "model": model}

            if self.config.extra_body_params:
                request_data.update(self.config.extra_body_params)

            try:
                response = await self.client.post(endpoint, json=request_data)
                response.raise_for_status()

                data = response.json()
                if "data" in data and data["data"]:
                    embedding = data["data"][0]["embedding"]
                    embeddings.append(embedding)
                else:
                    embeddings.append([])

            except Exception as e:
                logger.error(f"Embedding error from {self.config.name}: {e}")
                embeddings.append([])

        return embeddings

    async def list_models(self, force_refresh: bool = False) -> List[str]:
        """List available models."""

        def _normalize(value: Any) -> Optional[str]:
            if not isinstance(value, str):
                return None
            cleaned = value.strip()
            return cleaned or None

        def _dedupe_keep_order(values: List[str]) -> List[str]:
            seen = set()
            result: List[str] = []
            for item in values:
                if item in seen:
                    continue
                seen.add(item)
                result.append(item)
            return result

        if self.config.available_models and not force_refresh:
            cleaned = [_normalize(m) for m in self.config.available_models]
            return [m for m in cleaned if m]

        if not self.config.models_endpoint:
            return (
                [self.config.default_model]
                if _normalize(self.config.default_model)
                else []
            )

        endpoint = self._build_endpoint(self.config.models_endpoint, None)
        try:
            response = await self.client.get(endpoint)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_text = None
            try:
                error_text = e.response.text
            except Exception:
                error_text = None
            if error_text:
                error_text = error_text.strip()
                if len(error_text) > 1000:
                    error_text = error_text[:1000] + "..."
            logger.error(
                f"HTTP error listing models from {self.config.name}: {e} | {error_text}"
            )
            message = f"API request failed: {e}"
            if error_text:
                message = f"{message} | Response: {error_text}"
            raise LLMError(message)
        except Exception as e:
            logger.error(f"Error listing models from {self.config.name}: {e}")
            raise LLMError(f"Failed to list models: {e}")

        try:
            data = response.json()
        except Exception as e:
            raise LLMError(f"Failed to parse models response: {e}")

        models: List[str] = []

        def _add(item: Any) -> None:
            if isinstance(item, str):
                cleaned = _normalize(item)
                if cleaned:
                    models.append(cleaned)
                return
            if isinstance(item, dict):
                for key in ("id", "model", "name"):
                    cleaned = _normalize(item.get(key))
                    if cleaned:
                        models.append(cleaned)
                        return

        def _collect(container: Any) -> None:
            if container is None:
                return
            if isinstance(container, list):
                for it in container:
                    _add(it)
                return
            if isinstance(container, dict):
                # Some providers nest lists under `data`/`models`.
                if "data" in container:
                    _collect(container.get("data"))
                if "models" in container:
                    _collect(container.get("models"))

        if isinstance(data, list):
            _collect(data)
        elif isinstance(data, dict):
            if "data" in data:
                _collect(data.get("data"))
            elif "models" in data:
                _collect(data.get("models"))
            else:
                # Last-chance: if the payload itself looks like a nested container.
                _collect(data)

        models = [m for m in models if m]
        if not models:
            fallback: List[str] = []
            if self.config.available_models:
                fallback = [
                    m
                    for m in ([_normalize(x) for x in self.config.available_models])
                    if m
                ]
            if not fallback:
                fallback = (
                    [_normalize(self.config.default_model)]
                    if _normalize(self.config.default_model)
                    else []
                )
            models = fallback

        return _dedupe_keep_order(models)

    def _prepare_openai_request(
        self, messages: List[Message], config: LLMConfig, stream: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """Prepare request in OpenAI format."""

        request = {
            "model": config.model or self.config.default_model,
            "messages": [
                {"role": msg.role, "content": msg.content} for msg in messages
            ],
            "temperature": config.temperature or 0.7,
            "max_tokens": min(config.max_tokens or 2000, self.config.max_tokens_limit),
            "stream": stream,
        }

        # Add optional parameters
        if config.top_p is not None:
            request["top_p"] = config.top_p

        if config.frequency_penalty is not None:
            request["frequency_penalty"] = config.frequency_penalty

        if config.presence_penalty is not None:
            request["presence_penalty"] = config.presence_penalty

        # Add function calling if supported
        if self.config.supports_functions and "functions" in kwargs:
            request["functions"] = kwargs["functions"]
            if "function_call" in kwargs:
                request["function_call"] = kwargs["function_call"]

        return request

    def _prepare_anthropic_request(
        self, messages: List[Message], config: LLMConfig, **kwargs
    ) -> Dict[str, Any]:
        """Prepare request in Anthropic format."""

        # Convert messages to Anthropic format
        system_prompt = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        request = {
            "model": config.model or self.config.default_model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens or 2000,
            "temperature": config.temperature or 0.7,
        }

        if system_prompt:
            request["system"] = system_prompt

        return request

    def _prepare_google_request(
        self, messages: List[Message], config: LLMConfig, **kwargs
    ) -> Dict[str, Any]:
        """Prepare request in Google Gemini format."""

        # Convert messages to Gemini format
        contents = []

        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        return {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature or 0.7,
                "maxOutputTokens": config.max_tokens or 2000,
                "topP": config.top_p or 0.95,
                "topK": 40,
            },
        }

    def _prepare_custom_request(
        self, messages: List[Message], config: LLMConfig, **kwargs
    ) -> Dict[str, Any]:
        """Prepare request in custom format."""

        # Default to OpenAI format as base
        return self._prepare_openai_request(messages, config, **kwargs)

    def _parse_response(self, data: Dict[str, Any], format: APIFormat) -> str:
        """Parse response based on format."""

        if format == APIFormat.OPENAI:
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]

        elif format == APIFormat.ANTHROPIC:
            if "content" in data and data["content"]:
                return data["content"][0]["text"]

        elif format == APIFormat.GOOGLE:
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]

        elif format == APIFormat.CUSTOM:
            # Use response mapping if provided
            if self.config.response_mapping:
                content_path = self.config.response_mapping.get("content", "content")
                # Navigate nested path (e.g., "choices.0.message.content")
                result = data
                for key in content_path.split("."):
                    if key.isdigit():
                        result = result[int(key)]
                    else:
                        result = result.get(key, "")
                return result

        # Fallback: try to find content in common locations
        if "content" in data:
            return data["content"]
        if "text" in data:
            return data["text"]
        if "generated_text" in data:
            return data["generated_text"]
        if "response" in data:
            return data["response"]

        raise ValueError(f"Could not parse response from {self.config.name}: {data}")

    def _build_endpoint(self, endpoint_template: str, model: Optional[str]) -> str:
        """Build endpoint URL with model substitution."""

        # Replace model placeholder if needed
        if model and "{model}" in endpoint_template:
            endpoint_template = endpoint_template.replace("{model}", model)

        # Smart URL handling to avoid duplicate /v1
        # If base_url ends with /v1 and endpoint starts with /v1, remove the duplicate
        if self.config.base_url:
            base_parts = self.config.base_url.rstrip("/").split("/")
            endpoint_parts = endpoint_template.lstrip("/").split("/")

            # Check if there's a duplicate path segment at the junction
            if base_parts and endpoint_parts and base_parts[-1] == endpoint_parts[0]:
                # Remove the duplicate from endpoint
                endpoint_template = "/" + "/".join(endpoint_parts[1:])

        return endpoint_template

    async def health_check(self) -> bool:
        """Check if the API is accessible."""

        try:
            # Try to list models or send a minimal request
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Health check failed for {self.config.name}: {e}")
            return False

    # Implement abstract methods from base class to match interface
    async def chat_stream(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        """Stream chat completion response (wrapper for stream_chat)."""
        async for chunk in self.stream_chat(messages, config):
            yield chunk

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings for text (wrapper for get_embeddings)."""
        embeddings = await self.get_embeddings([text], model)
        return embeddings[0] if embeddings else []

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens in text (simple approximation)."""
        # Simple approximation: 1 token ≈ 4 characters
        # This is a rough estimate and should be improved with proper tokenization
        return len(text) // 4


class RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(
        self,
        requests_per_minute: Optional[int] = None,
        tokens_per_minute: Optional[int] = None,
    ):
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.request_times: List[float] = []
        self.token_usage: List[Tuple[float, int]] = []

    async def acquire(self, tokens: int = 0):
        """Wait if necessary to respect rate limits."""

        current_time = time.time()

        # Check request rate limit
        if self.requests_per_minute:
            # Remove old requests
            self.request_times = [
                t for t in self.request_times if current_time - t < 60
            ]

            if len(self.request_times) >= self.requests_per_minute:
                # Wait until oldest request is older than 1 minute
                wait_time = 60 - (current_time - self.request_times[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            self.request_times.append(current_time)

        # Check token rate limit
        if self.tokens_per_minute and tokens > 0:
            # Remove old token usage
            self.token_usage = [
                (t, tok) for t, tok in self.token_usage if current_time - t < 60
            ]

            total_tokens = sum(tok for _, tok in self.token_usage)

            if total_tokens + tokens > self.tokens_per_minute:
                # Wait for some tokens to expire
                wait_time = 60 - (current_time - self.token_usage[0][0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    current_time = time.time()

            self.token_usage.append((current_time, tokens))


# Export convenience function
def create_custom_provider(
    provider_name: str, api_key: str, base_url: Optional[str] = None, **kwargs
) -> CustomAPIProvider:
    """Create a custom API provider easily."""

    # Check if it's a preset
    if provider_name in CustomAPIProvider.PRESETS:
        return CustomAPIProvider.from_preset(provider_name, api_key, base_url)

    # Create custom configuration
    config = CustomAPIConfig(
        name=provider_name,
        base_url=base_url or f"http://localhost:8000",
        api_key=api_key,
        **kwargs,
    )

    return CustomAPIProvider(config)
