"""Add exchange trades, behavior patterns, and intervention tables

Revision ID: 011
Revises: 010
Create Date: 2026-01-20

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "011"
down_revision = "011a"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    op.execute(
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
    op.execute(
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
    op.execute(
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

    exchange_columns = {col["name"] for col in inspector.get_columns("exchange_connections")}
    if "sync_symbols" not in exchange_columns:
        op.execute(
            "ALTER TABLE exchange_connections ADD COLUMN IF NOT EXISTS sync_symbols JSON DEFAULT '[]'::json;"
        )
    if "last_trade_sync_at" not in exchange_columns:
        op.execute(
            "ALTER TABLE exchange_connections ADD COLUMN IF NOT EXISTS last_trade_sync_at TIMESTAMPTZ;"
        )

    if not inspector.has_table("exchange_trades"):
        op.create_table(
            "exchange_trades",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "exchange_connection_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("exchange_connections.id"),
                nullable=False,
            ),
            sa.Column(
                "journal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("journals.id"),
                nullable=True,
            ),
            sa.Column("exchange_trade_id", sa.String(200), nullable=False),
            sa.Column("symbol", sa.String(50), nullable=False),
            sa.Column("side", sa.String(10), nullable=True),
            sa.Column("price", sa.Float(), nullable=True),
            sa.Column("amount", sa.Float(), nullable=True),
            sa.Column("cost", sa.Float(), nullable=True),
            sa.Column("fee_cost", sa.Float(), nullable=True),
            sa.Column("fee_currency", sa.String(20), nullable=True),
            sa.Column("fee_rate", sa.Float(), nullable=True),
            sa.Column("trade_timestamp", sa.DateTime(timezone=True), nullable=True),
            sa.Column("raw", sa.JSON(), nullable=True),
            sa.Column(
                "is_imported", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_exchange_trades_connection_trade_id
        ON exchange_trades(exchange_connection_id, exchange_trade_id);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_exchange_trades_user_time
        ON exchange_trades(user_id, trade_timestamp);
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exchange_trades_symbol ON exchange_trades(symbol);"
    )

    if not inspector.has_table("pre_trade_checklists"):
        op.create_table(
            "pre_trade_checklists",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "is_required", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("items", sa.JSON(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pre_trade_checklists_user ON pre_trade_checklists(user_id);"
    )

    if not inspector.has_table("pre_trade_checklist_completions"):
        op.create_table(
            "pre_trade_checklist_completions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "checklist_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("pre_trade_checklists.id"),
                nullable=False,
            ),
            sa.Column(
                "journal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("journals.id"),
                nullable=True,
            ),
            sa.Column("responses", sa.JSON(), nullable=False),
            sa.Column("all_required_completed", sa.Boolean(), nullable=False),
            sa.Column(
                "completed_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_pre_trade_checklist_completions_user
        ON pre_trade_checklist_completions(user_id);
        """
    )

    if not inspector.has_table("trading_interventions"):
        op.create_table(
            "trading_interventions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "reason",
                sa.Enum(
                    "revenge_trading_detected",
                    "overtrading_detected",
                    "excessive_risk",
                    "emotional_state_poor",
                    "rule_violation",
                    "position_size_too_large",
                    "daily_loss_limit_reached",
                    "checklist_incomplete",
                    name="interventionreason",
                ),
                nullable=False,
            ),
            sa.Column(
                "action",
                sa.Enum(
                    "block_trade",
                    "warn_user",
                    "require_confirmation",
                    "suggest_alternative",
                    "none",
                    name="interventionaction",
                ),
                nullable=False,
            ),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column(
                "user_acknowledged",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
            sa.Column(
                "user_proceeded", sa.Boolean(), nullable=False, server_default="false"
            ),
            sa.Column("user_notes", sa.Text(), nullable=True),
            sa.Column("gate_token", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("gate_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("gate_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "journal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("journals.id"),
                nullable=True,
            ),
            sa.Column(
                "triggered_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_trading_interventions_user_triggered
        ON trading_interventions(user_id, triggered_at);
        """
    )

    if not inspector.has_table("trading_sessions"):
        op.create_table(
            "trading_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column(
                "trades_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("session_pnl", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_daily_loss_limit", sa.Integer(), nullable=True),
            sa.Column("max_trades_per_day", sa.Integer(), nullable=True),
            sa.Column(
                "enforce_trade_block",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
            sa.Column(
                "gate_timeout_minutes",
                sa.Integer(),
                nullable=False,
                server_default="15",
            ),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_trading_sessions_user_active
        ON trading_sessions(user_id, is_active);
        """
    )

    if not inspector.has_table("behavior_patterns"):
        op.create_table(
            "behavior_patterns",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "journal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("journals.id"),
                nullable=True,
            ),
            sa.Column(
                "session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("chat_sessions.id"),
                nullable=True,
            ),
            sa.Column(
                "pattern_type",
                sa.Enum(
                    "revenge_trading",
                    "overtrading",
                    "fear_of_loss",
                    "greed",
                    "fomo",
                    "analysis_paralysis",
                    "confirmation_bias",
                    "anchoring_bias",
                    "emotional_trading",
                    "discipline_breach",
                    name="patterntype",
                ),
                nullable=False,
            ),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("severity", sa.Integer(), nullable=True),
            sa.Column("context", sa.JSON(), nullable=True),
            sa.Column("trigger_conditions", sa.JSON(), nullable=True),
            sa.Column(
                "evidence",
                sa.JSON(),
                nullable=True,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column(
                "related_trades",
                sa.JSON(),
                nullable=True,
                server_default=sa.text("'[]'::json"),
            ),
            sa.Column("intervention_suggested", sa.Text(), nullable=True),
            sa.Column("intervention_accepted", sa.Boolean(), nullable=True),
            sa.Column("intervention_result", sa.Text(), nullable=True),
            sa.Column(
                "detected_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_behavior_patterns_user_type
        ON behavior_patterns(user_id, pattern_type);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_behavior_patterns_detected
        ON behavior_patterns(detected_at);
        """
    )


def downgrade():
    op.drop_index("ix_behavior_patterns_detected", table_name="behavior_patterns")
    op.drop_index("ix_behavior_patterns_user_type", table_name="behavior_patterns")
    op.drop_table("behavior_patterns")

    op.drop_index("ix_trading_sessions_user_active", table_name="trading_sessions")
    op.drop_table("trading_sessions")

    op.drop_index(
        "ix_trading_interventions_user_triggered", table_name="trading_interventions"
    )
    op.drop_table("trading_interventions")

    op.drop_index(
        "ix_pre_trade_checklist_completions_user",
        table_name="pre_trade_checklist_completions",
    )
    op.drop_table("pre_trade_checklist_completions")

    op.drop_index("ix_pre_trade_checklists_user", table_name="pre_trade_checklists")
    op.drop_table("pre_trade_checklists")

    op.drop_index(
        "ix_exchange_trades_connection_trade_id", table_name="exchange_trades"
    )
    op.drop_index("ix_exchange_trades_user_time", table_name="exchange_trades")
    op.drop_index("ix_exchange_trades_symbol", table_name="exchange_trades")
    op.drop_table("exchange_trades")

    op.drop_column("exchange_connections", "last_trade_sync_at")
    op.drop_column("exchange_connections", "sync_symbols")

    op.execute("DROP TYPE patterntype")
    op.execute("DROP TYPE interventionreason")
    op.execute("DROP TYPE interventionaction")
