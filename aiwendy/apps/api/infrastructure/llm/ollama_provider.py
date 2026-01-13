"""Ollama LLM provider for local model support."""

import json
import os
from typing import AsyncIterator, List, Optional

import aiohttp

from core.logging import get_logger

from .base import LLMConfig, LLMProvider, Message

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLM models."""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Ollama provider.

        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.base_url = self.base_url.rstrip("/")

    async def chat(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> str:
        """Send chat request and get complete response."""
        result = []
        async for chunk in self.chat_stream(messages, config):
            result.append(chunk)
        return "".join(result)

    async def chat_stream(
        self,
        messages: List[Message],
        config: LLMConfig,
    ) -> AsyncIterator[str]:
        """Send chat request and stream response."""
        # Convert messages to Ollama format
        formatted_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        # Prepare request data
        data = {
            "model": config.model,
            "messages": formatted_messages,
            "stream": True,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
            },
        }

        if config.max_tokens:
            data["options"]["num_predict"] = config.max_tokens

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"Ollama API error: {response.status} - {error_text}"
                        )
                        yield f"Error: Ollama API returned status {response.status}"
                        return

                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line)
                                if "message" in chunk:
                                    content = chunk["message"].get("content", "")
                                    if content:
                                        yield content
                                if chunk.get("done", False):
                                    break
                            except json.JSONDecodeError as e:
                                logger.debug(f"Failed to parse JSON: {line}")
                                continue

        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {e}")
            yield f"Error: Failed to connect to Ollama service at {self.base_url}"
        except Exception as e:
            logger.error(f"Unexpected error in Ollama chat: {e}")
            yield f"Error: {str(e)}"

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> List[float]:
        """Generate embeddings for text."""
        # Use default embedding model if not specified
        model = model or "nomic-embed-text"

        data = {"model": model, "prompt": text}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json=data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("embedding", [])
                    else:
                        logger.error(f"Ollama embedding error: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            return []

    async def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """
        Count tokens in text.

        Note: Ollama doesn't provide a direct token counting endpoint,
        so we estimate based on character count.
        """
        # Rough estimation: 1 token ≈ 4 characters for English text
        # This is a simplified approach; actual tokenization varies by model
        return len(text) // 4

    async def check_health(self) -> bool:
        """Check if Ollama service is running."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        return [model["name"] for model in models]
                    return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def pull_model(self, model_name: str) -> AsyncIterator[str]:
        """
        Pull a model from Ollama registry.

        Args:
            model_name: Name of the model to pull

        Yields:
            Progress updates during model download
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = json.dumps({"name": model_name})
                async with session.post(
                    f"{self.base_url}/api/pull",
                    data=data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    async for line in response.content:
                        if line:
                            try:
                                progress = json.loads(line)
                                if "status" in progress:
                                    status = progress["status"]
                                    if "completed" in progress and "total" in progress:
                                        completed = progress["completed"]
                                        total = progress["total"]
                                        yield f"{status}: {completed}/{total}"
                                    else:
                                        yield status
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield f"Error: {str(e)}"
