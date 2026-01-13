#!/usr/bin/env python
"""
Simple database initialization - creates only the users table.

Usage:
    python scripts/init_db_simple.py
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


async def create_users_table():
    """Create users table using raw SQL."""
    settings = get_settings()

    # Create database engine
    engine = create_async_engine(settings.database_url, echo=True, pool_pre_ping=True)

    async with engine.begin() as conn:
        # Ensure UUID generator exists for `gen_random_uuid()`
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))

        # Create ENUM type for subscription_tier if it doesn't exist
        await conn.execute(
            text(
                """
            DO $$ BEGIN
                CREATE TYPE subscriptiontier AS ENUM ('free', 'pro', 'elite', 'enterprise');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """
            )
        )

        # Create users table if it doesn't exist
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                is_email_verified BOOLEAN DEFAULT FALSE,
                email_verification_token VARCHAR(255),
                full_name VARCHAR(255),
                display_name VARCHAR(100),
                avatar_url TEXT,
                bio TEXT,
                timezone VARCHAR(50) DEFAULT 'UTC',
                language VARCHAR(10) DEFAULT 'en',
                trading_types JSON DEFAULT '[]'::json,
                main_concern TEXT,
                preferred_coach_id VARCHAR(50),
                preferred_coach_style VARCHAR(50),
                subscription_tier subscriptiontier DEFAULT 'free' NOT NULL,
                stripe_customer_id VARCHAR(255),
                stripe_subscription_id VARCHAR(255),
                subscription_expires_at TIMESTAMPTZ,
                openai_api_key TEXT,
                anthropic_api_key TEXT,
                api_keys_encrypted JSON DEFAULT '{}'::json,
                notification_preferences JSON DEFAULT '{"email_daily_summary": false, "email_weekly_report": true, "push_notifications": true, "sms_alerts": false}'::json,
                privacy_settings JSON DEFAULT '{"share_analytics": true, "public_profile": false}'::json,
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                last_login_at TIMESTAMPTZ,
                login_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            );
        """
            )
        )

        # Ensure newer columns exist when upgrading an existing database
        await conn.execute(
            text(
                """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS openai_api_key TEXT,
            ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT,
            ADD COLUMN IF NOT EXISTS api_keys_encrypted JSON DEFAULT '{}'::json;
        """
            )
        )

        # Create indexes for users table
        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
        """
            )
        )

        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_users_email_active ON users(email, is_active);
        """
            )
        )

        await conn.execute(
            text(
                """
            CREATE INDEX IF NOT EXISTS ix_users_subscription ON users(subscription_tier, subscription_expires_at);
        """
            )
        )

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
                device_info JSON,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL,
                last_activity_at TIMESTAMPTZ DEFAULT NOW(),
                revoked_at TIMESTAMPTZ
            );
        """
            )
        )

        await conn.execute(
            text(
                """
            ALTER TABLE user_sessions
            ADD COLUMN IF NOT EXISTS device_info JSON;
        """
            )
        )

        # Create indexes for user_sessions table
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
    logger.info("Users table created successfully!")


async def main():
    """Main function."""
    print("=" * 50)
    print("AIWendy - Initialize Database (Simple)")
    print("=" * 50)

    try:
        await create_users_table()
        print("\n✅ Users table created successfully!")
        print("\nYou can now run the user initialization script:")
        print("  python scripts/init_user_simple.py")

    except Exception as e:
        print(f"\n❌ Error creating table: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
