"""Persist Agent interaction modes.

Revision ID: 024
Revises: 023
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    statements = (
        "ALTER TABLE agent_platform_sessions ADD COLUMN IF NOT EXISTS interaction_mode VARCHAR(20) NOT NULL DEFAULT 'ask'",
        "ALTER TABLE agent_platform_runs ADD COLUMN IF NOT EXISTS interaction_mode VARCHAR(20) NOT NULL DEFAULT 'ask'",
        "ALTER TABLE agent_platform_sessions ADD CONSTRAINT ck_agent_platform_sessions_interaction_mode CHECK (interaction_mode IN ('ask', 'research', 'plan'))",
        "ALTER TABLE agent_platform_runs ADD CONSTRAINT ck_agent_platform_runs_interaction_mode CHECK (interaction_mode IN ('ask', 'research', 'plan'))",
    )
    for statement in statements:
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 024 is not reversible")
