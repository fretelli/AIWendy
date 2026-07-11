"""Remove the legacy AgentOS, chat, Agent Matrix, and execution schema.

Revision ID: 021
Revises: 020
"""

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


LEGACY_TABLES = (
    "execution_confirmations",
    "execution_orders",
    "ghost_trades",
    "sandbox_executions",
    "agent_memories",
    "agent_executions",
    "agent_events",
    "chat_attachments",
    "chat_messages",
    "chat_sessions",
    "risk_settings",
    "backtest_runs",
    "strategy_hypotheses",
    "review_lessons",
    "investment_decisions",
    "investment_memos",
    "investment_briefs",
    "workflow_versions",
    "agent_prompt_versions",
)


def upgrade() -> None:
    # Keep these as separate statements: asyncpg rejects multiple commands in a
    # prepared statement. CASCADE removes constraints owned by the legacy stack.
    for table in LEGACY_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade() -> None:
    raise RuntimeError("Migration 021 permanently removes the legacy Agent stack")
