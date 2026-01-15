"""Create report tables

Revision ID: 005
Revises: 004
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    # Create reports table
    op.create_table(
        "reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "report_type",
            sa.Enum(
                "daily", "weekly", "monthly", "quarterly", "yearly", name="reporttype"
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("subtitle", sa.String(500), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        # Statistics
        sa.Column("total_trades", sa.Integer(), default=0),
        sa.Column("winning_trades", sa.Integer(), default=0),
        sa.Column("losing_trades", sa.Integer(), default=0),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("total_pnl", sa.Float(), default=0.0),
        sa.Column("avg_pnl", sa.Float(), nullable=True),
        sa.Column("max_profit", sa.Float(), nullable=True),
        sa.Column("max_loss", sa.Float(), nullable=True),
        # Psychological metrics
        sa.Column("avg_mood_before", sa.Float(), nullable=True),
        sa.Column("avg_mood_after", sa.Float(), nullable=True),
        sa.Column("mood_improvement", sa.Float(), nullable=True),
        # Trading patterns
        sa.Column("top_mistakes", sa.JSON(), default=list),
        sa.Column("top_successes", sa.JSON(), default=list),
        sa.Column("improvements", sa.JSON(), default=list),
        # AI insights
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("ai_recommendations", sa.JSON(), default=list),
        sa.Column("key_insights", sa.JSON(), default=list),
        sa.Column("action_items", sa.JSON(), default=list),
        # Coach insights
        sa.Column("coach_notes", sa.JSON(), default=dict),
        sa.Column("primary_coach_id", sa.String(50), nullable=True),
        # Report settings
        sa.Column("is_public", sa.Boolean(), default=False),
        sa.Column("is_archived", sa.Boolean(), default=False),
        # Generation metadata
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "generating",
                "completed",
                "failed",
                "sent",
                name="reportstatus",
            ),
            default="pending",
        ),
        sa.Column("generation_time", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        # Email/notification status
        sa.Column("email_sent", sa.Boolean(), default=False),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create indexes for reports
    op.create_index("ix_reports_user_type", "reports", ["user_id", "report_type"])
    op.create_index(
        "ix_reports_user_period", "reports", ["user_id", "period_start", "period_end"]
    )
    op.create_index("ix_reports_status", "reports", ["status"])

    # Create report_schedules table
    op.create_table(
        "report_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
        ),
        # Schedule settings
        sa.Column("daily_enabled", sa.Boolean(), default=True),
        sa.Column("daily_time", sa.String(5), default="21:00"),
        sa.Column("weekly_enabled", sa.Boolean(), default=True),
        sa.Column("weekly_day", sa.Integer(), default=0),
        sa.Column("weekly_time", sa.String(5), default="18:00"),
        sa.Column("monthly_enabled", sa.Boolean(), default=True),
        sa.Column("monthly_day", sa.Integer(), default=1),
        sa.Column("monthly_time", sa.String(5), default="18:00"),
        # Notification preferences
        sa.Column("email_notification", sa.Boolean(), default=True),
        sa.Column("in_app_notification", sa.Boolean(), default=True),
        # Report preferences
        sa.Column("include_charts", sa.Boolean(), default=True),
        sa.Column("include_ai_analysis", sa.Boolean(), default=True),
        sa.Column("include_coach_feedback", sa.Boolean(), default=True),
        # Language and timezone
        sa.Column("language", sa.String(5), default="zh"),
        sa.Column("timezone", sa.String(50), default="Asia/Shanghai"),
        # Status
        sa.Column("is_active", sa.Boolean(), default=True),
        # Last generation times
        sa.Column("last_daily_generated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_weekly_generated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_monthly_generated", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create report_templates table
    op.create_table(
        "report_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "report_type",
            sa.Enum(
                "daily", "weekly", "monthly", "quarterly", "yearly", name="reporttype"
            ),
            nullable=False,
        ),
        # Template structure
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("charts", sa.JSON(), nullable=False),
        # AI prompts
        sa.Column("summary_prompt", sa.Text(), nullable=True),
        sa.Column("analysis_prompt", sa.Text(), nullable=True),
        sa.Column("recommendation_prompt", sa.Text(), nullable=True),
        # Style settings
        sa.Column("theme", sa.String(50), default="default"),
        sa.Column("color_scheme", sa.JSON(), nullable=True),
        # Access control
        sa.Column("is_default", sa.Boolean(), default=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("is_premium", sa.Boolean(), default=False),
        # Timestamps
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create index for report_templates
    op.create_index(
        "ix_report_templates_type", "report_templates", ["report_type", "is_active"]
    )


def downgrade():
    # Drop indexes
    op.drop_index("ix_report_templates_type", table_name="report_templates")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_user_period", table_name="reports")
    op.drop_index("ix_reports_user_type", table_name="reports")

    # Drop tables
    op.drop_table("report_templates")
    op.drop_table("report_schedules")
    op.drop_table("reports")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS reporttype")
    op.execute("DROP TYPE IF EXISTS reportstatus")
