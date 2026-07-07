from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_journals_schema(conn: AsyncConnection) -> None:
    # Journals (trading journal)
    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS journals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                -- Trade information
                trade_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(20) NOT NULL,
                market VARCHAR(20),
                direction VARCHAR(10) NOT NULL CHECK (direction IN ('long', 'short')),

                -- Entry/Exit
                entry_time TIMESTAMP WITH TIME ZONE,
                entry_price FLOAT,
                position_size FLOAT,
                exit_time TIMESTAMP WITH TIME ZONE,
                exit_price FLOAT,

                -- Results
                result VARCHAR(10) DEFAULT 'open' CHECK (result IN ('win', 'loss', 'breakeven', 'open')),
                pnl_amount FLOAT,
                pnl_percentage FLOAT,

                -- Risk management
                stop_loss FLOAT,
                take_profit FLOAT,
                risk_reward_ratio FLOAT,

                -- Emotions (1-5 scale)
                emotion_before INTEGER CHECK (emotion_before >= 1 AND emotion_before <= 5),
                emotion_during INTEGER CHECK (emotion_during >= 1 AND emotion_during <= 5),
                emotion_after INTEGER CHECK (emotion_after >= 1 AND emotion_after <= 5),

                -- Psychology
                confidence_level INTEGER CHECK (confidence_level >= 1 AND confidence_level <= 5),
                stress_level INTEGER CHECK (stress_level >= 1 AND stress_level <= 5),
                followed_rules BOOLEAN DEFAULT TRUE,
                rule_violations JSONB DEFAULT '[]',

                -- Notes
                setup_description TEXT,
                exit_reason TEXT,
                lessons_learned TEXT,
                notes TEXT,

                -- AI Analysis
                ai_insights TEXT,
                detected_patterns JSONB,

                -- Tags and categories
                tags JSONB DEFAULT '[]',
                strategy_name VARCHAR(100),

                -- Attachments
                screenshots JSONB DEFAULT '[]',

                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP WITH TIME ZONE
            );
            """
        )
    )

    await conn.execute(
        text(
            """
            ALTER TABLE journals
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS journal_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

                -- Template info
                name VARCHAR(100) NOT NULL,
                description TEXT,

                -- Default values
                default_values JSONB NOT NULL,

                -- Usage
                usage_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP WITH TIME ZONE,

                -- Timestamps
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_journals_user_date ON journals(user_id, trade_date);"
        )
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_journals_symbol ON journals(symbol);")
    )
    await conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_journals_result ON journals(result);")
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_journals_user_result ON journals(user_id, result);"
        )
    )

    # Add project grouping to journals when projects exist
    await conn.execute(
        text(
            """
            ALTER TABLE journals
            ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;
            """
        )
    )
    await conn.execute(
        text(
            """
            CREATE INDEX IF NOT EXISTS ix_journals_user_project_date
            ON journals(user_id, project_id, trade_date);
            """
        )
    )
