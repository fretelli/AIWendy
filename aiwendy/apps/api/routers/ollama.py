"""API routes for Ollama model management."""

import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.auth import get_current_user
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User
from infrastructure.llm.ollama_provider import OllamaProvider

logger = get_logger(__name__)
router = APIRouter()


class OllamaModelInfo(BaseModel):
    """Model information."""

    name: str
    modified_at: str
    size: int
    digest: str


class OllamaHealthResponse(BaseModel):
    """Health check response."""

    healthy: bool
    message: str


class PullModelRequest(BaseModel):
    """Request to pull a model."""

    model_name: str


class ListModelsResponse(BaseModel):
    """Response for list models."""

    models: List[str]
    available: bool


@router.get("/health", response_model=OllamaHealthResponse)
async def check_ollama_health(http_request: Request):
    """Check if Ollama service is running."""
    provider = OllamaProvider()
    is_healthy = await provider.check_health()
    locale = get_request_locale(http_request)

    return OllamaHealthResponse(
        healthy=is_healthy,
        message=(
            t("messages.ollama_service_running", locale)
            if is_healthy
            else t("errors.ollama_not_available", locale)
        ),
    )


@router.get("/models", response_model=ListModelsResponse)
async def list_models():
    """List available models in Ollama."""
    provider = OllamaProvider()

    # Check if service is running
    is_healthy = await provider.check_health()
    if not is_healthy:
        return ListModelsResponse(models=[], available=False)

    models = await provider.list_models()
    return ListModelsResponse(models=models, available=True)


@router.post("/models/pull")
async def pull_model(
    request: PullModelRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """Pull a model from Ollama registry."""
    provider = OllamaProvider()

    # Check if service is running
    is_healthy = await provider.check_health()
    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail=t("errors.ollama_not_available", get_request_locale(http_request)),
        )

    async def generate():
        """Generate SSE stream for model pulling progress."""
        async for status in provider.pull_model(request.model_name):
            # Format as Server-Sent Events
            event_data = json.dumps({"status": status})
            yield f"data: {event_data}\n\n"

        # Send final message
        yield f"data: {json.dumps({'status': 'Complete', 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/recommended-models")
async def get_recommended_models():
    """Get list of recommended models for trading psychology coaching."""
    return {
        "models": [
            {
                "name": "llama3.2:latest",
                "description": "Latest Llama 3.2 model - Fast and capable",
                "size": "3.2GB",
                "recommended": True,
                "use_case": "General coaching and analysis",
            },
            {
                "name": "mistral:latest",
                "description": "Mistral 7B - Efficient and powerful",
                "size": "4.1GB",
                "recommended": True,
                "use_case": "Technical analysis and pattern recognition",
            },
            {
                "name": "phi3:medium",
                "description": "Microsoft Phi-3 Medium - Compact but capable",
                "size": "7.9GB",
                "recommended": False,
                "use_case": "Quick responses and real-time coaching",
            },
            {
                "name": "gemma2:9b",
                "description": "Google Gemma 2 9B - Advanced reasoning",
                "size": "5.4GB",
                "recommended": True,
                "use_case": "Deep analysis and improvement plans",
            },
            {
                "name": "qwen2.5:7b",
                "description": "Qwen 2.5 7B - Multilingual support",
                "size": "4.4GB",
                "recommended": False,
                "use_case": "Multilingual coaching",
            },
            {
                "name": "nomic-embed-text",
                "description": "Embedding model for semantic search",
                "size": "274MB",
                "recommended": True,
                "use_case": "Journal search and similarity",
            },
        ]
    }


@router.post("/test-chat")
async def test_ollama_chat(
    model: str,
    message: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """Test chat with a specific Ollama model."""
    provider = OllamaProvider()
    locale = get_request_locale(http_request)

    # Check if service is running
    is_healthy = await provider.check_health()
    if not is_healthy:
        raise HTTPException(
            status_code=503,
            detail=t("errors.ollama_not_available", locale),
        )

    # Check if model is available
    models = await provider.list_models()
    if model not in models:
        raise HTTPException(
            status_code=404,
            detail=t("errors.ollama_model_not_available", locale, model=model),
        )

    # Create test messages
    from infrastructure.llm.base import LLMConfig, Message

    messages = [
        Message(
            role="system",
            content=t("ollama.test_chat_system_prompt", locale),
        ),
        Message(role="user", content=message),
    ]

    config = LLMConfig(model=model, temperature=0.7, max_tokens=500, stream=False)

    # Get response
    response = await provider.chat(messages, config)

    return {"model": model, "message": message, "response": response}
