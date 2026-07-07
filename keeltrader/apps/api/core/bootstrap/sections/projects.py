from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_projects_schema(conn: AsyncConnection) -> None:
    # Projects (workspaces)
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                is_default BOOLEAN DEFAULT FALSE,
                is_archived BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    # Ensure newer columns exist when upgrading an existing database
    await conn.execute(
        text(
            """
            ALTER TABLE projects
            ADD COLUMN IF NOT EXISTS description TEXT,
            ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_projects_user_updated ON projects(user_id, updated_at);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_projects_user_default ON projects(user_id, is_default);"
        )
    )
