"""Add roundtable session settings and message attachments

Revision ID: 009
Revises: 008
Create Date: 2026-01-10

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    # roundtable_sessions: session-level LLM + KB settings
    op.add_column(
        "roundtable_sessions", sa.Column("llm_config_id", sa.String(100), nullable=True)
    )
    op.add_column(
        "roundtable_sessions", sa.Column("llm_provider", sa.String(50), nullable=True)
    )
    op.add_column(
        "roundtable_sessions", sa.Column("llm_model", sa.String(200), nullable=True)
    )
    op.add_column(
        "roundtable_sessions", sa.Column("llm_temperature", sa.Float(), nullable=True)
    )
    op.add_column(
        "roundtable_sessions", sa.Column("llm_max_tokens", sa.Integer(), nullable=True)
    )

    op.add_column(
        "roundtable_sessions",
        sa.Column("kb_timing", sa.String(20), nullable=True, server_default="off"),
    )
    op.add_column(
        "roundtable_sessions",
        sa.Column("kb_top_k", sa.Integer(), nullable=True, server_default="5"),
    )
    op.add_column(
        "roundtable_sessions",
        sa.Column(
            "kb_max_candidates", sa.Integer(), nullable=True, server_default="400"
        ),
    )

    # roundtable_messages: attachments metadata
    op.add_column(
        "roundtable_messages", sa.Column("attachments", sa.JSON(), nullable=True)
    )


def downgrade():
    op.drop_column("roundtable_messages", "attachments")

    op.drop_column("roundtable_sessions", "kb_max_candidates")
    op.drop_column("roundtable_sessions", "kb_top_k")
    op.drop_column("roundtable_sessions", "kb_timing")

    op.drop_column("roundtable_sessions", "llm_max_tokens")
    op.drop_column("roundtable_sessions", "llm_temperature")
    op.drop_column("roundtable_sessions", "llm_model")
    op.drop_column("roundtable_sessions", "llm_provider")
    op.drop_column("roundtable_sessions", "llm_config_id")
