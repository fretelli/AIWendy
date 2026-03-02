"""Add Agent Matrix tables: agent_events, agent_executions, ghost_trades,
execution_orders, execution_confirmations, agent_memories, sandbox_executions.
Also add telegram_user_id to users table.

Revision ID: 012
Revises: 011
Create Date: 2026-03-02

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    # Add telegram fields to users table
    op.add_column("users", sa.Column("telegram_user_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("telegram_username", sa.String(100), nullable=True))
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=True)

    # Agent events (Event Sourcing core)
    op.create_table(
        "agent_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("source", sa.String(50)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("agent_id", sa.String(50), nullable=True, index=True),
        sa.Column("payload", postgresql.JSONB, server_default="{}"),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Agent execution audit (every tool call)
    op.create_table(
        "agent_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("tool_name", sa.String(100)),
        sa.Column("tool_params", postgresql.JSONB),
        sa.Column("tool_result", postgresql.JSONB),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Ghost trades (simulated / paper trading)
    op.create_table(
        "ghost_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("entry_price", sa.Float()),
        sa.Column("entry_time", sa.DateTime(timezone=True)),
        sa.Column("exit_price", sa.Float()),
        sa.Column("exit_time", sa.DateTime(timezone=True)),
        sa.Column("position_size", sa.Float()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("take_profit", sa.Float()),
        sa.Column("unrealized_pnl", sa.Float(), server_default="0"),
        sa.Column("realized_pnl", sa.Float()),
        sa.Column("reasoning", sa.Text()),
        sa.Column("status", sa.String(20), server_default="open", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Execution orders (audit trail for real orders)
    op.create_table(
        "execution_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("price", sa.Float()),
        sa.Column("stop_loss", sa.Float()),
        sa.Column("status", sa.String(20), server_default="pending", index=True),
        sa.Column("safety_checks", postgresql.JSONB),
        sa.Column("confirmation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ccxt_order_id", sa.String(100)),
        sa.Column("ccxt_response", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Execution confirmations (Telegram confirmation records)
    op.create_table(
        "execution_confirmations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("execution_orders.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),  # approved/rejected/timeout
        sa.Column("telegram_message_id", sa.BigInteger()),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Agent memories (agentic memory L1-L2)
    op.create_table(
        "agent_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("memory_key", sa.String(200), nullable=False),
        sa.Column("memory_value", postgresql.JSONB, nullable=False),
        sa.Column("memory_layer", sa.String(20), nullable=False, index=True),
        sa.Column("importance", sa.Float(), server_default="0.5"),
        sa.Column("last_accessed", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Unique constraint on agent+user+layer+key
    op.create_index(
        "ix_agent_memories_unique",
        "agent_memories",
        ["agent_id", "user_id", "memory_layer", "memory_key"],
        unique=True,
    )

    # Sandbox execution records
    op.create_table(
        "sandbox_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", sa.String(50), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("language", sa.String(20), server_default="python"),
        sa.Column("data_context", postgresql.JSONB),
        sa.Column("stdout", sa.Text()),
        sa.Column("stderr", sa.Text()),
        sa.Column("exit_code", sa.Integer()),
        sa.Column("output_files", postgresql.JSONB),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("memory_used_mb", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("sandbox_executions")
    op.drop_table("agent_memories")
    op.drop_table("execution_confirmations")
    op.drop_table("execution_orders")
    op.drop_table("ghost_trades")
    op.drop_table("agent_executions")
    op.drop_table("agent_events")
    op.drop_index("ix_users_telegram_user_id", "users")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_user_id")
