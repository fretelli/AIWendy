"""Add household wealth, SAA and TAA planning framework.

Revision ID: 038
Revises: 037
"""
from alembic import op

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def _comments(table: str, descriptions: dict[str, str]) -> None:
    for column, description in descriptions.items():
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{description}'")


def upgrade() -> None:
    op.execute("""CREATE TABLE wealth_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL DEFAULT '我的家庭财富', base_currency VARCHAR(12) NOT NULL DEFAULT 'CNY',
        annual_essential_spending NUMERIC(24,6) NOT NULL DEFAULT 0 CHECK (annual_essential_spending >= 0),
        short_bucket_months INTEGER NOT NULL DEFAULT 24 CHECK (short_bucket_months > 0),
        medium_bucket_months INTEGER NOT NULL DEFAULT 60 CHECK (medium_bucket_months > short_bucket_months),
        aspirational_cap NUMERIC(12,8) NOT NULL DEFAULT 0.10 CHECK (aspirational_cap >= 0 AND aspirational_cap <= 0.20),
        satellite_cap NUMERIC(12,8) NOT NULL DEFAULT 0.20 CHECK (satellite_cap >= 0 AND satellite_cap <= 0.30),
        settings_json JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE wealth_profiles IS '用户私有家庭财富规划单元；允许只有一名本人成员，不代表真实金融账户'")
    _comments("wealth_profiles", {"id":"家庭财富档案标识","user_id":"档案所属用户并保证一人一档","name":"用户可识别的财富档案名称","base_currency":"规划基础币种；首期固定人民币","annual_essential_spending":"家庭年度必要支出人民币估值","short_bucket_months":"短期资金桶月数边界","medium_bucket_months":"中期资金桶月数上边界","aspirational_cap":"进取层占可配置财富上限","satellite_cap":"卫星部分占市场层上限","settings_json":"框架扩展设置","created_at":"档案创建时间","updated_at":"档案更新时间"})

    op.execute("""CREATE TABLE household_members (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        name VARCHAR(120) NOT NULL, role VARCHAR(30) NOT NULL DEFAULT 'self', birth_date DATE NOT NULL,
        retirement_age INTEGER, dependency_end_date DATE, annual_income NUMERIC(24,6) NOT NULL DEFAULT 0,
        income_type VARCHAR(40), income_stability VARCHAR(30), is_primary BOOLEAN NOT NULL DEFAULT false,
        notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE household_members IS '家庭财富规划成员；本人必需，伴侣和受抚养人可选'")
    _comments("household_members", {"id":"成员标识","profile_id":"所属家庭财富档案","name":"成员称呼","role":"本人、伴侣、受抚养人或其他角色","birth_date":"出生日期；年龄实时派生","retirement_age":"预计退休年龄","dependency_end_date":"受抚养关系预计结束日期","annual_income":"年度收入人民币估值","income_type":"工资、经营或其他收入类型","income_stability":"收入稳定性说明","is_primary":"是否为主要规划成员","notes":"成员保障与其他说明","created_at":"成员创建时间","updated_at":"成员更新时间"})
    op.execute("CREATE INDEX ix_household_members_profile ON household_members(profile_id,role,birth_date)")
    op.execute("CREATE UNIQUE INDEX uq_household_members_one_self ON household_members(profile_id) WHERE role = 'self'")

    op.execute("""CREATE TABLE wealth_assets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL, category VARCHAR(40) NOT NULL, value_cny NUMERIC(24,6) NOT NULL CHECK (value_cny >= 0),
        original_currency VARCHAR(12), original_value NUMERIC(24,6), liquidity VARCHAR(30) NOT NULL DEFAULT 'liquid',
        allocatable BOOLEAN NOT NULL DEFAULT true, owner_member_id UUID REFERENCES household_members(id) ON DELETE SET NULL,
        notes TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE wealth_assets IS '用户手工维护的家庭资产及流动性分类，不执行外部估值'")
    _comments("wealth_assets", {"id":"资产标识","profile_id":"所属家庭财富档案","name":"资产名称","category":"现金、金融资产、房产、企业股权、养老金、保险或其他类别","value_cny":"用户输入的人民币估值","original_currency":"可选原始币种说明","original_value":"可选原币种金额","liquidity":"流动、有限流动或非流动","allocatable":"是否计入可配置金融财富","owner_member_id":"可选资产归属成员","notes":"估值口径与其他说明","created_at":"资产创建时间","updated_at":"资产更新时间"})
    op.execute("CREATE INDEX ix_wealth_assets_profile ON wealth_assets(profile_id,category,liquidity)")

    op.execute("""CREATE TABLE wealth_liabilities (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        name VARCHAR(160) NOT NULL, category VARCHAR(40) NOT NULL, balance_cny NUMERIC(24,6) NOT NULL CHECK (balance_cny >= 0),
        monthly_payment_cny NUMERIC(24,6) NOT NULL DEFAULT 0 CHECK (monthly_payment_cny >= 0), due_date DATE,
        owner_member_id UUID REFERENCES household_members(id) ON DELETE SET NULL, notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE wealth_liabilities IS '家庭当前负债与明确偿还责任的手工规划记录'")
    _comments("wealth_liabilities", {"id":"负债标识","profile_id":"所属家庭财富档案","name":"负债名称","category":"房贷、消费贷款或其他类别","balance_cny":"剩余负债人民币金额","monthly_payment_cny":"当前月度偿还金额","due_date":"预计到期日期","owner_member_id":"可选负债责任成员","notes":"利率和其他说明","created_at":"负债创建时间","updated_at":"负债更新时间"})
    op.execute("CREATE INDEX ix_wealth_liabilities_profile ON wealth_liabilities(profile_id,category,due_date)")

    op.execute("""CREATE TABLE wealth_goals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        member_id UUID REFERENCES household_members(id) ON DELETE SET NULL, name VARCHAR(160) NOT NULL,
        target_amount_cny NUMERIC(24,6) NOT NULL CHECK (target_amount_cny > 0), target_date DATE NOT NULL,
        priority VARCHAR(30) NOT NULL DEFAULT 'important', flexibility VARCHAR(30) NOT NULL DEFAULT 'flexible', notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE wealth_goals IS '关联家庭成员的目标金额、期限、优先级与弹性，不承诺目标达成'")
    _comments("wealth_goals", {"id":"目标标识","profile_id":"所属家庭财富档案","member_id":"可选关联家庭成员","name":"目标名称","target_amount_cny":"目标人民币金额","target_date":"目标日期","priority":"必须保障、重要或进取优先级","flexibility":"固定或可调整金额属性","notes":"目标口径与说明","created_at":"目标创建时间","updated_at":"目标更新时间"})
    op.execute("CREATE INDEX ix_wealth_goals_profile ON wealth_goals(profile_id,priority,target_date)")

    op.execute("""CREATE TABLE wealth_assignments (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        asset_id UUID NOT NULL REFERENCES wealth_assets(id) ON DELETE CASCADE, goal_id UUID REFERENCES wealth_goals(id) ON DELETE CASCADE,
        layer VARCHAR(30), amount_cny NUMERIC(24,6) NOT NULL CHECK (amount_cny > 0), notes TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE wealth_assignments IS '把同一资产金额拆分指定给目标或安全、市场、进取财富层的规划记录'")
    _comments("wealth_assignments", {"id":"资金指定标识","profile_id":"所属家庭财富档案","asset_id":"资金来源资产","goal_id":"可选目标去向","layer":"可选安全、市场或进取层去向","amount_cny":"指定人民币金额","notes":"指定原因说明","created_at":"指定创建时间"})
    op.execute("CREATE INDEX ix_wealth_assignments_profile ON wealth_assignments(profile_id,asset_id,goal_id)")

    op.execute("""CREATE TABLE wealth_framework_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        version INTEGER NOT NULL, snapshot JSONB NOT NULL, summary JSONB NOT NULL, conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
        content_hash VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(profile_id,version))""")
    op.execute("COMMENT ON TABLE wealth_framework_versions IS '家庭现状、目标、三层财富、期限桶和核心卫星参数的不可变框架版本'")
    _comments("wealth_framework_versions", {"id":"框架版本标识","profile_id":"所属家庭财富档案","version":"档案内单调递增版本号","snapshot":"成员、资产负债、目标和指定关系完整快照","summary":"净财富、资金层、期限桶和覆盖率摘要","conflicts":"违反硬边界的明确冲突列表","content_hash":"确定性内容哈希","created_at":"版本创建时间"})
    op.execute("CREATE INDEX ix_wealth_framework_profile_created ON wealth_framework_versions(profile_id,created_at DESC)")

    op.execute("""CREATE TABLE saa_policy_versions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        framework_version_id UUID NOT NULL REFERENCES wealth_framework_versions(id) ON DELETE RESTRICT,
        source_allocation_policy_version_id UUID REFERENCES allocation_policy_versions(id) ON DELETE SET NULL,
        version INTEGER NOT NULL, name VARCHAR(160) NOT NULL, effective_date DATE NOT NULL, review_date DATE NOT NULL,
        targets JSONB NOT NULL, constraints_snapshot JSONB NOT NULL, source_type VARCHAR(30) NOT NULL DEFAULT 'manual',
        status VARCHAR(30) NOT NULL DEFAULT 'draft', content_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(profile_id,version))""")
    op.execute("COMMENT ON TABLE saa_policy_versions IS '家庭财富框架之上的长期战略资产配置基准、目标权重和允许区间不可变版本'")
    _comments("saa_policy_versions", {"id":"SAA版本标识","profile_id":"所属家庭财富档案","framework_version_id":"引用的不可变财富框架版本","source_allocation_policy_version_id":"可选导入的现有ERC配置版本","version":"档案内SAA版本号","name":"SAA名称","effective_date":"战略基准生效日期","review_date":"计划复核日期","targets":"财富层与资产类别目标权重和上下限","constraints_snapshot":"生成时家庭与配置硬约束","source_type":"手工或现有配置导入来源","status":"草案、已确认或已取代状态","content_hash":"确定性内容哈希","created_at":"SAA版本创建时间"})
    op.execute("CREATE INDEX ix_saa_policy_profile_status ON saa_policy_versions(profile_id,status,created_at DESC)")

    op.execute("""CREATE TABLE taa_overlays (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(), profile_id UUID NOT NULL REFERENCES wealth_profiles(id) ON DELETE CASCADE,
        saa_version_id UUID NOT NULL REFERENCES saa_policy_versions(id) ON DELETE CASCADE,
        opportunity_snapshot_id UUID REFERENCES market_opportunity_snapshots(id) ON DELETE SET NULL,
        title VARCHAR(200) NOT NULL, deltas JSONB NOT NULL, rationale TEXT NOT NULL,
        evidence JSONB NOT NULL DEFAULT '[]'::jsonb, falsifiers JSONB NOT NULL DEFAULT '[]'::jsonb,
        starts_at DATE NOT NULL, review_at DATE NOT NULL, expires_at DATE NOT NULL,
        status VARCHAR(30) NOT NULL DEFAULT 'draft', content_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now())""")
    op.execute("COMMENT ON TABLE taa_overlays IS '已确认SAA上的人工战术偏离；有证据、复核、失效与人工确认但不自动调仓'")
    _comments("taa_overlays", {"id":"TAA覆盖层标识","profile_id":"所属家庭财富档案","saa_version_id":"引用的SAA长期基准","opportunity_snapshot_id":"可选不可变机会证据快照","title":"战术调整名称","deltas":"各资产类别相对SAA的权重增减","rationale":"临时偏离的投资判断","evidence":"支持证据快照","falsifiers":"证伪与提前退出条件","starts_at":"生效日期","review_at":"强制人工复核日期","expires_at":"最晚失效日期","status":"草案、已确认、已关闭或已过期状态","content_hash":"确定性内容哈希","created_at":"TAA创建时间","updated_at":"TAA更新时间"})
    op.execute("CREATE INDEX ix_taa_overlays_profile_status ON taa_overlays(profile_id,status,review_at,expires_at)")


def downgrade() -> None:
    raise RuntimeError("Migration 038 is additive and intentionally non-reversible")
