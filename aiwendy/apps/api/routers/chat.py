"""Chat endpoints for coach conversations."""

import asyncio
import json
from datetime import datetime
from typing import AsyncIterator, List, Optional
from uuid import UUID

from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from core.i18n import Locale, get_request_locale, t
from core.logging import get_logger
from domain.coach.models import ChatMessage as ChatMessageDB
from domain.coach.models import ChatSession, Coach
from domain.knowledge.models import KnowledgeChunk, KnowledgeDocument
from domain.user.models import User
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from infrastructure.llm.base import ImageContent, LLMConfig
from infrastructure.llm.base import Message as LLMMessage
from infrastructure.llm.base import MessageContent
from infrastructure.llm.factory import create_llm_provider, llm_factory
from infrastructure.llm.router import get_llm_router
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = get_logger(__name__)
encryption = get_encryption_service()


class MessageAttachment(BaseModel):
    """Attachment in a chat message."""

    id: str
    type: str  # 'image', 'audio', 'pdf', 'word', 'excel', 'ppt', 'text', 'code', 'file'
    fileName: str
    fileSize: int
    mimeType: str
    url: str
    base64Data: Optional[str] = None  # For images to send to LLM
    extractedText: Optional[str] = None  # For documents
    transcription: Optional[str] = None  # For audio


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str
    content: str
    attachments: Optional[List[MessageAttachment]] = None


class ChatRequest(BaseModel):
    """Chat request model."""

    coach_id: str
    session_id: Optional[UUID] = None
    messages: List[ChatMessage]
    stream: bool = True
    use_knowledge_base: bool = False
    knowledge_top_k: int = 5
    knowledge_max_candidates: int = 400
    config_id: Optional[str] = None  # User LLM config to use (from /llm-config)
    provider: Optional[str] = None  # 'openai', 'anthropic', 'ollama'
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


def _get_user_llm_config(user: User, config_id: str) -> Optional[dict]:
    if not user.api_keys_encrypted:
        return None
    configs = user.api_keys_encrypted.get("llm_configs") or []
    for cfg in configs:
        if cfg.get("id") == config_id:
            return cfg
    return None


