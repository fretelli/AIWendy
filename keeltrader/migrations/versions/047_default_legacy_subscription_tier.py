"""Give the retained legacy subscription column a database default.

Revision ID: 047
Revises: 046
"""

from alembic import op

revision = "047"
down_revision = "046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The current research-only User model intentionally does not map the
    # retired subscription fields. PostgreSQL must therefore supply the
    # retained NOT NULL column when a new user registers.
    op.execute(
        "ALTER TABLE users ALTER COLUMN subscription_tier "
        "SET DEFAULT 'free'::subscriptiontier"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN subscription_tier DROP DEFAULT")
