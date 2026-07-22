"""Build the unified, snapshot-based opportunity center.

Revision ID: 034
Revises: 033
"""
from alembic import op

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS scope VARCHAR(20) NOT NULL DEFAULT 'global'")
    op.execute("COMMENT ON COLUMN market_opportunities.scope IS '机会范围：global 为全局市场，private 为用户私有关注范围'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE")
    op.execute("COMMENT ON COLUMN market_opportunities.user_id IS '私有机会所属用户；全局机会为空，用于严格用户隔离'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS domain VARCHAR(40) NOT NULL DEFAULT 'market'")
    op.execute("COMMENT ON COLUMN market_opportunities.domain IS '机会数据域，如 macro、capital、rates、futures、options、company、holder'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS subject_type VARCHAR(40) NOT NULL DEFAULT 'market'")
    op.execute("COMMENT ON COLUMN market_opportunities.subject_type IS '机会主体类型，如 market、indicator、company、holder、contract 或 option_series'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS subject_key VARCHAR(160) NOT NULL DEFAULT 'market'")
    op.execute("COMMENT ON COLUMN market_opportunities.subject_key IS '机会主体稳定标识；不得包含源日期或刷新时间'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS state VARCHAR(30) NOT NULL DEFAULT 'new'")
    op.execute("COMMENT ON COLUMN market_opportunities.state IS '确定性生命周期状态：new、active、changed、challenged、invalidated、stale 或 closed'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS trigger TEXT NOT NULL DEFAULT ''")
    op.execute("COMMENT ON COLUMN market_opportunities.trigger IS '形成该机会候选的透明触发事实或状态变化，不是评分'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS as_of VARCHAR(32)")
    op.execute("COMMENT ON COLUMN market_opportunities.as_of IS '当前机会快照采用的主要源日期或报告期'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS freshness JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("COMMENT ON COLUMN market_opportunities.freshness IS '各证据源可用性、日期与滞后状态；缺失不得替代为零'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS latest_snapshot_id UUID")
    op.execute("COMMENT ON COLUMN market_opportunities.latest_snapshot_id IS '最新不可变机会快照标识'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS consecutive_misses INTEGER NOT NULL DEFAULT 0")
    op.execute("COMMENT ON COLUMN market_opportunities.consecutive_misses IS '连续成功刷新中未再次检测到该机会的次数；两次后关闭'")
    op.execute("ALTER TABLE market_opportunities ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ")
    op.execute("COMMENT ON COLUMN market_opportunities.closed_at IS '机会关闭时间；为空表示仍在观察生命周期中'")
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_opportunities_feed ON market_opportunities(scope,user_id,domain,state,as_of DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_market_opportunities_subject ON market_opportunities(subject_type,subject_key)")

    op.execute("""CREATE TABLE market_opportunity_snapshots (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        opportunity_id UUID NOT NULL REFERENCES market_opportunities(id) ON DELETE CASCADE,
        snapshot_fingerprint VARCHAR(160) NOT NULL,
        state VARCHAR(30) NOT NULL,
        as_of VARCHAR(32), trigger TEXT NOT NULL,
        hypothesis TEXT NOT NULL,
        affected_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
        catalysts JSONB NOT NULL DEFAULT '[]'::jsonb,
        falsifiers JSONB NOT NULL DEFAULT '[]'::jsonb,
        source_dates JSONB NOT NULL DEFAULT '{}'::jsonb,
        freshness JSONB NOT NULL DEFAULT '{}'::jsonb,
        evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
        chart_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(opportunity_id,snapshot_fingerprint))""")
    op.execute("COMMENT ON TABLE market_opportunity_snapshots IS '机会不可变证据快照；保留每次源数据变化，不覆盖历史证据'")
    # Keep these statements explicit: the schema-comment CI statically verifies
    # every new SQL column and intentionally does not execute Python loops.
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.id IS '机会快照标识'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.opportunity_id IS '所属稳定机会标识'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.snapshot_fingerprint IS '源日期、事实和证据内容的确定性去重指纹'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.state IS '生成该快照时的生命周期状态'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.as_of IS '主要源日期或报告期'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.trigger IS '透明触发事实'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.hypothesis IS '可验证且可证伪的机会假设'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.affected_assets IS '受影响资产或公司列表'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.catalysts IS '后续可核验催化剂'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.falsifiers IS '明确证伪条件'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.source_dates IS '各证据源日期'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.freshness IS '各证据源新鲜度与缺失状态'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.evidence IS '支持、反对或证伪证据列表及源定位'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.chart_refs IS '用于展示原始全历史序列的只读引用'")
    op.execute("COMMENT ON COLUMN market_opportunity_snapshots.created_at IS '快照创建时间'")
    op.execute("CREATE INDEX ix_market_opportunity_snapshots_history ON market_opportunity_snapshots(opportunity_id,created_at DESC)")
    op.execute("""ALTER TABLE market_opportunities
        ADD CONSTRAINT fk_market_opportunities_latest_snapshot
        FOREIGN KEY(latest_snapshot_id) REFERENCES market_opportunity_snapshots(id)
        ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED""")

    op.execute("""CREATE TABLE market_opportunity_refresh_state (
        domain VARCHAR(40) PRIMARY KEY,
        source_watermark JSONB NOT NULL DEFAULT '{}'::jsonb,
        status VARCHAR(30) NOT NULL DEFAULT 'idle',
        last_started_at TIMESTAMPTZ,
        last_succeeded_at TIMESTAMPTZ,
        last_error TEXT,
        candidates_seen INTEGER NOT NULL DEFAULT 0,
        duration_ms INTEGER,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE market_opportunity_refresh_state IS '分域机会物化状态、水位和错误信息；供增量调度、健康检查与监控使用'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.domain IS '机会数据域主键'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.source_watermark IS '该域已处理的上游源水位'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.status IS '最近刷新状态'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.last_started_at IS '最近开始时间'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.last_succeeded_at IS '最近成功时间'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.last_error IS '最近失败原因；成功后清空'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.candidates_seen IS '最近成功刷新检测到的候选数'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.duration_ms IS '最近刷新耗时毫秒'")
    op.execute("COMMENT ON COLUMN market_opportunity_refresh_state.updated_at IS '状态记录最后更新时间'")

    op.execute("""UPDATE market_opportunities SET
        domain=CASE WHEN playbook_key='option_surface_evidence' THEN 'options' ELSE 'rates' END,
        subject_type='market', subject_key=playbook_key, state='closed', lifecycle_state='closed',
        trigger=CASE WHEN playbook_key='option_surface_evidence' THEN '历史兼容：期权模型证据可用' ELSE '历史兼容：流动性传导观察' END,
        as_of=(SELECT MAX(value) FROM jsonb_each_text(source_dates::jsonb)),
        closed_at=now()
        WHERE domain='market'""")


def downgrade() -> None:
    raise RuntimeError("Migration 034 is additive and intentionally non-reversible")
