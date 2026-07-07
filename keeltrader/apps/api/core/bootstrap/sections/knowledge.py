from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_knowledge_schema(conn: AsyncConnection) -> None:
    # Knowledge base (documents + chunks)
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                title VARCHAR(255) NOT NULL,
                source_type VARCHAR(50) DEFAULT 'text',
                source_name TEXT,
                content TEXT NOT NULL,
                metadata JSONB DEFAULT '{}'::jsonb,
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_kb_documents_user_project_created ON knowledge_documents(user_id, project_id, created_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_kb_documents_user_title ON knowledge_documents(user_id, title);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding_vector vector,
                embedding_dim INTEGER,
                embedding_model VARCHAR(100),
                embedding_provider VARCHAR(50),
                token_count INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_kb_chunks_document_index ON knowledge_chunks(document_id, chunk_index);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_kb_chunks_user_project_created ON knowledge_chunks(user_id, project_id, created_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_kb_chunks_user_project_dim ON knowledge_chunks(user_id, project_id, embedding_dim);"
        )
    )

    # Ensure the vector column exists for older schemas
    await conn.execute(
        text(
            "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector;"
        )
    )

    # Partial ANN indexes per common embedding dims.
    #
    # Note: pgvector requires a fixed-dimension vector type for ivfflat/hnsw indexes.
    # Our schema uses `vector` without a fixed dimension to support multiple providers/models,
    # so we build expression indexes that cast to a fixed dimension and guard with a WHERE clause.
    # If index creation fails (e.g., older pgvector, inconsistent data), we log and continue.
    for dim, lists in ((1536, 100), (768, 50)):
        stmt = f"""
            CREATE INDEX IF NOT EXISTS ix_kb_chunks_embedding_vector_cosine_{dim}
            ON knowledge_chunks
            USING ivfflat ((embedding_vector::vector({dim})) vector_cosine_ops)
            WITH (lists = {lists})
            WHERE embedding_dim = {dim} AND embedding_vector IS NOT NULL;
        """
        try:
            async with conn.begin_nested():
                await conn.execute(text(stmt))
        except Exception as e:
            logger.warning(
                "Skipping knowledge_chunks ivfflat index creation",
                embedding_dim=dim,
                error=str(e),
            )
