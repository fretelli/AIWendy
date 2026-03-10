"""Knowledge tools: search_knowledge."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger

logger = get_logger(__name__)


async def search_knowledge(
    session: AsyncSession,
    user_id: UUID,
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """搜索知识库（pgvector RAG）。"""
    from domain.knowledge.models import KnowledgeChunk, KnowledgeDocument

    query = (query or "").strip()
    if not query:
        return {"results": [], "message": "请提供搜索关键词"}

    # Try to get embedding from OpenAI via LiteLLM
    try:
        from openai import AsyncOpenAI
        from config import get_settings

        settings = get_settings()
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url if hasattr(settings, "openai_base_url") else None,
        )
        resp = await client.embeddings.create(
            input=query,
            model="text-embedding-3-large",
        )
        query_embedding = resp.data[0].embedding
    except Exception as e:
        logger.warning("knowledge_embedding_failed", error=str(e))
        return {"results": [], "message": f"Embedding 生成失败: {str(e)}"}

    dim = len(query_embedding)
    distance = KnowledgeChunk.embedding_vector.cosine_distance(query_embedding)
    conditions = [
        KnowledgeChunk.user_id == user_id,
        KnowledgeChunk.embedding_dim == dim,
        KnowledgeChunk.embedding_vector.isnot(None),
        KnowledgeDocument.user_id == user_id,
        KnowledgeDocument.deleted_at.is_(None),
    ]

    stmt = (
        select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(and_(*conditions))
        .order_by(distance)
        .limit(max(1, min(top_k, 20)))
    )

    rows = (await session.execute(stmt)).all()
    if not rows:
        return {"results": [], "message": "未找到相关知识"}

    return {
        "results": [
            {
                "document_title": title,
                "content": chunk.content[:500],
                "score": round(max(0.0, 1.0 - float(dist)), 3),
            }
            for chunk, title, dist in rows
        ],
        "query": query,
    }
