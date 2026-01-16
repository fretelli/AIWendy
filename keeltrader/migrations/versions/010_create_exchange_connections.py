"""Create exchange_connections table

Revision ID: 010
Revises: 009
Create Date: 2026-01-15

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum type for exchange types
    op.execute(
        "CREATE TYPE exchangetype AS ENUM ('binance', 'okx', 'bybit', 'coinbase', 'kraken')"
    )

    # Create exchange_connections table
    op.create_table(
        "exchange_connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exchange_type", sa.Enum('binance', 'okx', 'bybit', 'coinbase', 'kraken', name='exchangetype'), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("api_secret_encrypted", sa.Text(), nullable=False),
        sa.Column("passphrase_encrypted", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_testnet", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index(
        "idx_exchange_connections_user_id",
        "exchange_connections",
        ["user_id"],
    )
    op.create_index(
        "idx_exchange_connections_user_exchange",
        "exchange_connections",
        ["user_id", "exchange_type"],
    )


def downgrade():
    # Drop table
    op.drop_table("exchange_connections")

    # Drop enum type
    op.execute("DROP TYPE exchangetype")
