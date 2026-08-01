"""Normalize AgentOS portfolio instrument identity.

Revision ID: 044
Revises: 043
"""
import sqlalchemy as sa
from alembic import op

revision = "044"
down_revision = "043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portfolio_instruments", sa.Column("instrument_type", sa.String(40), nullable=True,
                  comment="规范标的类型；未知旧标的保持 manual，不猜测"))
    op.add_column("portfolio_instruments", sa.Column("provider_symbol", sa.String(100), nullable=True,
                  comment="正式价格源使用的提供商代码"))
    op.execute("""UPDATE portfolio_instruments SET instrument_type = CASE
        WHEN lower(asset_class) IN ('stock','equity','a_share') THEN 'stock'
        WHEN lower(asset_class) IN ('etf') THEN 'etf'
        WHEN lower(asset_class) IN ('fund','open_fund','mutual_fund') THEN 'open_fund'
        WHEN lower(asset_class) IN ('future','futures') THEN 'future'
        WHEN lower(asset_class) IN ('option','options') THEN 'option'
        WHEN lower(asset_class) IN ('convertible_bond','cb') THEN 'convertible_bond'
        WHEN lower(asset_class) IN ('cash') THEN 'cash'
        WHEN lower(asset_class) IN ('fx','foreign_exchange') THEN 'fx'
        WHEN lower(asset_class) IN ('alternative','alternatives') THEN 'alternative'
        ELSE 'manual' END,
        provider_symbol = symbol WHERE instrument_type IS NULL""")
    op.alter_column("portfolio_instruments", "instrument_type", nullable=False, server_default="manual")
    op.create_index("ix_portfolio_instrument_provider", "portfolio_instruments", ["instrument_type", "provider_symbol"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_instrument_provider", table_name="portfolio_instruments")
    op.drop_column("portfolio_instruments", "provider_symbol")
    op.drop_column("portfolio_instruments", "instrument_type")
