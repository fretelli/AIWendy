"""Remove the standalone Research Cloud connection table.

Revision ID: 022
Revises: 021
"""

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('DROP TABLE IF EXISTS "research_cloud_connections" CASCADE')


def downgrade() -> None:
    raise RuntimeError("Migration 022 permanently removes Research Cloud connections")
