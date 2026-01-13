#!/usr/bin/env python
"""
Create user_sessions table.

Usage:
    python scripts/create_user_sessions_table.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_user_sessions_table():
    """Create user_sessions table."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=True, pool_pre_ping=True)

    async with engine.begin() as conn:
        # Create user_sessions table
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                access_token VARCHAR(500) NOT NULL,
                refresh_token VARCHAR(500) NOT NULL,
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                last_activity_at TIMESTAMPTZ DEFAULT NOW(),
                revoked_at TIMESTAMPTZ
            );
        """
            )
        )

        # Create indexes
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
        """
            )
        )

        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_user_sessions_access_token ON user_sessions(access_token);
        """
            )
        )

        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);
        """
            )
        )

    await engine.dispose()
    logger.info("User sessions table created successfully!")


async def main():
    """Main function."""
    print("=" * 50)
    print("AIWendy - Create User Sessions Table")
    print("=" * 50)

    try:
        await create_user_sessions_table()
        print("\n✅ User sessions table created successfully!")

    except Exception as e:
        print(f"\n❌ Error creating table: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
