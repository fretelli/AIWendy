"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2024-12-27 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute(
        "CREATE TYPE subscriptiontier AS ENUM ('free', 'pro', 'elite', 'enterprise')"
    )
    op.execute(
        "CREATE TYPE moodtype AS ENUM ('very_negative', 'negative', 'neutral', 'positive', 'very_positive')"
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("is_verified", sa.Boolean(), default=False, nullable=False),
        sa.Column(
            "subscription_tier",
            postgresql.ENUM(
                "free", "pro", "elite", "enterprise", name="subscriptiontier"
            ),
            default="free",
            nullable=False,
        ),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", postgresql.JSONB, default=dict, nullable=False),
        sa.Column(
            "notification_settings", postgresql.JSONB, default=dict, nullable=False
        ),
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

    # Create journal_entries table
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "mood",
            postgresql.ENUM(
                "very_negative",
                "negative",
                "neutral",
                "positive",
                "very_positive",
                name="moodtype",
            ),
            nullable=True,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String), default=list, nullable=False),
        sa.Column("is_private", sa.Boolean(), default=True, nullable=False),
        sa.Column("attachments", postgresql.JSONB, default=list, nullable=False),
        sa.Column("metadata", postgresql.JSONB, default=dict, nullable=False),
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
    op.create_index("ix_journal_entries_user_id", "journal_entries", ["user_id"])
    op.create_index("ix_journal_entries_created_at", "journal_entries", ["created_at"])

    # Create mood_analyses table
    op.create_table(
        "mood_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("average_mood", sa.Float(), nullable=False),
        sa.Column("mood_distribution", postgresql.JSONB, nullable=False),
        sa.Column(
            "dominant_emotions",
            postgresql.ARRAY(sa.String),
            default=list,
            nullable=False,
        ),
        sa.Column("triggers", postgresql.JSONB, default=dict, nullable=False),
        sa.Column("insights", sa.Text(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB, default=list, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_mood_analyses_user_id", "mood_analyses", ["user_id"])
    op.create_index(
        "ix_mood_analyses_period", "mood_analyses", ["period_start", "period_end"]
    )

    # Create journal_analyses table
    op.create_table(
        "journal_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "journal_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("journal_entries.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("emotions", postgresql.JSONB, nullable=False),
        sa.Column("themes", postgresql.ARRAY(sa.String), default=list, nullable=False),
        sa.Column("key_insights", postgresql.JSONB, default=list, nullable=False),
        sa.Column("action_items", postgresql.JSONB, default=list, nullable=False),
        sa.Column("metadata", postgresql.JSONB, default=dict, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_journal_analyses_journal_entry_id", "journal_analyses", ["journal_entry_id"]
    )


def downgrade() -> None:
    # Drop tables
    op.drop_table("journal_analyses")
    op.drop_table("mood_analyses")
    op.drop_table("journal_entries")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS moodtype")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
