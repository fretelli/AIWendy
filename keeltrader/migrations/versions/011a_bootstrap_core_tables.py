"""Bootstrap the historical core tables without importing runtime models.

Revision ID: 011a
Revises: 010
Create Date: 2026-01-20
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "011a"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')
    op.execute(
        "DO $$ BEGIN CREATE TYPE tradedirection AS ENUM ('LONG', 'SHORT'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN CREATE TYPE traderesult AS ENUM ('WIN', 'LOSS', 'BREAKEVEN', 'OPEN'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_projects_user_updated", "projects", ["user_id", "updated_at"])
    op.create_index("ix_projects_user_default", "projects", ["user_id", "is_default"])

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("access_token", sa.Text(), unique=True),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("device_info", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "journals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id")),
        sa.Column("trade_date", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("market", sa.String(20)),
        sa.Column("direction", postgresql.ENUM("LONG", "SHORT", name="tradedirection", create_type=False), nullable=False),
        sa.Column("entry_time", sa.DateTime(timezone=True)),
        sa.Column("entry_price", sa.Float()),
        sa.Column("position_size", sa.Float()),
        sa.Column("exit_time", sa.DateTime(timezone=True)),
        sa.Column("exit_price", sa.Float()),
        sa.Column("result", postgresql.ENUM("WIN", "LOSS", "BREAKEVEN", "OPEN", name="traderesult", create_type=False), server_default="OPEN"),
        sa.Column("pnl_amount", sa.Float()),
        sa.Column("pnl_percentage", sa.Float()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("take_profit", sa.Float()),
        sa.Column("risk_reward_ratio", sa.Float()),
        sa.Column("emotion_before", sa.Integer()),
        sa.Column("emotion_during", sa.Integer()),
        sa.Column("emotion_after", sa.Integer()),
        sa.Column("confidence_level", sa.Integer()),
        sa.Column("stress_level", sa.Integer()),
        sa.Column("followed_rules", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("rule_violations", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("setup_description", sa.Text()),
        sa.Column("exit_reason", sa.Text()),
        sa.Column("lessons_learned", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("ai_insights", sa.Text()),
        sa.Column("detected_patterns", sa.JSON()),
        sa.Column("tags", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("strategy_name", sa.String(100)),
        sa.Column("screenshots", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "journal_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("default_values", sa.JSON(), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_messages.id"), nullable=False),
        sa.Column("attachment_type", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("transcription", sa.Text()),
        sa.Column("thumbnail_base64", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_attachments_message", "chat_attachments", ["message_id"])

    report_type = postgresql.ENUM(
        "daily", "weekly", "monthly", "quarterly", "yearly", name="reporttype", create_type=False
    )
    op.create_table(
        "analysis_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("report_type", report_type, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_trades", sa.Integer(), server_default="0"),
        sa.Column("winning_trades", sa.Integer(), server_default="0"),
        sa.Column("losing_trades", sa.Integer(), server_default="0"),
        sa.Column("breakeven_trades", sa.Integer(), server_default="0"),
        sa.Column("win_rate", sa.Float()),
        sa.Column("profit_factor", sa.Float()),
        sa.Column("sharpe_ratio", sa.Float()),
        sa.Column("max_drawdown", sa.Float()),
        sa.Column("total_pnl", sa.Float()),
        sa.Column("avg_win", sa.Float()),
        sa.Column("avg_loss", sa.Float()),
        sa.Column("best_trade", sa.Float()),
        sa.Column("worst_trade", sa.Float()),
        sa.Column("avg_emotion_score", sa.Float()),
        sa.Column("avg_confidence_score", sa.Float()),
        sa.Column("avg_stress_score", sa.Float()),
        sa.Column("rule_violation_rate", sa.Float()),
        sa.Column("detected_patterns", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("pattern_frequencies", sa.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column("pattern_insights", sa.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column("ai_summary", sa.Text()),
        sa.Column("ai_recommendations", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("ai_strengths", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("ai_weaknesses", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("ai_action_items", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("key_insights", sa.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column("coaching_notes", sa.Text()),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("viewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_analysis_reports_user_type", "analysis_reports", ["user_id", "report_type"])
    op.create_index("ix_analysis_reports_period", "analysis_reports", ["period_start", "period_end"])

    op.create_table(
        "performance_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("metric_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("daily_pnl", sa.Float()),
        sa.Column("daily_trades", sa.Integer(), server_default="0"),
        sa.Column("daily_win_rate", sa.Float()),
        sa.Column("cumulative_pnl", sa.Float()),
        sa.Column("cumulative_trades", sa.Integer(), server_default="0"),
        sa.Column("account_balance", sa.Float()),
        sa.Column("daily_var", sa.Float()),
        sa.Column("daily_max_drawdown", sa.Float()),
        sa.Column("avg_emotion", sa.Float()),
        sa.Column("avg_confidence", sa.Float()),
        sa.Column("rule_violations", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_performance_metrics_user_date", "performance_metrics", ["user_id", "metric_date"])

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("users"):
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "username" in user_columns:
            op.execute("ALTER TABLE users ALTER COLUMN username DROP NOT NULL;")

    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_email_verified BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(255),
        ADD COLUMN IF NOT EXISTS display_name VARCHAR(100),
        ADD COLUMN IF NOT EXISTS bio TEXT,
        ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC',
        ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en',
        ADD COLUMN IF NOT EXISTS trading_types JSON DEFAULT '[]'::json,
        ADD COLUMN IF NOT EXISTS main_concern TEXT,
        ADD COLUMN IF NOT EXISTS preferred_coach_id VARCHAR(50),
        ADD COLUMN IF NOT EXISTS preferred_coach_style VARCHAR(50),
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS openai_api_key TEXT,
        ADD COLUMN IF NOT EXISTS anthropic_api_key TEXT,
        ADD COLUMN IF NOT EXISTS api_keys_encrypted JSON DEFAULT '{}'::json,
        ADD COLUMN IF NOT EXISTS notification_preferences JSON DEFAULT '{}'::json,
        ADD COLUMN IF NOT EXISTS privacy_settings JSON DEFAULT '{}'::json,
        ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email_active ON users(email, is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_subscription ON users(subscription_tier, subscription_expires_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_sessions_access_token ON user_sessions(access_token);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);")
    op.execute("ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_project_created ON chat_sessions(user_id, project_id, created_at);")
    op.execute("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS has_attachments BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reports_user_project_period ON reports(user_id, project_id, period_start);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_journals_user_date ON journals(user_id, trade_date);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_journals_symbol ON journals(symbol);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_journals_result ON journals(result);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_journals_user_project_date ON journals(user_id, project_id, trade_date);")


def downgrade() -> None:
    pass
