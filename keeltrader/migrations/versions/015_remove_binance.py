"""Remove binance from exchangetype enum.

Revision ID: 015
Revises: 014
Create Date: 2026-03-06

PostgreSQL does not support DROP VALUE from ENUM directly.
Strategy: create new enum → migrate column → drop old enum → rename.
"""

from alembic import op

# revision identifiers
revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

# The values we want to KEEP (all current values minus 'binance')
_KEEP_VALUES = ("okx", "bybit", "coinbase", "kraken", "ibkr")


def upgrade():
    conn = op.get_bind()

    # Safety check: abort if any rows still reference 'binance'
    result = conn.execute(
        __import__("sqlalchemy").text(
            "SELECT count(*) FROM exchange_connections WHERE exchange_type = 'binance'"
        )
    )
    count = result.scalar()
    if count:
        raise RuntimeError(
            f"Cannot remove 'binance' from enum: {count} row(s) in "
            "exchange_connections still have exchange_type='binance'. "
            "Delete or migrate them first."
        )

    values_sql = ", ".join(f"'{v}'" for v in _KEEP_VALUES)

    # 1. Create new enum type
    op.execute(f"CREATE TYPE exchangetype_new AS ENUM ({values_sql})")

    # 2. Swap column type
    op.execute(
        "ALTER TABLE exchange_connections "
        "ALTER COLUMN exchange_type TYPE exchangetype_new "
        "USING exchange_type::text::exchangetype_new"
    )

    # 3. Drop old enum, rename new
    op.execute("DROP TYPE exchangetype")
    op.execute("ALTER TYPE exchangetype_new RENAME TO exchangetype")


def downgrade():
    # Re-add 'binance' by rebuilding the enum with it included
    all_values = ("binance",) + _KEEP_VALUES
    values_sql = ", ".join(f"'{v}'" for v in all_values)

    op.execute(f"CREATE TYPE exchangetype_old AS ENUM ({values_sql})")
    op.execute(
        "ALTER TABLE exchange_connections "
        "ALTER COLUMN exchange_type TYPE exchangetype_old "
        "USING exchange_type::text::exchangetype_old"
    )
    op.execute("DROP TYPE exchangetype")
    op.execute("ALTER TYPE exchangetype_old RENAME TO exchangetype")
