"""Add per-user Research Cloud connections.

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "research_cloud_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("client_id", sa.String(length=100)),
        sa.Column("api_key_encrypted", sa.Text()),
        sa.Column("key_prefix", sa.String(length=64)),
        sa.Column("scopes", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("plan_code", sa.String(length=100)),
        sa.Column("pending_device_code_encrypted", sa.Text()),
        sa.Column("user_code", sa.String(length=32)),
        sa.Column("verification_uri", sa.String(length=500)),
        sa.Column("device_expires_at", sa.DateTime(timezone=True)),
        sa.Column("cloud_auto_context", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("connected_at", sa.DateTime(timezone=True)),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_research_cloud_connections_user_id"),
    )
    op.create_index(
        "ix_research_cloud_connections_user_id",
        "research_cloud_connections",
        ["user_id"],
    )


def downgrade():
    op.drop_index("ix_research_cloud_connections_user_id", table_name="research_cloud_connections")
    op.drop_table("research_cloud_connections")
