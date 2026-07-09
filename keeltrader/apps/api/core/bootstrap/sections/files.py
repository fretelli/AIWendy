from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_files_schema(conn: AsyncConnection) -> None:
    """Ensure uploaded file metadata tables exist."""
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                file_name VARCHAR(255) NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                file_category VARCHAR(50) NOT NULL,
                storage_path TEXT NOT NULL UNIQUE,
                thumbnail_base64 TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_uploaded_files_user_created ON uploaded_files(user_id, created_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_uploaded_files_storage_path ON uploaded_files(storage_path);"
        )
    )

