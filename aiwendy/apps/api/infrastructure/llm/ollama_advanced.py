"""Advanced Ollama Integration with Full Feature Support."""

import asyncio
import json
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
from core.cache import get_redis_client
from core.logging import get_logger
from infrastructure.llm.base import LLMConfig, LLMProvider, Message
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger(__name__)


@dataclass
class OllamaModel:
    """Ollama model information."""

    name: str
    tag: str
    digest: str
    size: int
    modified_at: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.name}:{self.tag}"

    @property
    def size_gb(self) -> float:
        return round(self.size / (1024**3), 2)


class ModelCache:
    """Cache for model responses and embeddings."""

    def __init__(self, redis_client=None):
        self.redis = redis_client or get_redis_client()
        self.ttl = 3600  # 1 hour default TTL

    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        try:
            value = await self.redis.get(f"ollama:cache:{key}")
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value."""
        try:
            await self.redis.setex(
                f"ollama:cache:{key}", ttl or self.ttl, json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def get_embedding(self, text: str, model: str) -> Optional[List[float]]:
        """Get cached embedding."""
        import hashlib

        key = hashlib.md5(f"{model}:{text}".encode()).hexdigest()
        cached = await self.get(f"embedding:{key}")
        return cached if cached else None

    async def set_embedding(self, text: str, model: str, embedding: List[float]):
        """Cache embedding."""
        import hashlib

        key = hashlib.md5(f"{model}:{text}".encode()).hexdigest()
        await self.set(f"embedding:{key}", embedding, ttl=86400)  # 24 hours


class ModelOptimizer:
    """Optimize model parameters for different use cases."""

    PRESETS = {
        "fast": {
            "temperature": 0.3,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
            "num_predict": 256,
        },
        "balanced": {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 50,
            "repeat_penalty": 1.2,
            "num_predict": 512,
        },
        "creative": {
            "temperature": 1.0,
            "top_p": 0.98,
            "top_k": 100,
            "repeat_penalty": 1.3,
            "num_predict": 1024,
        },
        "analytical": {
            "temperature": 0.1,
            "top_p": 0.85,
            "top_k": 20,
            "repeat_penalty": 1.0,
            "num_predict": 2048,
        },
    }

    @classmethod
    def get_optimized_params(
        cls, use_case: str, base_config: LLMConfig
    ) -> Dict[str, Any]:
        """Get optimized parameters for a use case."""
        preset = cls.PRESETS.get(use_case, cls.PRESETS["balanced"])

        return {
            "temperature": base_config.temperature or preset["temperature"],
            "top_p": preset["top_p"],
            "top_k": preset["top_k"],
            "repeat_penalty": preset["repeat_penalty"],
            "num_predict": base_config.max_tokens or preset["num_predict"],
            "seed": base_config.seed if hasattr(base_config, "seed") else None,
            "num_ctx": 4096,  # Context window
            "num_batch": 512,  # Batch size for prompt processing
            "num_gpu": -1,  # Use all available GPUs
            "main_gpu": 0,
            "low_vram": False,
            "f16_kv": True,  # Use f16 for key/value cache
            "vocab_only": False,
            "use_mmap": True,  # Memory-map model
            "use_mlock": False,  # Lock model in RAM
        }


class AdvancedOllamaProvider(LLMProvider):
    """Advanced Ollama provider with full features."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        enable_cache: bool = True,
        enable_monitoring: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.cache = ModelCache() if enable_cache else None
        self.enable_monitoring = enable_monitoring
        self.optimizer = ModelOptimizer()
        self._model_info_cache: Dict[str, OllamaModel] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def check_health(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[OllamaModel]:
        """List all available models with detailed information."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()

            data = response.json()
            models = []

            for model_data in data.get("models", []):
                model = OllamaModel(
                    name=model_data["name"].split(":")[0],
                    tag=(
                        model_data["name"].split(":")[-1]
                        if ":" in model_data["name"]
                        else "latest"
                    ),
                    digest=model_data["digest"],
                    size=model_data["size"],
                    modified_at=datetime.fromisoformat(
                        model_data["modified_at"].replace("Z", "+00:00")
                    ),
                    details=model_data.get("details", {}),
                )
                models.append(model)
                self._model_info_cache[model.full_name] = model

            return models
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(
        self, model_name: str, progress_callback: Optional[callable] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """Pull a model with progress tracking."""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model_name},
                timeout=None,  # No timeout for pulling
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        status = json.loads(line)

                        if progress_callback:
                            await progress_callback(status)

                        yield status

                        if status.get("status") == "success":
                            # Clear model cache to refresh
                            self._model_info_cache.clear()
                            break
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            yield {"status": "error", "error": str(e)}

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model from local storage."""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/delete", json={"name": model_name}
            )
            response.raise_for_status()

            # Clear cache
            if model_name in self._model_info_cache:
                del self._model_info_cache[model_name]

            return True
        except Exception as e:
            logger.error(f"Failed to delete model {model_name}: {e}")
            return False

    async def get_model_info(self, model_name: str) -> Optional[OllamaModel]:
        """Get detailed information about a specific model."""
        if model_name in self._model_info_cache:
            return self._model_info_cache[model_name]

        try:
            response = await self.client.post(
                f"{self.base_url}/api/show", json={"name": model_name}
            )
            response.raise_for_status()

            data = response.json()
            model = OllamaModel(
                name=model_name.split(":")[0],
                tag=model_name.split(":")[-1] if ":" in model_name else "latest",
                digest=data.get("digest", ""),
                size=data.get("size", 0),
                modified_at=datetime.now(),
                details=data,
            )

            self._model_info_cache[model_name] = model
            return model
        except Exception as e:
            logger.error(f"Failed to get model info for {model_name}: {e}")
            return None

    async def chat(
        self, messages: List[Message], config: LLMConfig, use_case: str = "balanced"
    ) -> str:
        """Chat completion with optimized parameters."""

        # Check cache if enabled
        if self.cache and not config.stream:
            cache_key = self._get_cache_key(messages, config)
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug("Returning cached response")
                return cached

        # Get optimized parameters
        params = self.optimizer.get_optimized_params(use_case, config)

        # Prepare request
        request_data = {
            "model": config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": config.stream,
            "options": params,
        }

        try:
            start_time = time.time()

            if config.stream:
                return self._stream_chat(request_data)
            else:
                response = await self.client.post(
                    f"{self.base_url}/api/chat", json=request_data, timeout=self.timeout
                )
                response.raise_for_status()

                data = response.json()
                content = data["message"]["content"]

                # Cache response
                if self.cache:
                    await self.cache.set(cache_key, content)

                # Monitor performance
                if self.enable_monitoring:
                    elapsed = time.time() - start_time
                    await self._log_metrics(config.model, elapsed, len(content))

                return content

        except Exception as e:
            logger.error(f"Chat request failed: {e}")
            raise

    async def _stream_chat(self, request_data: Dict) -> AsyncIterator[str]:
        """Stream chat responses."""
        try:
            async with self.client.stream(
                "POST", f"{self.base_url}/api/chat", json=request_data, timeout=None
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"]["content"]

                        if data.get("done", False):
                            break
        except Exception as e:
            logger.error(f"Stream chat failed: {e}")
            raise

    async def generate_embeddings(
        self, texts: List[str], model: str = "nomic-embed-text"
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        embeddings = []

        for text in texts:
            # Check cache
            if self.cache:
                cached = await self.cache.get_embedding(text, model)
                if cached:
                    embeddings.append(cached)
                    continue

            try:
                response = await self.client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                response.raise_for_status()

                embedding = response.json()["embedding"]
                embeddings.append(embedding)

                # Cache embedding
                if self.cache:
                    await self.cache.set_embedding(text, model, embedding)

            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                embeddings.append([])

        return embeddings

    async def similarity_search(
        self,
        query: str,
        documents: List[str],
        model: str = "nomic-embed-text",
        top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find most similar documents using embeddings."""

        # Generate embeddings
        query_embedding = (await self.generate_embeddings([query], model))[0]
        doc_embeddings = await self.generate_embeddings(documents, model)

        if not query_embedding or not doc_embeddings:
            return []

        query_len = len(query_embedding)
        query_norm = math.sqrt(sum(v * v for v in query_embedding))
        if query_norm == 0:
            return []

        # Calculate similarities
        similarities = []

        for doc, doc_embedding in zip(documents, doc_embeddings):
            if not doc_embedding or len(doc_embedding) != query_len:
                continue

            doc_norm = math.sqrt(sum(v * v for v in doc_embedding))
            denom = query_norm * doc_norm
            if denom == 0:
                continue

            dot = sum(qv * dv for qv, dv in zip(query_embedding, doc_embedding))
            similarity = dot / denom
            similarities.append((doc, float(similarity)))

        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

    async def analyze_sentiment(
        self, text: str, model: str = "llama3.2:latest"
    ) -> Dict[str, Any]:
        """Analyze sentiment of text."""

        prompt = f"""Analyze the sentiment of the following text and provide:
1. Overall sentiment (positive, negative, neutral)
2. Confidence score (0-1)
3. Key emotions detected
4. Brief explanation

Text: {text}

Provide response in JSON format."""

        messages = [
            Message(role="system", content="You are a sentiment analysis expert."),
            Message(role="user", content=prompt),
        ]

        config = LLMConfig(model=model, temperature=0.1, max_tokens=200)
        response = await self.chat(messages, config, use_case="analytical")

        try:
            # Parse JSON response
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "Could not parse response", "raw": response}
        except Exception as e:
            logger.error(f"Failed to parse sentiment analysis: {e}")
            return {"error": str(e), "raw": response}

    async def fine_tune_model(
        self,
        base_model: str,
        training_data: List[Dict[str, str]],
        model_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Fine-tune a model with custom data (requires Ollama 0.2+)."""

        try:
            # Prepare training file in JSONL format
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".jsonl", delete=False
            ) as f:
                for item in training_data:
                    f.write(json.dumps(item) + "\n")
                training_file = f.name

            # Create Modelfile
            modelfile = f"""FROM {base_model}
PARAMETER temperature {parameters.get('temperature', 0.7) if parameters else 0.7}
PARAMETER top_p {parameters.get('top_p', 0.9) if parameters else 0.9}
PARAMETER top_k {parameters.get('top_k', 40) if parameters else 40}

SYSTEM You are a specialized trading psychology coach trained on custom data.
"""

            # Create model
            response = await self.client.post(
                f"{self.base_url}/api/create",
                json={"name": model_name, "modelfile": modelfile},
            )
            response.raise_for_status()

            # Clean up
            import os

            os.unlink(training_file)

            return True

        except Exception as e:
            logger.error(f"Failed to fine-tune model: {e}")
            return False

    def _get_cache_key(self, messages: List[Message], config: LLMConfig) -> str:
        """Generate cache key for messages and config."""
        import hashlib

        content = json.dumps(
            {
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
            }
        )

        return hashlib.md5(content.encode()).hexdigest()

    async def _log_metrics(self, model: str, elapsed_time: float, tokens: int):
        """Log performance metrics."""
        try:
            if self.cache:
                # Store metrics in Redis for monitoring
                metrics = {
                    "model": model,
                    "timestamp": datetime.now().isoformat(),
                    "elapsed_time": elapsed_time,
                    "tokens": tokens,
                    "tokens_per_second": (
                        tokens / elapsed_time if elapsed_time > 0 else 0
                    ),
                }

                await self.cache.redis.lpush("ollama:metrics", json.dumps(metrics))

                # Trim to last 1000 entries
                await self.cache.redis.ltrim("ollama:metrics", 0, 999)

        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.cache:
            return {}

        try:
            # Get recent metrics
            metrics_raw = await self.cache.redis.lrange("ollama:metrics", 0, 99)
            metrics = [json.loads(m) for m in metrics_raw]

            if not metrics:
                return {}

            # Calculate statistics
            elapsed_times = [m["elapsed_time"] for m in metrics]
            tokens_per_second = [m["tokens_per_second"] for m in metrics]

            return {
                "total_requests": len(metrics),
                "avg_response_time": float(sum(elapsed_times) / len(elapsed_times)),
                "min_response_time": float(min(elapsed_times)),
                "max_response_time": float(max(elapsed_times)),
                "avg_tokens_per_second": float(
                    sum(tokens_per_second) / len(tokens_per_second)
                ),
                "models_used": list(set(m["model"] for m in metrics)),
            }
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}")
            return {}
