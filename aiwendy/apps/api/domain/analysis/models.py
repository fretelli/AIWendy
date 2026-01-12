"""Analysis domain models."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ReportType(str, enum.Enum):
    """Types of analysis reports."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class PatternType(str, enum.Enum):
    """Types of behavioral patterns."""

    REVENGE_TRADING = "revenge_trading"  # 报复性交易
    OVERTRADING = "overtrading"  # 过度交易
    FEAR_OF_LOSS = "fear_of_loss"  # 损失恐惧
    GREED = "greed"  # 贪婪
    FOMO = "fomo"  # 错失恐惧
    ANALYSIS_PARALYSIS = "analysis_paralysis"  # 分析瘫痪
    CONFIRMATION_BIAS = "confirmation_bias"  # 确认偏差
    ANCHORING_BIAS = "anchoring_bias"  # 锚定偏差
    EMOTIONAL_TRADING = "emotional_trading"  # 情绪化交易
    DISCIPLINE_BREACH = "discipline_breach"  # 违反纪律


class AnalysisReport(Base):
    """Analysis report for user trading behavior."""

    __tablename__ = "analysis_reports"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Report info
    report_type = Column(Enum(ReportType), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Trading statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    breakeven_trades = Column(Integer, default=0)

    win_rate = Column(Float, nullable=True)  # Percentage
    profit_factor = Column(Float, nullable=True)  # Total wins / Total losses
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)

    total_pnl = Column(Float, nullable=True)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    best_trade = Column(Float, nullable=True)
    worst_trade = Column(Float, nullable=True)

    # Psychological metrics
    avg_emotion_score = Column(Float, nullable=True)  # Average 1-5
    avg_confidence_score = Column(Float, nullable=True)
    avg_stress_score = Column(Float, nullable=True)
    rule_violation_rate = Column(Float, nullable=True)  # Percentage

    # Behavior patterns
    detected_patterns = Column(JSON, default=list)  # List of PatternType
    pattern_frequencies = Column(JSON, default=dict)  # Pattern -> count
    pattern_insights = Column(JSON, default=dict)  # Pattern -> insight text

    # AI Analysis
    ai_summary = Column(Text, nullable=True)
    ai_recommendations = Column(JSON, default=list)  # List of recommendations
    ai_strengths = Column(JSON, default=list)  # Identified strengths
    ai_weaknesses = Column(JSON, default=list)  # Identified weaknesses
    ai_action_items = Column(JSON, default=list)  # Suggested actions

    # Key insights
    key_insights = Column(JSON, default=list)
    coaching_notes = Column(Text, nullable=True)

    # Timestamps
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    viewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("ix_analysis_reports_user_type", "user_id", "report_type"),
        Index("ix_analysis_reports_period", "period_start", "period_end"),
    )

    def __repr__(self):
        return f"<AnalysisReport(id={self.id}, type={self.report_type}, user_id={self.user_id})>"


class BehaviorPattern(Base):
    """Detected behavior patterns for users."""

    __tablename__ = "behavior_patterns"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journals.id"), nullable=True)
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=True
    )

    # Pattern info
    pattern_type = Column(Enum(PatternType), nullable=False)
    confidence_score = Column(Float, nullable=False)  # 0-1 confidence
    severity = Column(Integer, nullable=True)  # 1-5 severity scale

    # Context
    context = Column(JSON, nullable=True)  # Additional context data
    trigger_conditions = Column(JSON, nullable=True)  # What triggered this pattern

    # Evidence
    evidence = Column(JSON, default=list)  # List of supporting evidence
    related_trades = Column(JSON, default=list)  # List of related journal IDs

    # Intervention
    intervention_suggested = Column(Text, nullable=True)
    intervention_accepted = Column(Boolean, nullable=True)
    intervention_result = Column(Text, nullable=True)

    # Timestamps
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_behavior_patterns_user_type", "user_id", "pattern_type"),
        Index("ix_behavior_patterns_detected", "detected_at"),
    )


class PerformanceMetric(Base):
    """Time-series performance metrics for users."""

    __tablename__ = "performance_metrics"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Metric info
    metric_date = Column(DateTime(timezone=True), nullable=False)

    # Daily metrics
    daily_pnl = Column(Float, nullable=True)
    daily_trades = Column(Integer, default=0)
    daily_win_rate = Column(Float, nullable=True)

    # Cumulative metrics
    cumulative_pnl = Column(Float, nullable=True)
    cumulative_trades = Column(Integer, default=0)
    account_balance = Column(Float, nullable=True)

    # Risk metrics
    daily_var = Column(Float, nullable=True)  # Value at Risk
    daily_max_drawdown = Column(Float, nullable=True)

    # Psychological metrics
    avg_emotion = Column(Float, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    rule_violations = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("ix_performance_metrics_user_date", "user_id", "metric_date"),
    )