def _decrypt_maybe(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        decrypted = encryption.decrypt(value)
        return decrypted or None
    except Exception:
        # Legacy/plain values (or mismatched key) - treat as plaintext
        return value


def _clean_base_url(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def _clean_str(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def _choose_preferred_model(
    models: list[str], provider_hint: Optional[str]
) -> Optional[str]:
    cleaned: list[str] = []
    seen = set()
    for item in models:
        if not isinstance(item, str):
            continue
        item_clean = _clean_str(item)
        if not item_clean:
            continue
        if item_clean in seen:
            continue
        seen.add(item_clean)
        cleaned.append(item_clean)

    if not cleaned:
        return None

    preferred: list[str]
    if provider_hint == "anthropic":
        preferred = [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-2.1",
        ]
    elif provider_hint == "ollama":
        preferred = [
            "llama3.2:latest",
            "llama3:latest",
        ]
    else:
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

    prefixes = []
    if provider_hint == "anthropic":
        prefixes = ["claude-"]
    elif provider_hint == "ollama":
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

    for model in cleaned:
        if model.lower() == "aqa":
            continue
        return model

    return cleaned[0]


def _build_provider_from_llm_config(cfg: dict):
    provider_type = cfg.get("provider_type")
    if not provider_type:
        raise ValueError("provider_type is required")

    api_key = _decrypt_maybe(cfg.get("api_key"))
    base_url = _clean_base_url(cfg.get("base_url"))

    if provider_type == "custom":
        cfg_copy = cfg.copy()
        cfg_copy["api_key"] = api_key
        return (
            llm_factory.create_custom_provider_from_dict(cfg_copy),
            provider_type,
            cfg,
        )

    provider = create_llm_provider(
        provider=provider_type,
        api_key=api_key,
        base_url=base_url,
        model=cfg.get("default_model") or None,
    )
    return provider, provider_type, cfg


async def _retrieve_kb_context(
    session: AsyncSession,
    current_user: User,
    project_id: Optional[UUID],
    query_text: str,
    top_k: int = 5,
    max_candidates: int = 400,
) -> list[dict]:
    query_text = (query_text or "").strip()
    if not query_text:
        return []

    llm_router = get_llm_router(user=current_user)
    provider_order: list[str] = []
    if "openai" in llm_router.providers:
        provider_order.append("openai")
    if "ollama" in llm_router.providers:
        provider_order.append("ollama")
    # 添加支持 embedding 的 custom provider
    for name, provider in llm_router.providers.items():
        if name not in ("openai", "ollama", "anthropic"):
            # 检查 custom provider 是否支持 embedding
            if hasattr(provider, "config") and getattr(
                provider.config, "supports_embeddings", False
            ):
                provider_order.append(name)

    for provider_name in provider_order:
        provider = llm_router.providers.get(provider_name)
        if provider is None:
            continue

        try:
            query_embedding = await provider.embed(query_text, model=None)
            if not query_embedding:
                continue
        except Exception as e:
            logger.warning(f"KB embedding failed with {provider_name}: {e}")
            continue

        dim = len(query_embedding)
        distance = KnowledgeChunk.embedding_vector.cosine_distance(query_embedding)
        conditions = [
            KnowledgeChunk.user_id == current_user.id,
            KnowledgeChunk.embedding_dim == dim,
            KnowledgeChunk.embedding_vector.isnot(None),
            KnowledgeDocument.user_id == current_user.id,
            KnowledgeDocument.deleted_at.is_(None),
        ]
        if project_id is not None:
            conditions.append(KnowledgeChunk.project_id == project_id)
            conditions.append(KnowledgeDocument.project_id == project_id)

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(and_(*conditions))
            .order_by(distance)
            .limit(max(1, min(top_k, 20)))
        )

        rows = (await session.execute(stmt)).all()
        if not rows:
            continue

        return [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "document_title": title,
                "score": max(0.0, 1.0 - float(dist)),
                "content": chunk.content,
            }
            for chunk, title, dist in rows
        ]

    return []


async def stream_llm_response(
    messages: List[LLMMessage],
    config: LLMConfig,
    user: Optional[User] = None,
    provider: Optional[str] = None,
    locale: Locale = "en",
) -> AsyncIterator[str]:
    """Stream LLM response with SSE format."""
    try:
        # Create user-specific router if user is provided
        llm_router = get_llm_router(user=user)

        # Get the streaming response from LLM
        stream = await llm_router.chat_stream_with_fallback(
            messages=messages, config=config, preferred_provider=provider
        )

        # Stream the response chunks
        async for chunk in stream:
            # Format as Server-Sent Events
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            await asyncio.sleep(0.01)  # Small delay for smooth streaming

        # Send completion signal
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(
            f"Error in streaming response: {str(e)}\n"
            f"Type: {type(e).__name__}\n"
            f"Traceback:\n{error_traceback}"
        )
        error_msg = {"error": t("errors.internal", locale)}
        yield f"data: {json.dumps(error_msg)}\n\n"


@router.post("")
@router.post("/")
async def chat_with_coach(
    request: ChatRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Chat with a coach."""
    locale: Locale = get_request_locale(http_request)
    try:
        chat_session: Optional[ChatSession] = None
        if request.session_id:
            result = await session.execute(
                select(ChatSession).where(
                    ChatSession.id == request.session_id,
                    ChatSession.user_id == current_user.id,
                )
            )
            chat_session = result.scalar_one_or_none()
            if not chat_session:
                raise HTTPException(
                    status_code=404, detail=t("errors.chat_session_not_found", locale)
                )
            if chat_session.coach_id != request.coach_id:
                raise HTTPException(
                    status_code=400,
                    detail=t("errors.chat_coach_mismatch", locale),
                )

        selected_provider = None
        selected_provider_type: Optional[str] = None
        selected_cfg: Optional[dict] = None

        if request.config_id:
            cfg = _get_user_llm_config(current_user, request.config_id)
            if not cfg:
                raise HTTPException(
                    status_code=404,
                    detail=t("errors.llm_configuration_not_found", locale),
                )
            if cfg.get("is_active") is False:
                raise HTTPException(
                    status_code=400,
                    detail=t("errors.llm_configuration_inactive", locale),
                )
            try:
                selected_provider, selected_provider_type, selected_cfg = (
                    _build_provider_from_llm_config(cfg)
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"Failed to build provider from config: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=400,
                    detail=t(
                        "errors.llm_configuration_use_failed", locale, detail=str(e)
                    ),
                )

        # Create user-specific router
        llm_router = get_llm_router(user=current_user)

        # Check if LLM providers are available
        if not selected_provider and not llm_router.providers:
            # Raise error if no providers configured
            logger.error(f"No LLM providers configured for user {current_user.email}")
            raise HTTPException(
                status_code=500,
                detail=t("errors.no_llm_providers_configured", locale),
            )

        # Convert messages to LLM format (with multimodal support)
        llm_messages = []
        for msg in request.messages:
            if msg.attachments:
                # Build multimodal content
                content_parts: List[MessageContent] = []

                # Add text content first
                if msg.content.strip():
                    content_parts.append(MessageContent(type="text", text=msg.content))

                # Add extracted text from documents and audio
                extra_context = []
                for att in msg.attachments:
                    if att.type == "image" and att.base64Data:
                        # Add image content for vision models
                        content_parts.append(
                            MessageContent(
                                type="image_url",
                                image_url=ImageContent(url=att.base64Data),
                            )
                        )
                    elif att.extractedText:
                        # Add extracted document text as context
                        extra_context.append(
                            f"[{t('attachments.file', locale)}: {att.fileName}]\n{att.extractedText}"
                        )
                    elif att.transcription:
                        # Add audio transcription as context
                        extra_context.append(
                            f"[{t('attachments.audio_transcript', locale)}: {att.fileName}]\n{att.transcription}"
                        )

                # If there's extra context from documents/audio, add it as text
                if extra_context:
                    context_text = "\n\n---\n\n".join(extra_context)
                    section = t("attachments.section", locale)
                    if content_parts and content_parts[0].type == "text":
                        # Append to existing text content
                        content_parts[0] = MessageContent(
                            type="text",
                            text=f"{content_parts[0].text}\n\n{section}:\n{context_text}",
                        )
                    else:
                        # Insert text content at beginning
                        content_parts.insert(
                            0,
                            MessageContent(
                                type="text", text=f"{section}:\n{context_text}"
                            ),
                        )

                # If we have multimodal content, use content list
                if len(content_parts) > 1 or (
                    len(content_parts) == 1 and content_parts[0].type == "image_url"
                ):
                    llm_messages.append(
                        LLMMessage(role=msg.role, content=content_parts)
                    )
                elif content_parts:
                    # Just text, use simple content
                    llm_messages.append(
                        LLMMessage(
                            role=msg.role, content=content_parts[0].text or msg.content
                        )
                    )
                else:
                    llm_messages.append(LLMMessage(role=msg.role, content=msg.content))
            else:
                llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

        # Add system message for coach personality (from DB)
        resolved_coach_id = (request.coach_id or "").strip() or "wendy"
        if resolved_coach_id == "default":
            resolved_coach_id = "wendy"

        coach_result = await session.execute(
            select(Coach).where(Coach.id == resolved_coach_id, Coach.is_active == True)
        )
        coach = coach_result.scalar_one_or_none()

        if coach and not coach.is_public and coach.created_by != current_user.id:
            raise HTTPException(
                status_code=403, detail=t("errors.access_denied", locale)
            )

        default_prompt = (
            "You are Wendy, an AI trading psychology performance coach inspired by "
            "Wendy Rhoades from 'Billions'. You are insightful, direct, and focused on "
            "helping traders overcome psychological barriers and improve their performance. "
            "Be supportive but also challenging when needed. Focus on mindset, discipline, "
            "and emotional control in trading."
        )
        system_message = LLMMessage(
            role="system",
            content=((coach.system_prompt or "").strip() if coach else default_prompt),
        )
        language_message = LLMMessage(
            role="system",
            content=t("chat.language_instruction", locale),
        )

        # Optional: Knowledge base context (per project)
        if (
            request.use_knowledge_base
            and chat_session is not None
            and (request.knowledge_top_k or 0) > 0
        ):
            last_user_text = next(
                (
                    m.content
                    for m in reversed(request.messages)
                    if m.role == "user" and m.content.strip()
                ),
                "",
            )
            kb_hits = await _retrieve_kb_context(
                session=session,
                current_user=current_user,
                project_id=chat_session.project_id,
                query_text=last_user_text,
                top_k=request.knowledge_top_k,
                max_candidates=request.knowledge_max_candidates,
            )
            if kb_hits:
                context_lines = []
                for i, hit in enumerate(kb_hits, start=1):
                    title_default = "Document" if locale == "en" else "文档"
                    title = hit.get("document_title") or title_default
                    content = (hit.get("content") or "").strip()
                    if len(content) > 1200:
                        content = content[:1200] + "…"
                    context_lines.append(f"[{i}] {title}\n{content}")

                kb_message = LLMMessage(
                    role="system",
                    content=(t("kb.chat_intro", locale) + "\n\n".join(context_lines)),
                )
                llm_messages = [
                    system_message,
                    kb_message,
                    language_message,
                ] + llm_messages
            else:
                llm_messages = [system_message, language_message] + llm_messages
        else:
            llm_messages = [system_message, language_message] + llm_messages

        # Configure LLM settings with request parameters
        requested_model = _clean_str(request.model)
        configured_model = (
            _clean_str(selected_cfg.get("default_model")) if selected_cfg else None
        )

        # Some OpenAI-compatible gateways include internal/placeholder models (e.g. `aqa`) that
        # may exist in `/v1/models` but be unusable unless an admin configures pricing.
        # Only ignore it when it's coming from the saved default (not an explicit user choice).
        if (
            configured_model
            and configured_model.lower() == "aqa"
            and not requested_model
        ):
            configured_model = None

        model = requested_model or configured_model

        if not model and selected_cfg:
            stored_models = selected_cfg.get("available_models") or []
            if isinstance(stored_models, list):
                provider_hint = selected_provider_type or request.provider
                model = _choose_preferred_model(stored_models, provider_hint)

        if not model and selected_provider:
            list_models_fn = getattr(selected_provider, "list_models", None)
            if callable(list_models_fn):
                try:
                    try:
                        provider_models = await list_models_fn(force_refresh=False)
                    except TypeError:
                        provider_models = await list_models_fn()
                except Exception:
                    provider_models = []
                if provider_models:
                    provider_hint = selected_provider_type or request.provider
                    model = _choose_preferred_model(provider_models, provider_hint)

        provider_hint = selected_provider_type or request.provider
        if not model and provider_hint == "custom" and selected_provider is not None:
            model = _clean_str(
                getattr(
                    getattr(selected_provider, "config", None), "default_model", None
                )
            )

        if not model:
            if provider_hint == "ollama":
                model = "llama3.2:latest"  # Default Ollama model
            elif provider_hint == "anthropic":
                model = "claude-3-haiku-20240307"  # Default Anthropic model
            else:
                model = "gpt-4o-mini"  # Default OpenAI model

        if not model:
            raise HTTPException(
                status_code=400,
                detail=t("errors.no_model_specified", locale),
            )

        config = LLMConfig(
            model=model,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1000,
            stream=request.stream,
        )

        if request.stream:
            # Return streaming response
            if selected_provider:

                async def provider_stream():
                    accumulated = ""
                    try:
                        # Persist the latest user message (server-side history) if session_id is provided
                        if chat_session and request.messages:
                            last_user = next(
                                (
                                    m
                                    for m in reversed(request.messages)
                                    if m.role == "user" and m.content.strip()
                                ),
                                None,
                            )
                            if last_user:
                                session.add(
                                    ChatMessageDB(
                                        session_id=chat_session.id,
                                        role="user",
                                        content=last_user.content.strip(),
                                    )
                                )
                                chat_session.message_count = (
                                    chat_session.message_count or 0
                                ) + 1
                                chat_session.updated_at = datetime.utcnow()
                                await session.commit()

                        async for chunk in selected_provider.chat_stream(
                            llm_messages, config
                        ):
                            accumulated += chunk
                            yield f"data: {json.dumps({'content': chunk})}\n\n"
                            await asyncio.sleep(0.01)
                        yield f"data: {json.dumps({'done': True})}\n\n"
                    except Exception as e:
                        import traceback

                        error_traceback = traceback.format_exc()
                        logger.error(
                            f"Error in provider streaming response: {str(e)}\n"
                            f"Type: {type(e).__name__}\n"
                            f"Provider: {selected_provider.__class__.__name__ if selected_provider else 'None'}\n"
                            f"Traceback:\n{error_traceback}"
                        )
                        error_msg = {"error": t("errors.internal", locale)}
                        yield f"data: {json.dumps(error_msg)}\n\n"
                    finally:
                        # Persist assistant message when streaming finishes
                        if chat_session and accumulated.strip():
                            session.add(
                                ChatMessageDB(
                                    session_id=chat_session.id,
                                    role="assistant",
                                    content=accumulated,
                                )
                            )
                            chat_session.message_count = (
                                chat_session.message_count or 0
                            ) + 1
                            chat_session.updated_at = datetime.utcnow()
                            await session.commit()

                return StreamingResponse(
                    provider_stream(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",  # Disable Nginx buffering
                    },
                )

            async def router_stream():
                accumulated = ""
                try:
                    # Persist the latest user message (server-side history) if session_id is provided
                    if chat_session and request.messages:
                        last_user = next(
                            (
                                m
                                for m in reversed(request.messages)
                                if m.role == "user" and m.content.strip()
                            ),
                            None,
                        )
                        if last_user:
                            session.add(
                                ChatMessageDB(
                                    session_id=chat_session.id,
                                    role="user",
                                    content=last_user.content.strip(),
                                )
                            )
                            chat_session.message_count = (
                                chat_session.message_count or 0
                            ) + 1
                            chat_session.updated_at = datetime.utcnow()
                            await session.commit()

                    async for event in stream_llm_response(
                        llm_messages,
                        config,
                        user=current_user,
                        provider=request.provider,
                        locale=locale,
                    ):
                        # Capture assistant content from SSE events
                        try:
                            for line in event.splitlines():
                                line = line.strip()
                                if not line.startswith("data:"):
                                    continue
                                payload = line[5:].strip()
                                if not payload:
                                    continue
                                parsed = json.loads(payload)
                                if isinstance(parsed, dict) and isinstance(
                                    parsed.get("content"), str
                                ):
                                    accumulated += parsed["content"]
                        except Exception:
                            pass

                        yield event
                finally:
                    if chat_session and accumulated.strip():
                        session.add(
                            ChatMessageDB(
                                session_id=chat_session.id,
                                role="assistant",
                                content=accumulated,
                            )
                        )
                        chat_session.message_count = (
                            chat_session.message_count or 0
                        ) + 1
                        chat_session.updated_at = datetime.utcnow()
                        await session.commit()

            return StreamingResponse(
                router_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable Nginx buffering
                },
            )
        else:
            # Return regular response
            if selected_provider:
                response = await selected_provider.chat(llm_messages, config)
            else:
                response = await llm_router.chat_with_fallback(
                    messages=llm_messages,
                    config=config,
                    preferred_provider=request.provider,
                )

            if chat_session and request.messages:
                last_user = next(
                    (
                        m
                        for m in reversed(request.messages)
                        if m.role == "user" and m.content.strip()
                    ),
                    None,
                )
                if last_user:
                    session.add(
                        ChatMessageDB(
                            session_id=chat_session.id,
                            role="user",
                            content=last_user.content.strip(),
                        )
                    )
                    chat_session.message_count = (chat_session.message_count or 0) + 1

                if isinstance(response, str) and response.strip():
                    session.add(
                        ChatMessageDB(
                            session_id=chat_session.id,
                            role="assistant",
                            content=response,
                        )
                    )
                    chat_session.message_count = (chat_session.message_count or 0) + 1

                chat_session.updated_at = datetime.utcnow()
                await session.commit()

            return {
                "response": response,
                "coach_id": request.coach_id,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": str(chat_session.id) if chat_session else None,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.get("/sessions")
async def list_chat_sessions(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List user's chat sessions."""
    # TODO: Implement session listing
    return {"sessions": [], "total": 0}


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get chat session details."""
    # TODO: Implement session retrieval
    return {"session_id": session_id, "messages": []}
