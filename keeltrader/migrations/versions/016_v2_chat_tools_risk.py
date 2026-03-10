"""v2: Add tool_calls to chat_messages and risk_settings table.

Revision ID: 016
Revises: 015
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tool_calls JSON column to chat_messages (stores tool call data for v2 chat)
    op.add_column(
        'chat_messages',
        sa.Column('tool_calls', postgresql.JSONB(), nullable=True),
    )

    # Create risk_settings table
    op.create_table(
        'risk_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('max_order_value_usd', sa.Float(), nullable=False, server_default='5000'),
        sa.Column('max_daily_loss_usd', sa.Float(), nullable=False, server_default='500'),
        sa.Column('max_positions', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('require_confirmation', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_morning_report', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_evening_report', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_trade_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('push_risk_alerts', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Ensure keeltrader-ai coach exists for v2 sessions
    op.execute("""
        INSERT INTO coaches (id, name, system_prompt, personality, is_active, is_public, description)
        VALUES (
            'keeltrader-ai',
            'KeelTrader AI',
            'You are KeelTrader AI trading assistant.',
            'analytical',
            true,
            true,
            'AI 原生交易助手'
        )
        ON CONFLICT (id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('risk_settings')
    op.drop_column('chat_messages', 'tool_calls')
