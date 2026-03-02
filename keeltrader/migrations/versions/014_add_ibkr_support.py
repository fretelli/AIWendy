"""Add IBKR support: new exchange type, trading modes, credentials_extra, asset_class.

Revision ID: 014
Revises: 013
Create Date: 2026-03-02

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade():
    # Add IBKR to exchangetype enum
    op.execute("ALTER TYPE exchangetype ADD VALUE IF NOT EXISTS 'ibkr'")

    # Add new trading modes to tradingmode enum
    op.execute("ALTER TYPE tradingmode ADD VALUE IF NOT EXISTS 'stock'")
    op.execute("ALTER TYPE tradingmode ADD VALUE IF NOT EXISTS 'option'")
    op.execute("ALTER TYPE tradingmode ADD VALUE IF NOT EXISTS 'future'")

    # Add credentials_extra JSON column (IBKR-specific: gateway_host, port, client_id, etc.)
    op.add_column(
        "exchange_connections",
        sa.Column("credentials_extra", sa.JSON(), nullable=True),
    )

    # Add asset_class to exchange_trades (stock, option, future, crypto)
    op.add_column(
        "exchange_trades",
        sa.Column("asset_class", sa.String(20), nullable=True, server_default="crypto"),
    )


def downgrade():
    op.drop_column("exchange_trades", "asset_class")
    op.drop_column("exchange_connections", "credentials_extra")
    # Note: PostgreSQL does not support removing values from ENUMs.
    # The enum values 'ibkr', 'stock', 'option', 'future' will remain.
