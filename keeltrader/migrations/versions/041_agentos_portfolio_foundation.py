"""Add the user-owned AgentOS portfolio ledger.

Revision ID: 041
Revises: 040
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "041"
down_revision = "040"
branch_labels = None
depends_on = None


def c(name, type_, *args, comment: str, **kwargs):
    return sa.Column(name, type_, *args, comment=comment, **kwargs)


def upgrade() -> None:
    op.create_table(
        "portfolio_accounts",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="组合账户主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("name", sa.String(160), nullable=False, comment="账户名称"),
        c("account_type", sa.String(30), nullable=False, server_default="manual", comment="账户录入类型"),
        c("base_currency", sa.String(12), nullable=False, server_default="CNY", comment="账户基础币种"),
        c("status", sa.String(30), nullable=False, server_default="active", comment="账户状态"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="用户手工维护或 CSV 导入的研究组合账户；不代表券商账户",
    )
    op.create_index("ix_portfolio_accounts_user_status", "portfolio_accounts", ["user_id", "status", "updated_at"])

    op.create_table(
        "portfolio_instruments",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="持仓标的主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("symbol", sa.String(80), nullable=False, comment="市场代码"),
        c("name", sa.String(160), nullable=False, comment="标的名称"),
        c("market", sa.String(30), nullable=False, comment="交易市场"),
        c("asset_class", sa.String(40), nullable=False, comment="资产类别"),
        c("currency", sa.String(12), nullable=False, server_default="CNY", comment="计价币种"),
        c("direction", sa.String(12), nullable=False, server_default="long", comment="多空方向"),
        c("multiplier", sa.Numeric(24, 8), nullable=False, server_default="1", comment="合约乘数"),
        c("expiry", sa.Date(), comment="衍生品到期日"),
        c("strike", sa.Numeric(24, 8), comment="期权行权价"),
        c("option_type", sa.String(12), comment="期权类型"),
        c("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="非关键扩展属性"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="用户组合中的股票、基金、现金及衍生品标的",
    )
    op.create_index("uq_portfolio_instrument_user_symbol", "portfolio_instruments", ["user_id", "symbol", "market"], unique=True)
    op.create_index("ix_portfolio_instrument_user_asset", "portfolio_instruments", ["user_id", "asset_class"])

    op.create_table(
        "portfolio_transactions",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="流水主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False, comment="所属组合账户"),
        c("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolio_instruments.id", ondelete="RESTRICT"), comment="关联标的；现金流水可为空"),
        c("transaction_type", sa.String(30), nullable=False, comment="流水类型"),
        c("trade_date", sa.Date(), nullable=False, comment="交易或记账日期"),
        c("quantity", sa.Numeric(28, 10), nullable=False, server_default="0", comment="带方向的数量变化"),
        c("price", sa.Numeric(28, 10), comment="成交或调整价格"),
        c("cash_amount", sa.Numeric(28, 10), nullable=False, server_default="0", comment="带方向的现金变化"),
        c("fee", sa.Numeric(24, 8), nullable=False, server_default="0", comment="费用"),
        c("currency", sa.String(12), nullable=False, server_default="CNY", comment="流水币种"),
        c("external_ref", sa.String(160), comment="外部幂等标识"),
        c("note", sa.Text(), comment="用户备注"),
        c("metadata_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="导入行及扩展信息"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="不可变的组合交易、现金和手工调整流水",
    )
    op.create_index("ix_portfolio_transactions_user_date", "portfolio_transactions", ["user_id", "trade_date", "created_at"])
    op.create_index("ix_portfolio_transactions_account_date", "portfolio_transactions", ["account_id", "trade_date", "created_at"])
    op.create_index("uq_portfolio_transactions_external", "portfolio_transactions", ["account_id", "external_ref"], unique=True)

    op.create_table(
        "portfolio_import_batches",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="导入批次主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False, comment="目标账户"),
        c("import_type", sa.String(30), nullable=False, comment="持仓、流水或历史净值"),
        c("filename", sa.String(255), nullable=False, comment="原文件名"),
        c("content_hash", sa.String(64), nullable=False, comment="原文件内容校验和"),
        c("mapping_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="用户确认的列映射"),
        c("rows_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="验证后的规范化行"),
        c("row_count", sa.Integer(), nullable=False, server_default="0", comment="规范化行数"),
        c("status", sa.String(30), nullable=False, server_default="preview", comment="批次状态"),
        c("error_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="逐行验证错误"),
        c("committed_at", sa.DateTime(timezone=True), comment="提交时间"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="可预览、原子提交且按内容校验和幂等的 CSV 导入批次",
    )
    op.create_index("uq_portfolio_import_user_hash", "portfolio_import_batches", ["user_id", "account_id", "content_hash"], unique=True)
    op.create_index("ix_portfolio_import_user_status", "portfolio_import_batches", ["user_id", "status", "created_at"])

    op.create_table(
        "portfolio_manual_prices",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="手工价格主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolio_instruments.id", ondelete="CASCADE"), nullable=False, comment="关联标的"),
        c("price_date", sa.Date(), nullable=False, comment="价格日期"),
        c("price", sa.Numeric(28, 10), nullable=False, comment="用户提供价格"),
        c("currency", sa.String(12), nullable=False, comment="价格币种"),
        c("source_note", sa.String(240), comment="价格来源说明"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="带明确日期和来源说明的用户手工估值价格",
    )
    op.create_index("uq_portfolio_manual_price", "portfolio_manual_prices", ["user_id", "instrument_id", "price_date"], unique=True)
    op.create_index("ix_portfolio_manual_price_lookup", "portfolio_manual_prices", ["instrument_id", "price_date"])

    op.create_table(
        "portfolio_daily_snapshots",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="净值快照主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False, comment="所属账户"),
        c("snapshot_date", sa.Date(), nullable=False, comment="快照日期"),
        c("base_currency", sa.String(12), nullable=False, comment="快照基础币种"),
        c("nav", sa.Numeric(28, 10), nullable=False, comment="组合净值"),
        c("net_flow", sa.Numeric(28, 10), nullable=False, server_default="0", comment="当日外部净现金流"),
        c("data_status", sa.String(20), nullable=False, server_default="complete", comment="数据完整状态"),
        c("positions_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="持仓估值快照"),
        c("attribution_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="收益归因快照"),
        c("source_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="价格和汇率来源快照"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="按日保存的组合净值、持仓、来源和归因快照",
    )
    op.create_index("uq_portfolio_daily_snapshot", "portfolio_daily_snapshots", ["account_id", "snapshot_date"], unique=True)
    op.create_index("ix_portfolio_daily_user_date", "portfolio_daily_snapshots", ["user_id", "snapshot_date"])


def downgrade() -> None:
    for table in ["portfolio_daily_snapshots", "portfolio_manual_prices", "portfolio_import_batches", "portfolio_transactions", "portfolio_instruments", "portfolio_accounts"]:
        op.drop_table(table)
