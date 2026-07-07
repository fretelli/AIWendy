"""AgentOS investment research and decision tables.

Revision ID: 018
Revises: 017
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investment_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("brief_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("watchlist", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("signals", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("risks", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("falsifiers", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("data_sources", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investment_briefs_user_date", "investment_briefs", ["user_id", "brief_date"])
    op.create_index("ix_investment_briefs_project_date", "investment_briefs", ["project_id", "brief_date"])

    op.create_table(
        "investment_memos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("market", sa.String(30), nullable=True),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("analyst_views", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("bull_case", sa.Text(), nullable=True),
        sa.Column("bear_case", sa.Text(), nullable=True),
        sa.Column("red_team", sa.Text(), nullable=True),
        sa.Column("risk_view", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.String(30), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("falsifiers", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("data_sources", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investment_memos_user_created", "investment_memos", ["user_id", "created_at"])
    op.create_index("ix_investment_memos_symbol", "investment_memos", ["symbol"])

    op.create_table(
        "investment_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("memo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("investment_memos.id"), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("market", sa.String(30), nullable=True),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("expected_horizon", sa.String(50), nullable=True),
        sa.Column("position_plan", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("risk_plan", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("falsifiers", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("human_decision", sa.String(30), server_default="pending", nullable=False),
        sa.Column("human_reason", sa.Text(), nullable=True),
        sa.Column("outcome", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_investment_decisions_user_created", "investment_decisions", ["user_id", "created_at"])
    op.create_index("ix_investment_decisions_symbol", "investment_decisions", ["symbol"])
    op.create_index("ix_investment_decisions_status", "investment_decisions", ["status"])

    op.create_table(
        "review_lessons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("lesson", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("approved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_lessons_user_created", "review_lessons", ["user_id", "created_at"])
    op.create_index("ix_review_lessons_approved", "review_lessons", ["approved"])

    op.create_table(
        "strategy_hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("asset_universe", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("frequency", sa.String(30), server_default="daily", nullable=False),
        sa.Column("status", sa.String(30), server_default="draft", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_strategy_hypotheses_user_created", "strategy_hypotheses", ["user_id", "created_at"])
    op.create_index("ix_strategy_hypotheses_status", "strategy_hypotheses", ["status"])

    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("hypothesis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategy_hypotheses.id"), nullable=True),
        sa.Column("engine", sa.String(50), server_default="agentos_vectorized_v1", nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("strategy", sa.String(100), nullable=False),
        sa.Column("params", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("train_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("train_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("trades", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("passed_gate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_backtest_runs_user_created", "backtest_runs", ["user_id", "created_at"])
    op.create_index("ix_backtest_runs_hypothesis", "backtest_runs", ["hypothesis_id"])
    op.create_index("ix_backtest_runs_symbol", "backtest_runs", ["symbol"])

    op.create_table(
        "agent_prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_prompt_versions_agent", "agent_prompt_versions", ["agent_name", "version"], unique=True)
    op.create_index("ix_agent_prompt_versions_active", "agent_prompt_versions", ["agent_name", "is_active"])

    op.create_table(
        "workflow_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workflow_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("definition", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workflow_versions_workflow", "workflow_versions", ["workflow_name", "version"], unique=True)
    op.create_index("ix_workflow_versions_active", "workflow_versions", ["workflow_name", "is_active"])


def downgrade() -> None:
    op.drop_table("workflow_versions")
    op.drop_table("agent_prompt_versions")
    op.drop_table("backtest_runs")
    op.drop_table("strategy_hypotheses")
    op.drop_table("review_lessons")
    op.drop_table("investment_decisions")
    op.drop_table("investment_memos")
    op.drop_table("investment_briefs")
