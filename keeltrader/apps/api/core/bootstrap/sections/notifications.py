from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_notifications_schema(conn: AsyncConnection) -> None:
    # Notifications
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE notificationtype AS ENUM (
                    'pattern_detected',
                    'risk_alert',
                    'daily_summary',
                    'weekly_report',
                    'trade_reminder',
                    'goal_achieved',
                    'rule_violation'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE notificationchannel AS ENUM ('push', 'email', 'sms', 'in_app');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE notificationpriority AS ENUM ('low', 'normal', 'high', 'urgent');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS device_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                token VARCHAR(500) NOT NULL UNIQUE,
                platform VARCHAR(20) NOT NULL,
                device_name VARCHAR(200),
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                last_used_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_device_tokens_user_id ON device_tokens(user_id);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_device_tokens_token ON device_tokens(token);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                type notificationtype NOT NULL,
                title VARCHAR(200) NOT NULL,
                body TEXT NOT NULL,
                data JSON,
                channel notificationchannel NOT NULL,
                priority notificationpriority DEFAULT 'normal' NOT NULL,
                is_sent BOOLEAN DEFAULT FALSE NOT NULL,
                is_read BOOLEAN DEFAULT FALSE NOT NULL,
                sent_at TIMESTAMPTZ,
                read_at TIMESTAMPTZ,
                error_message TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
            );
            """
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);"
        )
    )
