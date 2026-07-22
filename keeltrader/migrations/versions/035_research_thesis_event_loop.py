"""Add the user-owned thesis and research event loop.

Revision ID: 035
Revises: 034
"""
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE research_theses (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(240) NOT NULL,
        subject_type VARCHAR(40) NOT NULL,
        subject_key VARCHAR(160) NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'draft',
        thesis TEXT NOT NULL,
        catalysts JSONB NOT NULL DEFAULT '[]'::jsonb,
        falsifiers JSONB NOT NULL DEFAULT '[]'::jsonb,
        review_at TIMESTAMPTZ,
        origin_resource_type VARCHAR(40),
        origin_resource_id VARCHAR(160),
        current_version INTEGER NOT NULL DEFAULT 1,
        closed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE research_theses IS '用户拥有的正式研究论点；连接机会、证据、复核与关闭生命周期，不包含评分或自动交易' ")
    op.execute("COMMENT ON COLUMN research_theses.id IS '研究论点标识'")
    op.execute("COMMENT ON COLUMN research_theses.user_id IS '论点所属用户；用于严格私有隔离'")
    op.execute("COMMENT ON COLUMN research_theses.title IS '用户可识别的论点标题'")
    op.execute("COMMENT ON COLUMN research_theses.subject_type IS '论点主体类型，如 company、market、holder 或 asset'")
    op.execute("COMMENT ON COLUMN research_theses.subject_key IS '论点主体稳定标识'")
    op.execute("COMMENT ON COLUMN research_theses.status IS '生命周期：draft、active、challenged、invalidated 或 closed'")
    op.execute("COMMENT ON COLUMN research_theses.thesis IS '可验证且可证伪的正式论点正文'")
    op.execute("COMMENT ON COLUMN research_theses.catalysts IS '用户确认的后续催化；带日期时必须标明来源类型'")
    op.execute("COMMENT ON COLUMN research_theses.falsifiers IS '明确证伪条件列表'")
    op.execute("COMMENT ON COLUMN research_theses.review_at IS '用户计划的下次人工复核时间'")
    op.execute("COMMENT ON COLUMN research_theses.origin_resource_type IS '创建论点所依据的原始资源类型'")
    op.execute("COMMENT ON COLUMN research_theses.origin_resource_id IS '创建论点所依据的不可变快照或资源标识'")
    op.execute("COMMENT ON COLUMN research_theses.current_version IS '当前不可变版本号'")
    op.execute("COMMENT ON COLUMN research_theses.closed_at IS '论点关闭时间'")
    op.execute("COMMENT ON COLUMN research_theses.created_at IS '论点创建时间'")
    op.execute("COMMENT ON COLUMN research_theses.updated_at IS '论点最近更新时间'")
    op.execute("CREATE INDEX ix_research_theses_user_status ON research_theses(user_id,status,updated_at DESC)")
    op.execute("CREATE INDEX ix_research_theses_subject ON research_theses(user_id,subject_type,subject_key)")

    op.execute("""CREATE TABLE research_thesis_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        thesis_id UUID NOT NULL REFERENCES research_theses(id) ON DELETE CASCADE,
        version INTEGER NOT NULL,
        snapshot JSONB NOT NULL,
        diff JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(thesis_id,version))""")
    op.execute("COMMENT ON TABLE research_thesis_versions IS '研究论点不可变版本历史；每次用户确认的修改均新增版本，不覆盖旧结论'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.id IS '论点版本标识'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.thesis_id IS '所属研究论点标识'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.version IS '单个论点内单调递增的版本号'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.snapshot IS '该版本完整论点内容快照'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.diff IS '相对前一版本的字段级变化'")
    op.execute("COMMENT ON COLUMN research_thesis_versions.created_at IS '版本创建时间'")

    op.execute("""CREATE TABLE research_thesis_evidence_links (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        thesis_id UUID NOT NULL REFERENCES research_theses(id) ON DELETE CASCADE,
        stance VARCHAR(20) NOT NULL,
        source_type VARCHAR(40) NOT NULL,
        source_id VARCHAR(160) NOT NULL,
        citation JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(thesis_id,stance,source_type,source_id))""")
    op.execute("COMMENT ON TABLE research_thesis_evidence_links IS '论点与不可变证据资源的关联；支持、冲突和证伪证据分开保存'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.id IS '证据关联标识'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.thesis_id IS '所属研究论点标识'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.stance IS '证据立场：supporting、challenging 或 invalidating'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.source_type IS '证据资源类型，如 opportunity_snapshot、dossier_version、report 或 context_snapshot'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.source_id IS '证据资源不可变标识'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.citation IS '证据来源、日期、正文摘录与页码或章节定位'")
    op.execute("COMMENT ON COLUMN research_thesis_evidence_links.created_at IS '证据关联创建时间'")

    op.execute("""CREATE TABLE research_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        event_key VARCHAR(96) NOT NULL,
        category VARCHAR(40) NOT NULL,
        event_type VARCHAR(60) NOT NULL,
        title VARCHAR(240) NOT NULL,
        summary TEXT NOT NULL,
        resource_type VARCHAR(40) NOT NULL,
        resource_id VARCHAR(160) NOT NULL,
        source_date VARCHAR(32),
        before_state JSONB NOT NULL DEFAULT '{}'::jsonb,
        after_state JSONB NOT NULL DEFAULT '{}'::jsonb,
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        read_at TIMESTAMPTZ,
        archived_at TIMESTAMPTZ,
        detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(user_id,event_key))""")
    op.execute("COMMENT ON TABLE research_events IS '用户研究事件统一收件箱；按源日期和检测时间记录变化，不进行评分或推荐排序'")
    op.execute("COMMENT ON COLUMN research_events.id IS '研究事件标识'")
    op.execute("COMMENT ON COLUMN research_events.user_id IS '事件所属用户；全局机会仅向明确关注者生成事件'")
    op.execute("COMMENT ON COLUMN research_events.event_key IS '用户范围内确定性幂等去重键'")
    op.execute("COMMENT ON COLUMN research_events.category IS '事件类别，如 opportunity、company、holder、thesis 或 schedule'")
    op.execute("COMMENT ON COLUMN research_events.event_type IS '可机读事件类型'")
    op.execute("COMMENT ON COLUMN research_events.title IS '事件标题'")
    op.execute("COMMENT ON COLUMN research_events.summary IS '透明描述变化事实的事件摘要'")
    op.execute("COMMENT ON COLUMN research_events.resource_type IS '关联研究资源类型'")
    op.execute("COMMENT ON COLUMN research_events.resource_id IS '关联研究资源标识'")
    op.execute("COMMENT ON COLUMN research_events.source_date IS '上游披露、报告期或市场源日期'")
    op.execute("COMMENT ON COLUMN research_events.before_state IS '变化前状态或字段快照'")
    op.execute("COMMENT ON COLUMN research_events.after_state IS '变化后状态或字段快照'")
    op.execute("COMMENT ON COLUMN research_events.metadata_json IS '来源定位和展示所需的非敏感元数据'")
    op.execute("COMMENT ON COLUMN research_events.read_at IS '用户阅读时间；为空表示未读'")
    op.execute("COMMENT ON COLUMN research_events.archived_at IS '用户归档时间；归档事件默认不在今日页展示'")
    op.execute("COMMENT ON COLUMN research_events.detected_at IS 'KeelTrader 检测到变化的时间'")
    op.execute("COMMENT ON COLUMN research_events.created_at IS '事件记录创建时间'")
    op.execute("CREATE INDEX ix_research_events_inbox ON research_events(user_id,archived_at,read_at,detected_at DESC)")


def downgrade() -> None:
    raise RuntimeError("Migration 035 is additive and intentionally non-reversible")
