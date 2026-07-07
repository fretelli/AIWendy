from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_extensions_schema(conn: AsyncConnection) -> None:
    # Ensure UUID generator exists for `gen_random_uuid()`
    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))
    # pgvector extension for embedding search
    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector";'))
