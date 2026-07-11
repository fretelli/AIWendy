"""Add conversational Agent workspace fields.

Revision ID: 023
Revises: 022
"""

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "ALTER TABLE agent_platform_sessions ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE agent_platform_sessions ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ",
        "ALTER TABLE agent_platform_sessions ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ NOT NULL DEFAULT now()",
        "ALTER TABLE agent_platform_messages ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES agent_platform_runs(id) ON DELETE SET NULL",
        "ALTER TABLE agent_platform_messages ADD COLUMN IF NOT EXISTS kind VARCHAR(30) NOT NULL DEFAULT 'message'",
        "ALTER TABLE agent_platform_messages ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'completed'",
        "CREATE INDEX IF NOT EXISTS ix_agent_platform_sessions_activity ON agent_platform_sessions(user_id, is_pinned DESC, last_message_at DESC)",
        "CREATE INDEX IF NOT EXISTS ix_agent_platform_messages_run ON agent_platform_messages(run_id)",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 023 is not reversible")
