"""Add immutable explicit research context snapshots.

Revision ID: 030
Revises: 029
"""
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TABLE agent_context_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, resource_type VARCHAR(40) NOT NULL, resource_id VARCHAR(120) NOT NULL, field VARCHAR(80), visible_start VARCHAR(32), visible_end VARCHAR(32), selected_point JSONB, source VARCHAR(240) NOT NULL, methodology TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())")
    op.execute("CREATE INDEX ix_agent_context_snapshots_user ON agent_context_snapshots(user_id, created_at DESC)")


def downgrade() -> None:
    raise RuntimeError("Migration 030 is not reversible")
