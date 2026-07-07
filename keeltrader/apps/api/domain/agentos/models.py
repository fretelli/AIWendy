"""AgentOS domain models.

These tables store research artifacts, decision logs, review lessons, and
strategy experiments. They intentionally do not store upstream data-provider
credentials such as Tushare tokens.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class InvestmentBrief(Base):
    """Daily investment brief generated from structured data and research docs."""

    __tablename__ = "investment_briefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    title = Column(String(200), nullable=False)
    brief_date = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    watchlist = Column(JSON, default=list, nullable=False)
    summary = Column(Text, nullable=False)
    signals = Column(JSON, default=list, nullable=False)
    risks = Column(JSON, default=list, nullable=False)
    falsifiers = Column(JSON, default=list, nullable=False)
    data_sources = Column(JSON, default=list, nullable=False)
    status = Column(String(30), default="draft", nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_investment_briefs_user_date", "user_id", "brief_date"),
        Index("ix_investment_briefs_project_date", "project_id", "brief_date"),
    )


class InvestmentMemo(Base):
    """Deep research memo with multi-perspective analysis."""

    __tablename__ = "investment_memos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    symbol = Column(String(50), nullable=False)
    market = Column(String(30), nullable=True)
    title = Column(String(240), nullable=False)
    thesis = Column(Text, nullable=False)
    analyst_views = Column(JSON, default=dict, nullable=False)
    bull_case = Column(Text, nullable=True)
    bear_case = Column(Text, nullable=True)
    red_team = Column(Text, nullable=True)
    risk_view = Column(Text, nullable=True)
    recommendation = Column(String(30), nullable=True)
    confidence = Column(Float, nullable=True)
    falsifiers = Column(JSON, default=list, nullable=False)
    data_sources = Column(JSON, default=list, nullable=False)
    status = Column(String(30), default="draft", nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_investment_memos_user_created", "user_id", "created_at"),
        Index("ix_investment_memos_symbol", "symbol"),
    )


class InvestmentDecision(Base):
    """Human-in-the-loop decision journal entry."""

    __tablename__ = "investment_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    memo_id = Column(UUID(as_uuid=True), ForeignKey("investment_memos.id"), nullable=True)

    symbol = Column(String(50), nullable=False)
    market = Column(String(30), nullable=True)
    action = Column(String(30), nullable=False)
    thesis = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    expected_horizon = Column(String(50), nullable=True)
    position_plan = Column(JSON, default=dict, nullable=False)
    risk_plan = Column(JSON, default=dict, nullable=False)
    falsifiers = Column(JSON, default=list, nullable=False)
    human_decision = Column(String(30), default="pending", nullable=False)
    human_reason = Column(Text, nullable=True)
    outcome = Column(JSON, nullable=True)
    status = Column(String(30), default="open", nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_investment_decisions_user_created", "user_id", "created_at"),
        Index("ix_investment_decisions_symbol", "symbol"),
        Index("ix_investment_decisions_status", "status"),
    )


class ReviewLesson(Base):
    """Lesson generated by review workflow; only approved lessons enter memory."""

    __tablename__ = "review_lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    title = Column(String(200), nullable=False)
    lesson = Column(Text, nullable=False)
    evidence = Column(JSON, default=list, nullable=False)
    category = Column(String(50), nullable=True)
    approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_review_lessons_user_created", "user_id", "created_at"),
        Index("ix_review_lessons_approved", "approved"),
    )


class StrategyHypothesis(Base):
    """Research hypothesis that can be implemented and backtested."""

    __tablename__ = "strategy_hypotheses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    name = Column(String(200), nullable=False)
    hypothesis = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)
    asset_universe = Column(JSON, default=list, nullable=False)
    frequency = Column(String(30), default="daily", nullable=False)
    status = Column(String(30), default="draft", nullable=False)
    attempt_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_strategy_hypotheses_user_created", "user_id", "created_at"),
        Index("ix_strategy_hypotheses_status", "status"),
    )


class BacktestRun(Base):
    """Backtest result for a strategy hypothesis."""

    __tablename__ = "backtest_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hypothesis_id = Column(UUID(as_uuid=True), ForeignKey("strategy_hypotheses.id"), nullable=True)

    engine = Column(String(50), default="agentos_vectorized_v1", nullable=False)
    symbol = Column(String(50), nullable=False)
    strategy = Column(String(100), nullable=False)
    params = Column(JSON, default=dict, nullable=False)
    train_start = Column(DateTime(timezone=True), nullable=True)
    train_end = Column(DateTime(timezone=True), nullable=True)
    test_start = Column(DateTime(timezone=True), nullable=True)
    test_end = Column(DateTime(timezone=True), nullable=True)
    metrics = Column(JSON, default=dict, nullable=False)
    trades = Column(JSON, default=list, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)
    passed_gate = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_backtest_runs_user_created", "user_id", "created_at"),
        Index("ix_backtest_runs_hypothesis", "hypothesis_id"),
        Index("ix_backtest_runs_symbol", "symbol"),
    )


class AgentPromptVersion(Base):
    """Versioned prompt/config artifact for audit and rollback."""

    __tablename__ = "agent_prompt_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_agent_prompt_versions_agent", "agent_name", "version", unique=True),
        Index("ix_agent_prompt_versions_active", "agent_name", "is_active"),
    )


class WorkflowVersion(Base):
    """Versioned workflow definition for AgentOS workflows."""

    __tablename__ = "workflow_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    definition = Column(JSON, default=dict, nullable=False)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_workflow_versions_workflow", "workflow_name", "version", unique=True),
        Index("ix_workflow_versions_active", "workflow_name", "is_active"),
    )
