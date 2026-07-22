"""Add private asset-allocation research accounts and immutable policies.

Revision ID: 036
Revises: 035
"""
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def _comments(table: str, descriptions: dict[str, str]) -> None:
    for column, description in descriptions.items():
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{description}'")


def upgrade() -> None:
    op.execute("""CREATE TABLE allocation_accounts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL,
        base_currency VARCHAR(12) NOT NULL DEFAULT 'CNY',
        capital NUMERIC(24,6) NOT NULL CHECK (capital > 0),
        horizon_months INTEGER NOT NULL CHECK (horizon_months > 0),
        liquidity_reserve NUMERIC(24,6) NOT NULL DEFAULT 0 CHECK (liquidity_reserve >= 0),
        max_drawdown NUMERIC(12,8) NOT NULL CHECK (max_drawdown > 0 AND max_drawdown <= 1),
        max_leverage NUMERIC(12,8) NOT NULL DEFAULT 1 CHECK (max_leverage > 0),
        future_cash_needs JSONB NOT NULL DEFAULT '[]'::jsonb,
        allowed_markets JSONB NOT NULL DEFAULT '[]'::jsonb,
        allowed_instruments JSONB NOT NULL DEFAULT '[]'::jsonb,
        hard_restrictions JSONB NOT NULL DEFAULT '[]'::jsonb,
        status VARCHAR(30) NOT NULL DEFAULT 'active',
        current_policy_version_id UUID,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE allocation_accounts IS '用户私有资产配置研究资金池；保存约束和当前确认版本，不代表券商账户、真实持仓或交易授权'")
    _comments("allocation_accounts", {
        "id": "资产配置研究账户标识", "user_id": "账户所属用户；用于严格私有隔离",
        "name": "用户可识别的资金池名称", "base_currency": "基础计价币种；首版固定为 CNY",
        "capital": "研究资金总额", "horizon_months": "配置研究期限，单位为月",
        "liquidity_reserve": "优先保留、不参与风险预算的流动性金额",
        "max_drawdown": "用户可承受的最大压力回撤，小数口径",
        "max_leverage": "用户允许的最大底层总敞口倍数",
        "future_cash_needs": "未来现金需求列表；包含日期、金额和说明",
        "allowed_markets": "用户账户和法律条件允许的市场列表",
        "allowed_instruments": "用户允许的实施工具类型列表",
        "hard_restrictions": "仅保存法律、账户或伦理硬限制，不保存普通机会排除条件",
        "status": "账户状态：active 或 archived", "current_policy_version_id": "当前由用户确认的不可变配置版本标识",
        "created_at": "账户创建时间", "updated_at": "账户最近更新时间",
    })
    op.execute("CREATE INDEX ix_allocation_accounts_user ON allocation_accounts(user_id,status,updated_at DESC)")

    op.execute("""CREATE TABLE allocation_policy_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        account_id UUID NOT NULL REFERENCES allocation_accounts(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        feasibility_status VARCHAR(30) NOT NULL,
        quality_status VARCHAR(30) NOT NULL,
        constraint_snapshot JSONB NOT NULL,
        methodology_snapshot JSONB NOT NULL,
        data_snapshot JSONB NOT NULL,
        risk_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
        stress_results JSONB NOT NULL DEFAULT '[]'::jsonb,
        infeasible_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
        content_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(account_id,version))""")
    op.execute("COMMENT ON TABLE allocation_policy_versions IS '资产配置不可变版本；完整保存约束、方法、数据门禁、风险与压力结果，相同输入快照产生相同内容哈希'")
    _comments("allocation_policy_versions", {
        "id": "配置版本标识", "account_id": "所属资产配置研究账户标识", "version": "账户内单调递增版本号",
        "feasibility_status": "求解状态：feasible、infeasible 或 unavailable", "quality_status": "输入数据整体质量状态",
        "constraint_snapshot": "生成时的完整用户约束快照", "methodology_snapshot": "风险预算、协方差和压力测试方法快照",
        "data_snapshot": "使用的不可变源序列、日期范围与内容哈希", "risk_summary": "组合风险、贡献和底层敞口摘要",
        "stress_results": "固定情景和可用历史窗口的压力测试结果", "infeasible_reasons": "数据不可用或约束无解的明确原因列表",
        "content_hash": "排除数据库标识和创建时间后的确定性 SHA-256 内容哈希", "created_at": "不可变版本创建时间",
    })
    op.execute("CREATE INDEX ix_allocation_policy_account_created ON allocation_policy_versions(account_id,created_at DESC)")
    op.execute("ALTER TABLE allocation_accounts ADD CONSTRAINT fk_allocation_accounts_current_policy FOREIGN KEY (current_policy_version_id) REFERENCES allocation_policy_versions(id) ON DELETE SET NULL")

    op.execute("""CREATE TABLE allocation_policy_sleeves (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), policy_version_id UUID NOT NULL REFERENCES allocation_policy_versions(id) ON DELETE CASCADE,
        sleeve_key VARCHAR(40) NOT NULL, label VARCHAR(120) NOT NULL,
        target_weight NUMERIC(12,8) NOT NULL, min_weight NUMERIC(12,8) NOT NULL, max_weight NUMERIC(12,8) NOT NULL,
        amount_cny NUMERIC(24,6) NOT NULL, risk_contribution NUMERIC(12,8) NOT NULL,
        currency_exposure JSONB NOT NULL DEFAULT '{}'::jsonb, source_series_id VARCHAR(80),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(policy_version_id,sleeve_key))""")
    op.execute("COMMENT ON TABLE allocation_policy_sleeves IS '不可变配置版本的战略资产权重、允许范围、人民币金额与风险贡献'")
    _comments("allocation_policy_sleeves", {
        "id": "资产袖套记录标识", "policy_version_id": "所属不可变配置版本标识", "sleeve_key": "战略资产稳定标识",
        "label": "战略资产中文名称", "target_weight": "占总资金的目标权重", "min_weight": "允许范围下限",
        "max_weight": "允许范围上限", "amount_cny": "按总资金换算的人民币金额", "risk_contribution": "占风险资产组合总风险的贡献",
        "currency_exposure": "该袖套产生的币种底层敞口", "source_series_id": "用于计算的受管总回报序列标识", "created_at": "记录创建时间",
    })

    op.execute("""CREATE TABLE allocation_policy_implementations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), policy_version_id UUID NOT NULL REFERENCES allocation_policy_versions(id) ON DELETE CASCADE,
        sleeve_key VARCHAR(40) NOT NULL, instrument_type VARCHAR(30) NOT NULL, instrument_code VARCHAR(80) NOT NULL,
        instrument_name VARCHAR(160) NOT NULL, target_weight NUMERIC(12,8) NOT NULL DEFAULT 0,
        amount_cny NUMERIC(24,6) NOT NULL DEFAULT 0, underlying_key VARCHAR(120) NOT NULL,
        margin_cash NUMERIC(24,6), premium_cash NUMERIC(24,6), delta_equivalent NUMERIC(24,6),
        gross_notional NUMERIC(24,6), net_notional NUMERIC(24,6), max_loss NUMERIC(24,6),
        gamma NUMERIC(24,10), vega NUMERIC(24,10), metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE allocation_policy_implementations IS '配置版本的直接实施工具；期货和期权记录现金占用与底层等价敞口，避免与底层资产重复计权'")
    _comments("allocation_policy_implementations", {
        "id": "实施记录标识", "policy_version_id": "所属不可变配置版本标识", "sleeve_key": "所属战略资产袖套",
        "instrument_type": "工具类型：fund、etf、future、option 或 fx_cash", "instrument_code": "工具市场代码",
        "instrument_name": "工具名称", "target_weight": "工具占总资金的资本权重", "amount_cny": "工具对应人民币资本金额",
        "underlying_key": "底层风险敞口稳定标识", "margin_cash": "期货等工具占用的保证金现金",
        "premium_cash": "期权权利金现金", "delta_equivalent": "按 Delta 换算的人民币底层敞口",
        "gross_notional": "工具总名义金额", "net_notional": "考虑方向后的净名义金额", "max_loss": "工具可确定的最大损失",
        "gamma": "期权 Gamma 敞口", "vega": "期权 Vega 敞口", "metadata_json": "费用、期限、乘数和来源日期等元数据",
        "created_at": "实施记录创建时间",
    })
    op.execute("CREATE INDEX ix_allocation_implementation_policy ON allocation_policy_implementations(policy_version_id,sleeve_key)")

    op.execute("""CREATE TABLE allocation_policy_thesis_links (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), policy_version_id UUID NOT NULL REFERENCES allocation_policy_versions(id) ON DELETE CASCADE,
        thesis_id UUID NOT NULL REFERENCES research_theses(id) ON DELETE CASCADE,
        thesis_version_id UUID NOT NULL REFERENCES research_thesis_versions(id) ON DELETE CASCADE,
        sleeve_key VARCHAR(40) NOT NULL, weight_delta NUMERIC(12,8) NOT NULL,
        review_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
        evidence_snapshot JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE allocation_policy_thesis_links IS '战术权重偏离与用户确认论点版本的不可变关联；必须具有复核和失效时间'")
    _comments("allocation_policy_thesis_links", {
        "id": "战术偏离关联标识", "policy_version_id": "所属不可变配置版本标识", "thesis_id": "所属用户研究论点标识",
        "thesis_version_id": "生成时引用的不可变论点版本标识", "sleeve_key": "发生战术偏离的战略资产袖套",
        "weight_delta": "相对战略目标的权重偏离，小数口径", "review_at": "必须人工复核的时间",
        "expires_at": "偏离失效时间；系统只提醒而不自动调仓", "evidence_snapshot": "论点内容与证据定位快照",
        "created_at": "关联创建时间",
    })
    op.execute("CREATE INDEX ix_allocation_thesis_policy ON allocation_policy_thesis_links(policy_version_id,sleeve_key)")


def downgrade() -> None:
    raise RuntimeError("Migration 036 is additive and intentionally non-reversible")
