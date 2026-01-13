"""
Ollama Service for local LLM support
Handles communication with Ollama API for local model inference
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from core.logging import get_logger

logger = get_logger(__name__)


class OllamaService:
    """Service for interacting with Ollama local models"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama service

        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def check_health(self) -> bool:
        """
        Check if Ollama service is running

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in Ollama

        Returns:
            List of available models
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("models", [])
                    return []
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def pull_model(self, model_name: str) -> AsyncGenerator[str, None]:
        """
        Pull a model from Ollama registry

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
                                    yield progress["status"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield f"Error: {str(e)}"

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Generate chat completion with Ollama

        Args:
            model: Model name to use
            messages: List of chat messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Yields:
            Generated text chunks
        """
        try:
            # Prepare request data
            data = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {"temperature": temperature},
            }

            if max_tokens:
                data["options"]["num_predict"] = max_tokens

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if not stream:
                        # Non-streaming response
                        result = await response.json()
                        if "message" in result:
                            yield result["message"]["content"]
                    else:
                        # Streaming response
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    if "message" in chunk:
                                        content = chunk["message"].get("content", "")
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue

        except Exception as e:
            logger.error(f"Ollama chat completion failed: {e}")
            yield f"Error: {str(e)}"

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        Generate text completion with Ollama (non-chat endpoint)

        Args:
            model: Model name to use
            prompt: Input prompt
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Yields:
            Generated text chunks
        """
        try:
            data = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {"temperature": temperature},
            }

            if system:
                data["system"] = system

            if max_tokens:
                data["options"]["num_predict"] = max_tokens

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=data,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if not stream:
                        result = await response.json()
                        if "response" in result:
                            yield result["response"]
                    else:
                        async for line in response.content:
                            if line:
                                try:
                                    chunk = json.loads(line)
                                    if "response" in chunk:
                                        yield chunk["response"]
                                except json.JSONDecodeError:
                                    continue

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            yield f"Error: {str(e)}"

    @staticmethod
    def format_for_ollama(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Format messages for Ollama chat API

        Args:
            messages: Messages in standard format

        Returns:
            Messages formatted for Ollama
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Ollama uses 'user', 'assistant', and 'system' roles
            if role in ["user", "assistant", "system"]:
                formatted.append({"role": role, "content": content})
            elif role == "human":
                formatted.append({"role": "user", "content": content})
            elif role == "ai":
                formatted.append({"role": "assistant", "content": content})

        return formatted


# Singleton instance
_ollama_service: Optional[OllamaService] = None


def get_ollama_service(base_url: str = "http://localhost:11434") -> OllamaService:
    """
    Get or create Ollama service instance

    Args:
        base_url: Base URL for Ollama API

    Returns:
        OllamaService instance
    """
    global _ollama_service
    if _ollama_service is None:
        _ollama_service = OllamaService(base_url)
    return _ollama_service
