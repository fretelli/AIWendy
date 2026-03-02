"""Add trading_mode column to exchange_connections.

Supports spot vs swap (perpetual futures) trading mode per connection.
Coinbase and Kraken are spot-only exchanges.

Revision ID: 013
Revises: 012
Create Date: 2026-03-02

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    # Create ENUM type
    tradingmode = sa.Enum("spot", "swap", name="tradingmode")
    tradingmode.create(op.get_bind(), checkfirst=True)

    # Add column with server default
    op.add_column(
        "exchange_connections",
        sa.Column(
            "trading_mode",
            sa.Enum("spot", "swap", name="tradingmode"),
            nullable=False,
            server_default="swap",
        ),
    )

    # Backfill: Coinbase and Kraken are spot-only
    op.execute(
        "UPDATE exchange_connections SET trading_mode = 'spot' "
        "WHERE exchange_type IN ('coinbase', 'kraken')"
    )


def downgrade():
    op.drop_column("exchange_connections", "trading_mode")
    op.execute("DROP TYPE IF EXISTS tradingmode")
