"""Create roundtable discussion tables

Revision ID: 007
Revises: 006
Create Date: 2025-01-04

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    # Create coach_presets table
    op.create_table(
        "coach_presets",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("coach_ids", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
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

    # Insert default presets
    op.execute(
        """
        INSERT INTO coach_presets (id, name, description, coach_ids, icon, sort_order, is_active) VALUES
        ('all_stars', '全明星阵容', '5位教练全员参与，多角度全面分析您的交易心理问题', '["wendy", "marcus", "sophia", "alex", "socrates"]', 'stars', 1, true),
        ('rational', '理性派', '数据分析师 + 纪律教练：用数据说话，用执行力解决问题', '["sophia", "marcus"]', 'brain', 2, true),
        ('emotional', '情感派', '共情教练 + 激励大师：情感支持与正能量激励', '["wendy", "alex"]', 'heart', 3, true),
        ('debate', '辩论组', '温和派 vs 严厉派：听取截然不同的观点和建议', '["wendy", "marcus"]', 'swords', 4, true),
        ('philosophers', '哲学家', '苏格拉底式提问 + 深度数据分析：引导您深入思考', '["socrates", "sophia"]', 'lightbulb', 5, true)
    """
    )

    # Create roundtable_sessions table
    op.create_table(
        "roundtable_sessions",
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
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=True,
        ),
        sa.Column(
            "preset_id", sa.String(50), sa.ForeignKey("coach_presets.id"), nullable=True
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("coach_ids", sa.JSON(), nullable=False),
        sa.Column("turn_order", sa.JSON(), nullable=True),
        sa.Column("current_turn", sa.Integer(), nullable=True, default=0),
        sa.Column("message_count", sa.Integer(), nullable=True, default=0),
        sa.Column("round_count", sa.Integer(), nullable=True, default=0),
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

    # Create indexes for roundtable_sessions
    op.create_index(
        "ix_roundtable_sessions_user_created",
        "roundtable_sessions",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_roundtable_sessions_active", "roundtable_sessions", ["is_active"]
    )

    # Create roundtable_messages table
    op.create_table(
        "roundtable_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roundtable_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "coach_id", sa.String(50), sa.ForeignKey("coaches.id"), nullable=True
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("sequence_in_turn", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
        ),
    )

    # Create indexes for roundtable_messages
    op.create_index(
        "ix_roundtable_messages_session_created",
        "roundtable_messages",
        ["session_id", "created_at"],
    )
    op.create_index(
        "ix_roundtable_messages_turn",
        "roundtable_messages",
        ["session_id", "turn_number"],
    )


def downgrade():
    # Drop indexes
    op.drop_index("ix_roundtable_messages_turn", table_name="roundtable_messages")
    op.drop_index(
        "ix_roundtable_messages_session_created", table_name="roundtable_messages"
    )
    op.drop_index("ix_roundtable_sessions_active", table_name="roundtable_sessions")
    op.drop_index(
        "ix_roundtable_sessions_user_created", table_name="roundtable_sessions"
    )

    # Drop tables
    op.drop_table("roundtable_messages")
    op.drop_table("roundtable_sessions")
    op.drop_table("coach_presets")
