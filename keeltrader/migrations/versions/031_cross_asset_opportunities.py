"""Cross-asset rates, opportunities and private trade planning.

Revision ID: 031
Revises: 030
"""
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE agent_risk_profiles (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        account_equity NUMERIC(24,6), currency VARCHAR(12) NOT NULL DEFAULT 'CNY',
        risk_per_trade NUMERIC(12,8) NOT NULL DEFAULT 0.005,
        aggregate_open_risk NUMERIC(12,8) NOT NULL DEFAULT 0.03,
        single_instrument_notional NUMERIC(12,8) NOT NULL DEFAULT 0.20,
        derivative_premium_risk NUMERIC(12,8) NOT NULL DEFAULT 0.005,
        max_leverage NUMERIC(12,8) NOT NULL DEFAULT 1.0,
        sizing_method VARCHAR(40) NOT NULL DEFAULT 'fixed_risk',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE market_opportunities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), fingerprint VARCHAR(160) NOT NULL UNIQUE,
        playbook_key VARCHAR(80) NOT NULL, title VARCHAR(240) NOT NULL, lifecycle_state VARCHAR(30) NOT NULL,
        hypothesis TEXT NOT NULL, affected_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
        catalysts JSONB NOT NULL DEFAULT '[]'::jsonb, falsifiers JSONB NOT NULL DEFAULT '[]'::jsonb,
        source_dates JSONB NOT NULL DEFAULT '{}'::jsonb, first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE market_opportunity_evidence (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        stance VARCHAR(20) NOT NULL, fact TEXT NOT NULL, source VARCHAR(240) NOT NULL,
        source_date VARCHAR(32), source_ref JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_market_opportunity_evidence ON market_opportunity_evidence(opportunity_id, stance)")
    op.execute("""CREATE TABLE agent_opportunity_follows (
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        state VARCHAR(20) NOT NULL DEFAULT 'following', notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(user_id, opportunity_id))""")
    op.execute("""CREATE TABLE agent_trade_plan_drafts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL, unavailable_reason TEXT, direction VARCHAR(20), instrument VARCHAR(80),
        entry_trigger TEXT, entry_price NUMERIC(24,8), stop_price NUMERIC(24,8), target_price NUMERIC(24,8),
        horizon VARCHAR(80), quantity NUMERIC(24,8), max_loss NUMERIC(24,8), notional NUMERIC(24,8),
        checklist JSONB NOT NULL DEFAULT '[]'::jsonb, assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
        human_confirmation_required BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_agent_trade_plans_user ON agent_trade_plan_drafts(user_id, updated_at DESC)")
    for statement in """
        COMMENT ON TABLE agent_risk_profiles IS '用户私有风险预算与仓位规划偏好，不用于自动下单';
        COMMENT ON COLUMN agent_risk_profiles.user_id IS '用户标识，同时为风险配置主键';
        COMMENT ON COLUMN agent_risk_profiles.account_equity IS '用户提供的账户权益';
        COMMENT ON COLUMN agent_risk_profiles.currency IS '账户权益币种';
        COMMENT ON COLUMN agent_risk_profiles.risk_per_trade IS '单笔交易最大风险占权益比例';
        COMMENT ON COLUMN agent_risk_profiles.aggregate_open_risk IS '全部未平仓交易合计最大风险占权益比例';
        COMMENT ON COLUMN agent_risk_profiles.single_instrument_notional IS '单一工具最大名义本金占权益比例';
        COMMENT ON COLUMN agent_risk_profiles.derivative_premium_risk IS '衍生品权利金最大风险占权益比例';
        COMMENT ON COLUMN agent_risk_profiles.max_leverage IS '允许的最大杠杆倍数';
        COMMENT ON COLUMN agent_risk_profiles.sizing_method IS '仓位计算方法';
        COMMENT ON COLUMN agent_risk_profiles.updated_at IS '配置最后更新时间';
        COMMENT ON COLUMN agent_risk_profiles.created_at IS '配置创建时间';

        COMMENT ON TABLE market_opportunities IS '由跨资产事实与证据确定性生成的机会假设，不含评分、排名或自动交易指令';
        COMMENT ON COLUMN market_opportunities.id IS '机会标识';
        COMMENT ON COLUMN market_opportunities.fingerprint IS '机会去重指纹';
        COMMENT ON COLUMN market_opportunities.playbook_key IS '确定性机会模板标识';
        COMMENT ON COLUMN market_opportunities.title IS '机会标题';
        COMMENT ON COLUMN market_opportunities.lifecycle_state IS '机会生命周期状态';
        COMMENT ON COLUMN market_opportunities.hypothesis IS '可验证的机会假设';
        COMMENT ON COLUMN market_opportunities.affected_assets IS '受影响资产列表';
        COMMENT ON COLUMN market_opportunities.catalysts IS '潜在催化剂列表';
        COMMENT ON COLUMN market_opportunities.falsifiers IS '证伪条件列表';
        COMMENT ON COLUMN market_opportunities.source_dates IS '各证据源的数据日期';
        COMMENT ON COLUMN market_opportunities.first_seen_at IS '首次发现时间';
        COMMENT ON COLUMN market_opportunities.last_seen_at IS '最近仍成立时间';

        COMMENT ON TABLE market_opportunity_evidence IS '市场机会的正反两面源证据，保留事实、来源和定位信息';
        COMMENT ON COLUMN market_opportunity_evidence.id IS '证据标识';
        COMMENT ON COLUMN market_opportunity_evidence.opportunity_id IS '所属市场机会标识';
        COMMENT ON COLUMN market_opportunity_evidence.stance IS '证据立场，如 supporting 或 challenging';
        COMMENT ON COLUMN market_opportunity_evidence.fact IS '证据支持的事实陈述';
        COMMENT ON COLUMN market_opportunity_evidence.source IS '证据来源名称';
        COMMENT ON COLUMN market_opportunity_evidence.source_date IS '证据源日期';
        COMMENT ON COLUMN market_opportunity_evidence.source_ref IS '证据定位与源引用结构';
        COMMENT ON COLUMN market_opportunity_evidence.created_at IS '证据创建时间';

        COMMENT ON TABLE agent_opportunity_follows IS '用户私有的市场机会关注状态与笔记';
        COMMENT ON COLUMN agent_opportunity_follows.user_id IS '用户标识';
        COMMENT ON COLUMN agent_opportunity_follows.opportunity_id IS '市场机会标识';
        COMMENT ON COLUMN agent_opportunity_follows.state IS '用户关注状态';
        COMMENT ON COLUMN agent_opportunity_follows.notes IS '用户私有笔记';
        COMMENT ON COLUMN agent_opportunity_follows.created_at IS '关注记录创建时间';
        COMMENT ON COLUMN agent_opportunity_follows.updated_at IS '关注记录最后更新时间';

        COMMENT ON TABLE agent_trade_plan_drafts IS '需人工确认的私有交易计划草稿，仅作研究与风险规划，不执行交易';
        COMMENT ON COLUMN agent_trade_plan_drafts.id IS '交易计划草稿标识';
        COMMENT ON COLUMN agent_trade_plan_drafts.user_id IS '用户标识';
        COMMENT ON COLUMN agent_trade_plan_drafts.opportunity_id IS '关联市场机会标识';
        COMMENT ON COLUMN agent_trade_plan_drafts.status IS '草稿状态';
        COMMENT ON COLUMN agent_trade_plan_drafts.unavailable_reason IS '无法生成有效计划时的明确原因';
        COMMENT ON COLUMN agent_trade_plan_drafts.direction IS '计划方向';
        COMMENT ON COLUMN agent_trade_plan_drafts.instrument IS '计划使用的交易工具';
        COMMENT ON COLUMN agent_trade_plan_drafts.entry_trigger IS '入场触发条件';
        COMMENT ON COLUMN agent_trade_plan_drafts.entry_price IS '假设入场价格';
        COMMENT ON COLUMN agent_trade_plan_drafts.stop_price IS '假设止损价格';
        COMMENT ON COLUMN agent_trade_plan_drafts.target_price IS '假设目标价格';
        COMMENT ON COLUMN agent_trade_plan_drafts.horizon IS '计划持有期限';
        COMMENT ON COLUMN agent_trade_plan_drafts.quantity IS '按风险预算计算的建议数量';
        COMMENT ON COLUMN agent_trade_plan_drafts.max_loss IS '按草稿参数估算的最大损失';
        COMMENT ON COLUMN agent_trade_plan_drafts.notional IS '按草稿参数估算的名义本金';
        COMMENT ON COLUMN agent_trade_plan_drafts.checklist IS '人工确认前检查清单';
        COMMENT ON COLUMN agent_trade_plan_drafts.assumptions IS '计划计算所用假设';
        COMMENT ON COLUMN agent_trade_plan_drafts.human_confirmation_required IS '是否必须人工确认，固定为真';
        COMMENT ON COLUMN agent_trade_plan_drafts.created_at IS '草稿创建时间';
        COMMENT ON COLUMN agent_trade_plan_drafts.updated_at IS '草稿最后更新时间';
    """.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Migration 031 is additive and intentionally non-reversible")
