"""Add journal tables to database."""

import asyncio
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine
from core.logging import get_logger

logger = get_logger(__name__)


async def add_journal_tables():
    """Create journal tables in database."""

    async with engine.begin() as conn:
        # Ensure UUID generator exists for `gen_random_uuid()`
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto";'))

        # Create journals table
        create_journals_table = """
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

        # Create journal_templates table
        create_templates_table = """
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

        # Create indexes (separate statements for AsyncPG)
        create_indexes = [
            "CREATE INDEX IF NOT EXISTS ix_journals_user_date ON journals(user_id, trade_date)",
            "CREATE INDEX IF NOT EXISTS ix_journals_symbol ON journals(symbol)",
            "CREATE INDEX IF NOT EXISTS ix_journals_result ON journals(result)",
            "CREATE INDEX IF NOT EXISTS ix_journals_user_result ON journals(user_id, result)",
        ]

        try:
            # Create tables
            logger.info("Creating journals table...")
            await conn.execute(text(create_journals_table))

            # Ensure newer columns exist when upgrading an existing database
            await conn.execute(
                text(
                    """
                ALTER TABLE journals
                ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;
            """
                )
            )

            logger.info("Creating journal_templates table...")
            await conn.execute(text(create_templates_table))

            logger.info("Creating indexes...")
            for index_sql in create_indexes:
                await conn.execute(text(index_sql))

            logger.info("Journal tables created successfully")

        except Exception as e:
            logger.error(f"Failed to create journal tables: {e}")
            raise


async def main():
    """Run migration."""
    try:
        await add_journal_tables()
        logger.info("Journal tables migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
