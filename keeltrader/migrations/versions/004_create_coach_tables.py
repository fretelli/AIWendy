"""Create coach tables

Revision ID: 004
Revises: 001
Create Date: 2024-12-30

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "004"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # Create coaches table
    op.create_table(
        "coaches",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column(
            "style",
            sa.Enum(
                "empathetic",
                "disciplined",
                "analytical",
                "motivational",
                "socratic",
                name="coachstyle",
            ),
            nullable=False,
        ),
        sa.Column("personality_traits", sa.JSON(), nullable=True, default=list),
        sa.Column("specialty", sa.JSON(), nullable=True, default=list),
        sa.Column("language", sa.String(10), nullable=True, default="en"),
        sa.Column(
            "llm_provider",
            sa.Enum("openai", "anthropic", "local", "custom", name="llmprovider"),
            nullable=True,
        ),
        sa.Column("llm_model", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=True, default=0.7),
        sa.Column("max_tokens", sa.Integer(), nullable=True, default=2000),
        sa.Column("voice_id", sa.String(100), nullable=True),
        sa.Column("voice_settings", sa.JSON(), nullable=True),
        sa.Column("is_premium", sa.Boolean(), nullable=True, default=False),
        sa.Column("is_public", sa.Boolean(), nullable=True, default=True),
        sa.Column(
            "min_subscription_tier", sa.String(20), nullable=True, default="free"
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("total_sessions", sa.Integer(), nullable=True, default=0),
        sa.Column("total_messages", sa.Integer(), nullable=True, default=0),
        sa.Column("avg_rating", sa.Float(), nullable=True),
        sa.Column("rating_count", sa.Integer(), nullable=True, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("is_default", sa.Boolean(), nullable=True, default=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create indexes for coaches
    op.create_index("ix_coaches_style_active", "coaches", ["style", "is_active"])
    op.create_index("ix_coaches_public_premium", "coaches", ["is_public", "is_premium"])

    # Create chat_sessions table
    op.create_table(
        "chat_sessions",
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
            "coach_id", sa.String(50), sa.ForeignKey("coaches.id"), nullable=False
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("mood_before", sa.Integer(), nullable=True),
        sa.Column("mood_after", sa.Integer(), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=True, default=0),
        sa.Column("total_tokens", sa.Integer(), nullable=True, default=0),
        sa.Column("user_rating", sa.Integer(), nullable=True),
        sa.Column("user_feedback", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )

    # Create indexes for chat_sessions
    op.create_index(
        "ix_chat_sessions_user_created", "chat_sessions", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_chat_sessions_coach_active", "chat_sessions", ["coach_id", "is_active"]
    )

    # Create chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("message_metadata", sa.JSON(), nullable=True),
        sa.Column("detected_emotions", sa.JSON(), nullable=True),
        sa.Column("detected_patterns", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )

    # Create index for chat_messages
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at"],
    )


def downgrade():
    # Drop indexes
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_index("ix_chat_sessions_coach_active", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_created", table_name="chat_sessions")
    op.drop_index("ix_coaches_public_premium", table_name="coaches")
    op.drop_index("ix_coaches_style_active", table_name="coaches")

    # Drop tables
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("coaches")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS coachstyle")
    op.execute("DROP TYPE IF EXISTS llmprovider")
