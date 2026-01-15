"""Add API key columns to users table."""

import asyncio
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine
from core.logging import get_logger

logger = get_logger(__name__)


async def add_api_key_columns():
    """Add API key columns to users table."""

    async with engine.begin() as conn:
        # Check if columns already exist
        check_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name IN ('openai_api_key', 'anthropic_api_key', 'api_keys_encrypted');
        """

        result = await conn.execute(text(check_query))
        existing_columns = [row[0] for row in result]

        # Add openai_api_key column if not exists
        if "openai_api_key" not in existing_columns:
            logger.info("Adding openai_api_key column to users table")
            await conn.execute(
                text(
                    """
                ALTER TABLE users
                ADD COLUMN openai_api_key TEXT;
            """
                )
            )
            logger.info("Added openai_api_key column")
        else:
            logger.info("Column openai_api_key already exists")

        # Add anthropic_api_key column if not exists
        if "anthropic_api_key" not in existing_columns:
            logger.info("Adding anthropic_api_key column to users table")
            await conn.execute(
                text(
                    """
                ALTER TABLE users
                ADD COLUMN anthropic_api_key TEXT;
            """
                )
            )
            logger.info("Added anthropic_api_key column")
        else:
            logger.info("Column anthropic_api_key already exists")

        # Add api_keys_encrypted column if not exists
        if "api_keys_encrypted" not in existing_columns:
            logger.info("Adding api_keys_encrypted column to users table")
            await conn.execute(
                text(
                    """
                ALTER TABLE users
                ADD COLUMN api_keys_encrypted JSONB DEFAULT '{}';
            """
                )
            )
            logger.info("Added api_keys_encrypted column")
        else:
            logger.info("Column api_keys_encrypted already exists")

        logger.info("API key columns migration completed successfully")


async def main():
    """Run migration."""
    try:
        await add_api_key_columns()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
