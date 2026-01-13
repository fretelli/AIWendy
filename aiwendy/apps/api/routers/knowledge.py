"""Knowledge base endpoints (documents + retrieval)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.cache_keys import knowledge_search_key
from core.cache_service import get_cache_service
from core.database import get_session
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.knowledge.chunking import chunk_text
from domain.knowledge.models import KnowledgeChunk, KnowledgeDocument
from domain.user.models import User
from infrastructure.llm.router import get_llm_router

logger = get_logger(__name__)
router = APIRouter()


class CreateDocumentRequest(BaseModel):
    project_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source_type: str = Field("text", max_length=50)
    source_name: Optional[str] = Field(None, max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_provider: Optional[str] = Field(
        None, description="openai/ollama (optional)"
    )
    embedding_model: Optional[str] = None


class DocumentResponse(BaseModel):
    id: UUID
    project_id: Optional[UUID]
    title: str
    source_type: str
    source_name: Optional[str]
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    score: float
    content: str


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    project_id: Optional[UUID] = Query(None),
    include_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    conditions = [KnowledgeDocument.user_id == current_user.id]
    if project_id is not None:
        conditions.append(KnowledgeDocument.project_id == project_id)
    if not include_deleted:
        conditions.append(KnowledgeDocument.deleted_at.is_(None))

    result = await session.execute(
        select(KnowledgeDocument)
        .where(and_(*conditions))
        .order_by(KnowledgeDocument.updated_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def create_document(
    request: CreateDocumentRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale = get_request_locale(http_request)
    title = request.title.strip()
    content = request.content.strip()
    if not title or not content:
        raise HTTPException(
            status_code=400, detail=t("errors.title_and_content_required", locale)
        )

    chunks = chunk_text(content)
    if not chunks:
        raise HTTPException(
            status_code=400, detail=t("errors.content_empty_after_cleaning", locale)
        )

    llm_router = get_llm_router(user=current_user)
    preferred_provider = (request.embedding_provider or "").strip().lower() or None

    provider_name: Optional[str] = None
    provider = None
    if preferred_provider:
        provider = llm_router.providers.get(preferred_provider)
        provider_name = preferred_provider if provider else None

    if provider is None:
        # Default preference: OpenAI first, then Ollama, then custom providers with embedding support
        provider = llm_router.providers.get("openai") or llm_router.providers.get(
            "ollama"
        )
        provider_name = (
            "openai"
            if llm_router.providers.get("openai")
            else ("ollama" if llm_router.providers.get("ollama") else None)
        )

        # 如果 openai/ollama 都没有，尝试找支持 embedding 的 custom provider
        if provider is None:
            for name, p in llm_router.providers.items():
                if name not in ("openai", "ollama", "anthropic"):
                    if hasattr(p, "config") and getattr(
                        p.config, "supports_embeddings", False
                    ):
                        provider = p
                        provider_name = name
                        break

    if provider is None or provider_name is None:
        raise HTTPException(
            status_code=400, detail=t("errors.no_embedding_provider", locale)
        )

    # Create document
    doc = KnowledgeDocument(
        user_id=current_user.id,
        project_id=request.project_id,
        title=title,
        source_type=request.source_type,
        source_name=request.source_name,
        content=content,
        metadata_=request.metadata or {},
        chunk_count=0,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    embedding_model = request.embedding_model
    embeddings: List[List[float]] = []
    for chunk in chunks:
        emb = await provider.embed(chunk, model=embedding_model)
        if not emb:
            raise HTTPException(
                status_code=500, detail=t("errors.failed_generate_embeddings", locale)
            )
        embeddings.append(emb)

    # Persist chunks
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        chunk_kwargs: Dict[str, Any] = {
            "document_id": doc.id,
            "user_id": current_user.id,
            "project_id": request.project_id,
            "chunk_index": idx,
            "content": chunk,
            "embedding_vector": emb,
            "embedding_dim": len(emb),
            "embedding_model": embedding_model,
            "embedding_provider": provider_name,
        }
        session.add(KnowledgeChunk(**chunk_kwargs))

    doc.chunk_count = len(chunks)
    doc.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(doc)
    logger.info(
        "kb_document_created",
        user_id=str(current_user.id),
        document_id=str(doc.id),
        chunks=len(chunks),
    )
    return doc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    http_request: Request,
    hard_delete: bool = Query(False),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale = get_request_locale(http_request)
    result = await session.execute(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=404, detail=t("errors.document_not_found", locale)
        )

    if hard_delete:
        await session.delete(doc)
    else:
        doc.deleted_at = datetime.utcnow()
        doc.updated_at = datetime.utcnow()

    await session.commit()
    return None


@router.get("/search", response_model=List[SearchResult])
async def search_knowledge(
    http_request: Request,
    q: str = Query(..., min_length=1),
    project_id: Optional[UUID] = Query(None),
    limit: int = Query(5, ge=1, le=20),
    max_candidates: int = Query(500, ge=50, le=2000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    locale = get_request_locale(http_request)
    query_text = q.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail=t("errors.query_required", locale))

    cache = get_cache_service()
    cache_key = knowledge_search_key(
        str(current_user.id),
        str(project_id) if project_id else None,
        limit,
        query_text,
    )
    cached = await cache.get_async(cache_key)
    if isinstance(cached, list):
        return cached

    llm_router = get_llm_router(user=current_user)
    provider_order = []
    if "openai" in llm_router.providers:
        provider_order.append("openai")
    if "ollama" in llm_router.providers:
        provider_order.append("ollama")
    # 添加支持 embedding 的 custom provider
    for name, provider in llm_router.providers.items():
        if name not in ("openai", "ollama", "anthropic"):
            if hasattr(provider, "config") and getattr(
                provider.config, "supports_embeddings", False
            ):
                provider_order.append(name)

    if not provider_order:
        raise HTTPException(
            status_code=400, detail=t("errors.no_embedding_provider", locale)
        )

    best_results: List[SearchResult] = []

    for provider_name in provider_order:
        provider = llm_router.providers.get(provider_name)
        if provider is None:
            continue

        query_embedding = await provider.embed(query_text, model=None)
        if not query_embedding:
            continue

        dim = len(query_embedding)
        conditions = [
            KnowledgeChunk.user_id == current_user.id,
            KnowledgeChunk.embedding_dim == dim,
        ]
        if project_id is not None:
            conditions.append(KnowledgeChunk.project_id == project_id)

        distance = KnowledgeChunk.embedding_vector.cosine_distance(query_embedding)
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(
                and_(
                    *conditions,
                    KnowledgeDocument.deleted_at.is_(None),
                    KnowledgeChunk.embedding_vector.isnot(None),
                )
            )
            .order_by(distance)
            .limit(limit)
        )

        rows = (await session.execute(stmt)).all()
        if not rows:
            continue

        best_results = [
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                document_title=doc_title,
                score=max(0.0, 1.0 - float(dist)),
                content=chunk.content,
            )
            for chunk, doc_title, dist in rows
        ]
        break

    payload = [r.model_dump(mode="json") for r in best_results]
    await cache.set_async(cache_key, payload, ttl=60)
    return payload
