"""Add immutable AgentOS research, decision, strategy, and consensus records.

Revision ID: 042
Revises: 041
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None


def c(name, type_, *args, comment: str, **kwargs):
    return sa.Column(name, type_, *args, comment=comment, **kwargs)


def upgrade() -> None:
    op.create_table(
        "research_hypotheses",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="研究假设主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("title", sa.String(240), nullable=False, comment="假设标题"),
        c("status", sa.String(30), nullable=False, server_default="draft", comment="生命周期状态"),
        c("current_version", sa.Integer(), nullable=False, server_default="1", comment="当前修订号"),
        c("review_date", sa.Date(), comment="下次复核日期"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="结构化且可证伪的用户研究假设",
    )
    op.create_index("ix_research_hypotheses_user_status", "research_hypotheses", ["user_id", "status", "updated_at"])
    op.create_table(
        "research_hypothesis_revisions",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="假设修订主键"),
        c("hypothesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_hypotheses.id", ondelete="CASCADE"), nullable=False, comment="所属假设"),
        c("version", sa.Integer(), nullable=False, comment="不可变修订号"),
        c("thesis", sa.Text(), nullable=False, comment="判断正文"),
        c("falsification", sa.Text(), nullable=False, comment="证伪条件"),
        c("evidence_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="带研报页码或章节的证据引用"),
        c("outcome_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="复核结果"),
        c("created_by", sa.String(30), nullable=False, server_default="user", comment="修订来源"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="研究假设的不可变内容、证据和结果修订",
    )
    op.create_index("uq_research_hypothesis_revision", "research_hypothesis_revisions", ["hypothesis_id", "version"], unique=True)
    op.create_table(
        "decision_records",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="决策主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("title", sa.String(240), nullable=False, comment="决策标题"),
        c("status", sa.String(30), nullable=False, server_default="draft", comment="决策状态"),
        c("current_version", sa.Integer(), nullable=False, server_default="1", comment="当前修订号"),
        c("hypothesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_hypotheses.id", ondelete="SET NULL"), comment="来源研究假设"),
        c("decided_at", sa.DateTime(timezone=True), comment="用户确认时间"),
        c("review_date", sa.Date(), comment="复核日期"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="用户确认的投资研究决策；不代表交易订单",
    )
    op.create_index("ix_decision_records_user_status", "decision_records", ["user_id", "status", "updated_at"])
    op.create_table(
        "decision_revisions",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="决策修订主键"),
        c("decision_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("decision_records.id", ondelete="CASCADE"), nullable=False, comment="所属决策"),
        c("version", sa.Integer(), nullable=False, comment="不可变修订号"),
        c("rationale", sa.Text(), nullable=False, comment="决策理由"),
        c("action_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="分析动作；不得包含券商订单"),
        c("conditions_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="可判真假的条件与失效动作"),
        c("evidence_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="证据引用"),
        c("attribution_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="事后归因"),
        c("created_by", sa.String(30), nullable=False, server_default="user", comment="修订来源"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="决策理由、条件、证据和归因的不可变修订",
    )
    op.create_index("uq_decision_revision", "decision_revisions", ["decision_id", "version"], unique=True)
    op.create_table(
        "strategy_experiments",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="策略实验主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("name", sa.String(180), nullable=False, comment="实验名称"),
        c("template_key", sa.String(40), nullable=False, comment="白名单策略模板"),
        c("status", sa.String(30), nullable=False, server_default="active", comment="实验状态"),
        c("parameters_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="版本化策略参数"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="更新时间"),
        comment="白名单投研策略实验定义",
    )
    op.create_index("ix_strategy_experiments_user", "strategy_experiments", ["user_id", "status", "updated_at"])
    op.create_table(
        "strategy_run_versions",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="策略运行版本主键"),
        c("experiment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_experiments.id", ondelete="CASCADE"), nullable=False, comment="所属实验"),
        c("version", sa.Integer(), nullable=False, comment="不可变运行版本"),
        c("status", sa.String(30), nullable=False, server_default="queued", comment="运行状态"),
        c("parameters_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="运行参数快照"),
        c("data_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="输入数据版本和发布日期"),
        c("metrics_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="收益与风险指标"),
        c("series_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="净值序列"),
        c("trades_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="模拟交易记录"),
        c("error_message", sa.Text(), comment="失败原因"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        c("completed_at", sa.DateTime(timezone=True), comment="完成时间"),
        comment="可审计、不可变且防未来数据的策略回测结果",
    )
    op.create_index("uq_strategy_run_version", "strategy_run_versions", ["experiment_id", "version"], unique=True)
    op.create_table(
        "consensus_snapshots",
        c("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), comment="共识快照主键"),
        c("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户"),
        c("subject_type", sa.String(30), nullable=False, comment="研究对象类型"),
        c("subject_code", sa.String(80), nullable=False, comment="研究对象代码"),
        c("as_of", sa.Date(), nullable=False, comment="共识截止日期"),
        c("status", sa.String(30), nullable=False, server_default="insufficient_evidence", comment="证据完整状态"),
        c("claims_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb"), comment="带来源定位的独立主张"),
        c("summary_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="满足门槛后生成的共识摘要"),
        c("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        comment="只有可追溯研报证据达到门槛时才形成的卖方共识快照",
    )
    op.create_index("ix_consensus_user_subject", "consensus_snapshots", ["user_id", "subject_type", "subject_code", "as_of"])


def downgrade() -> None:
    for table in ["consensus_snapshots", "strategy_run_versions", "strategy_experiments", "decision_revisions", "decision_records", "research_hypothesis_revisions", "research_hypotheses"]:
        op.drop_table(table)
