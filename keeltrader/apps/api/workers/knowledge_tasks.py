"""Knowledge base ingestion/search tasks (Celery)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import Task
from sqlalchemy import and_, select

from core.cache import get_redis_client
from core.cache_keys import knowledge_search_key
from core.database import SessionLocal
from core.logging import get_logger
from core.task_events import publish_task_event
from domain.knowledge.chunking import chunk_text
from domain.knowledge.models import KnowledgeChunk, KnowledgeDocument
from domain.user.models import User
from infrastructure.llm.router import get_llm_router
from workers.celery_app import celery_app

logger = get_logger(__name__)


def _invalidate_user_knowledge_caches(user_id: str) -> None:
    try:
        redis_client = get_redis_client()
        for key in redis_client.scan_iter(match=f"kb:*:{user_id}:*"):
            redis_client.delete(key)
    except Exception:
        return


def _choose_embedding_provider(llm_router, preferred: Optional[str] = None):
    preferred_name = (preferred or "").strip().lower() or None
    if preferred_name:
        provider = llm_router.providers.get(preferred_name)
        if provider is not None:
            return preferred_name, provider

    provider = llm_router.providers.get("openai") or llm_router.providers.get("ollama")
    if provider is None:
        return None, None
    return ("openai" if llm_router.providers.get("openai") else "ollama"), provider


class KnowledgeTask(Task):
    """Base task for knowledge base operations."""

    def _get_db(self):
        return SessionLocal()


@celery_app.task(bind=True, base=KnowledgeTask)
def ingest_knowledge_document(
    self,
    document_id: str,
    user_id: str,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """Chunk + embed a knowledge document and persist chunks into pgvector."""
    task_id = self.request.id
    db = self._get_db()
    try:
        publish_task_event(
            task_id, {"task_id": task_id, "state": "STARTED", "ready": False}
        )
        doc_uuid = UUID(document_id)
        user_uuid = UUID(user_id)

        doc = (
            db.query(KnowledgeDocument)
            .filter(
                and_(
                    KnowledgeDocument.id == doc_uuid,
                    KnowledgeDocument.user_id == user_uuid,
                    KnowledgeDocument.deleted_at.is_(None),
                )
            )
            .first()
        )
        if doc is None:
            return {"status": "error", "error": "Document not found"}

        user = db.query(User).filter(User.id == user_uuid).first()
        if user is None:
            return {"status": "error", "error": "User not found"}

        chunks = chunk_text(doc.content)
        if not chunks:
            return {
                "status": "error",
                "error": "Document content is empty after cleaning",
            }

        publish_task_event(
            task_id,
            {
                "task_id": task_id,
                "state": "CHUNKED",
                "ready": False,
                "total_chunks": len(chunks),
            },
        )

        llm_router = get_llm_router(user=user)
        provider_name, provider = _choose_embedding_provider(
            llm_router, embedding_provider
        )
        if provider is None or provider_name is None:
            return {
                "status": "error",
                "error": "No embedding provider available (configure OpenAI or start Ollama)",
            }

        if overwrite:
            db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == doc_uuid
            ).delete(synchronize_session=False)
            db.commit()

        embeddings: List[List[float]] = []
        for idx, chunk in enumerate(chunks):
            emb = _run_async(provider.embed(chunk, model=embedding_model))
            if not emb:
                raise RuntimeError("Failed to generate embeddings")
            embeddings.append(emb)
            if (idx + 1) % 3 == 0 or (idx + 1) == len(chunks):
                publish_task_event(
                    task_id,
                    {
                        "task_id": task_id,
                        "state": "EMBEDDING",
                        "ready": False,
                        "processed_chunks": idx + 1,
                        "total_chunks": len(chunks),
                    },
                )

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.add(
                KnowledgeChunk(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    project_id=doc.project_id,
                    chunk_index=idx,
                    content=chunk,
                    embedding_vector=emb,
                    embedding_dim=len(emb),
                    embedding_model=embedding_model,
                    embedding_provider=provider_name,
                )
            )

        doc.chunk_count = len(chunks)
        doc.updated_at = datetime.utcnow()
        db.commit()

        _invalidate_user_knowledge_caches(user_id)
        logger.info(
            "kb_ingest_done",
            user_id=user_id,
            document_id=document_id,
            chunks=len(chunks),
            provider=provider_name,
            dim=len(embeddings[0]) if embeddings else None,
        )
        payload = {
            "status": "success",
            "document_id": document_id,
            "chunks": len(chunks),
            "provider": provider_name,
            "embedding_dim": len(embeddings[0]) if embeddings else None,
        }
        publish_task_event(
            task_id,
            {
                "task_id": task_id,
                "state": "SUCCESS",
                "ready": True,
                "successful": True,
                "result": payload,
            },
        )
        return payload

    except Exception as e:
        db.rollback()
        logger.error(
            "kb_ingest_failed", user_id=user_id, document_id=document_id, error=str(e)
        )
        publish_task_event(
            task_id,
            {
                "task_id": task_id,
                "state": "FAILURE",
                "ready": True,
                "successful": False,
                "error": str(e),
            },
        )
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, base=KnowledgeTask)
def semantic_search(
    self,
    query: str,
    user_id: str,
    top_k: int = 5,
    project_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Semantic search against the knowledge base (pgvector cosine)."""
    db = self._get_db()
    try:
        query_text = (query or "").strip()
        if not query_text:
            return {"status": "error", "error": "query is required"}

        user_uuid = UUID(user_id)
        project_uuid = UUID(project_id) if project_id else None

        cache_key = knowledge_search_key(user_id, project_id, top_k, query_text)
        try:
            cached = get_redis_client().get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        user = db.query(User).filter(User.id == user_uuid).first()
        if user is None:
            return {"status": "error", "error": "User not found"}

        llm_router = get_llm_router(user=user)
        provider_name, provider = _choose_embedding_provider(llm_router, None)
        if provider is None or provider_name is None:
            return {
                "status": "error",
                "error": "No embedding provider available (configure OpenAI or start Ollama)",
            }

        query_embedding = _run_async(provider.embed(query_text, model=None))
        if not query_embedding:
            return {"status": "error", "error": "Failed to generate query embedding"}

        dim = len(query_embedding)
        distance = KnowledgeChunk.embedding_vector.cosine_distance(query_embedding)
        conditions = [
            KnowledgeChunk.user_id == user_uuid,
            KnowledgeChunk.embedding_dim == dim,
            KnowledgeChunk.embedding_vector.isnot(None),
            KnowledgeDocument.user_id == user_uuid,
            KnowledgeDocument.deleted_at.is_(None),
        ]
        if project_uuid is not None:
            conditions.append(KnowledgeChunk.project_id == project_uuid)
            conditions.append(KnowledgeDocument.project_id == project_uuid)

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument.title, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(and_(*conditions))
            .order_by(distance)
            .limit(max(1, min(int(top_k or 5), 20)))
        )
        rows = db.execute(stmt).all()

        results = [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "document_title": title,
                "score": max(0.0, 1.0 - float(dist)),
                "content": chunk.content,
            }
            for chunk, title, dist in rows
        ]

        payload = {
            "status": "success",
            "query": query_text,
            "provider": provider_name,
            "embedding_dim": dim,
            "results": results,
            "count": len(results),
        }
        try:
            get_redis_client().setex(cache_key, 60, json.dumps(payload))
        except Exception:
            pass
        return payload

    except Exception as e:
        logger.error("kb_search_failed", user_id=user_id, error=str(e))
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


def _run_async(awaitable):
    """Run an async call from a Celery worker process."""
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("Async call cannot run inside an active event loop")
