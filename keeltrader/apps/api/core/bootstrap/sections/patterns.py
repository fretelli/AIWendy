from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_patterns_schema(conn: AsyncConnection) -> None:
    # Behavior pattern storage
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE patterntype AS ENUM (
                    'revenge_trading',
                    'overtrading',
                    'fear_of_loss',
                    'greed',
                    'fomo',
                    'analysis_paralysis',
                    'confirmation_bias',
                    'anchoring_bias',
                    'emotional_trading',
                    'discipline_breach'
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
            CREATE TABLE IF NOT EXISTS behavior_patterns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                journal_id UUID REFERENCES journals(id) ON DELETE SET NULL,
                session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
                pattern_type patterntype NOT NULL,
                confidence_score FLOAT NOT NULL,
                severity INTEGER,
                context JSONB,
                trigger_conditions JSONB,
                evidence JSONB DEFAULT '[]'::jsonb,
                related_trades JSONB DEFAULT '[]'::jsonb,
                intervention_suggested TEXT,
                intervention_accepted BOOLEAN,
                intervention_result TEXT,
                detected_at TIMESTAMPTZ DEFAULT NOW(),
                resolved_at TIMESTAMPTZ
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_behavior_patterns_user_type ON behavior_patterns(user_id, pattern_type);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_behavior_patterns_detected ON behavior_patterns(detected_at);"
        )
    )
