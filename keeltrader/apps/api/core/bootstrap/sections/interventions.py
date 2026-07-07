from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from core.logging import get_logger

logger = get_logger(__name__)

async def ensure_interventions_schema(conn: AsyncConnection) -> None:
    # Trading interventions + checklists
    await conn.execute(
        text(
            """
            DO $$ BEGIN
                CREATE TYPE interventionaction AS ENUM (
                    'block_trade',
                    'warn_user',
                    'require_confirmation',
                    'suggest_alternative',
                    'none'
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
                CREATE TYPE interventionreason AS ENUM (
                    'revenge_trading_detected',
                    'overtrading_detected',
                    'excessive_risk',
                    'emotional_state_poor',
                    'rule_violation',
                    'position_size_too_large',
                    'daily_loss_limit_reached',
                    'checklist_incomplete'
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
            CREATE TABLE IF NOT EXISTS pre_trade_checklists (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                is_required BOOLEAN DEFAULT FALSE NOT NULL,
                items JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS pre_trade_checklist_completions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                checklist_id UUID NOT NULL REFERENCES pre_trade_checklists(id) ON DELETE CASCADE,
                journal_id UUID REFERENCES journals(id) ON DELETE SET NULL,
                responses JSONB NOT NULL,
                all_required_completed BOOLEAN NOT NULL,
                completed_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_pre_trade_checklists_user ON pre_trade_checklists(user_id);"
        )
    )
    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_pre_trade_checklist_completions_user ON pre_trade_checklist_completions(user_id);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS trading_interventions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reason interventionreason NOT NULL,
                action interventionaction NOT NULL,
                message TEXT NOT NULL,
                details JSONB,
                user_acknowledged BOOLEAN DEFAULT FALSE NOT NULL,
                user_proceeded BOOLEAN DEFAULT FALSE NOT NULL,
                user_notes TEXT,
                gate_token UUID,
                gate_expires_at TIMESTAMPTZ,
                gate_used_at TIMESTAMPTZ,
                journal_id UUID REFERENCES journals(id) ON DELETE SET NULL,
                triggered_at TIMESTAMPTZ DEFAULT NOW(),
                acknowledged_at TIMESTAMPTZ
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_trading_interventions_user_triggered ON trading_interventions(user_id, triggered_at);"
        )
    )

    await conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS trading_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                trades_count INTEGER DEFAULT 0 NOT NULL,
                session_pnl INTEGER DEFAULT 0 NOT NULL,
                max_daily_loss_limit INTEGER,
                max_trades_per_day INTEGER,
                enforce_trade_block BOOLEAN DEFAULT FALSE NOT NULL,
                gate_timeout_minutes INTEGER DEFAULT 15 NOT NULL,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                ended_at TIMESTAMPTZ
            );
            """
        )
    )

    await conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_trading_sessions_user_active ON trading_sessions(user_id, is_active);"
        )
    )
