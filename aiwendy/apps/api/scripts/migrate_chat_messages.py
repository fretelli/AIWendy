"""
Migration script to add missing columns to chat_messages table.

Run this script once to add the missing columns.
"""

import asyncio

from core.database import engine
from core.logging import get_logger
from sqlalchemy import text

logger = get_logger(__name__)


async def migrate_chat_messages():
    """Add missing columns to chat_messages table."""

    migrations = [
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS message_metadata JSON;
        """,
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS detected_emotions JSON;
        """,
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS detected_patterns JSON;
        """,
    ]

    async with engine.begin() as conn:
        for i, migration_sql in enumerate(migrations, 1):
            try:
                logger.info(f"Running migration {i}/{len(migrations)}...")
                await conn.execute(text(migration_sql))
                logger.info(f"Migration {i} completed successfully")
            except Exception as e:
                logger.error(f"Migration {i} failed: {str(e)}")
                raise

    logger.info("All migrations completed successfully!")


async def main():
    """Main entry point."""
    try:
        logger.info("Starting chat_messages table migration...")
        await migrate_chat_messages()
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
