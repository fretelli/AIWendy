"""Report domain models."""

import enum
import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional

from core.database import Base
from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Enum, Float,
                        ForeignKey, Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class ReportType(str, enum.Enum):
    """Report type enumeration."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportStatus(str, enum.Enum):
    """Report generation status."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    SENT = "sent"


class Report(Base):
    """Periodic report model."""

    __tablename__ = "reports"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Report metadata
    report_type = Column(Enum(ReportType), nullable=False)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(500), nullable=True)

    # Time period
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    # Report content
    summary = Column(Text, nullable=True)  # AI生成的总结
    content = Column(JSON, nullable=True)  # 报告详细内容（结构化数据）

    # Statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, nullable=True)

    total_pnl = Column(Float, default=0.0)
    avg_pnl = Column(Float, nullable=True)
    max_profit = Column(Float, nullable=True)
    max_loss = Column(Float, nullable=True)

    # Psychological metrics
    avg_mood_before = Column(Float, nullable=True)
    avg_mood_after = Column(Float, nullable=True)
    mood_improvement = Column(Float, nullable=True)

    # Trading patterns
    top_mistakes = Column(JSON, default=list)  # List of common mistakes
    top_successes = Column(JSON, default=list)  # List of successful patterns
    improvements = Column(JSON, default=list)  # Recommended improvements

    # AI insights
    ai_analysis = Column(Text, nullable=True)  # AI生成的深度分析
    ai_recommendations = Column(JSON, default=list)  # AI建议列表
    key_insights = Column(JSON, default=list)  # 关键洞察
    action_items = Column(JSON, default=list)  # 行动项

    # Coach insights (if applicable)
    coach_notes = Column(JSON, default=dict)  # 各教练的评论
    primary_coach_id = Column(String(50), nullable=True)  # 主要使用的教练

    # Report settings
    is_public = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    # Generation metadata
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING)
    generation_time = Column(Float, nullable=True)  # 生成耗时（秒）
    error_message = Column(Text, nullable=True)  # 错误信息（如果失败）

    # Email/notification status
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="reports")
    project = relationship("Project", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_reports_user_type", "user_id", "report_type"),
        Index("ix_reports_user_period", "user_id", "period_start", "period_end"),
        Index(
            "ix_reports_user_project_period", "user_id", "project_id", "period_start"
        ),
        Index("ix_reports_status", "status"),
    )

    def __repr__(self):
        return (
            f"<Report(id={self.id}, type={self.report_type}, user_id={self.user_id})>"
        )


class ReportSchedule(Base):
    """User's report schedule preferences."""

    __tablename__ = "report_schedules"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )

    # Schedule settings
    daily_enabled = Column(Boolean, default=True)
    daily_time = Column(String(5), default="21:00")  # HH:MM format

    weekly_enabled = Column(Boolean, default=True)
    weekly_day = Column(Integer, default=0)  # 0=Monday, 6=Sunday
    weekly_time = Column(String(5), default="18:00")

    monthly_enabled = Column(Boolean, default=True)
    monthly_day = Column(Integer, default=1)  # Day of month (1-31)
    monthly_time = Column(String(5), default="18:00")

    # Notification preferences
    email_notification = Column(Boolean, default=True)
    in_app_notification = Column(Boolean, default=True)

    # Report preferences
    include_charts = Column(Boolean, default=True)
    include_ai_analysis = Column(Boolean, default=True)
    include_coach_feedback = Column(Boolean, default=True)

    # Language preference
    language = Column(String(5), default="zh")

    # Timezone
    timezone = Column(String(50), default="Asia/Shanghai")

    # Status
    is_active = Column(Boolean, default=True)

    # Last generation times
    last_daily_generated = Column(DateTime(timezone=True), nullable=True)
    last_weekly_generated = Column(DateTime(timezone=True), nullable=True)
    last_monthly_generated = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="report_schedule", uselist=False)

    def __repr__(self):
        return f"<ReportSchedule(user_id={self.user_id})>"


class ReportTemplate(Base):
    """Report template configuration."""

    __tablename__ = "report_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Template metadata
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    report_type = Column(Enum(ReportType), nullable=False)

    # Template structure
    sections = Column(JSON, nullable=False)  # List of sections to include
    metrics = Column(JSON, nullable=False)  # Metrics to calculate
    charts = Column(JSON, nullable=False)  # Charts to generate

    # AI prompts
    summary_prompt = Column(Text, nullable=True)
    analysis_prompt = Column(Text, nullable=True)
    recommendation_prompt = Column(Text, nullable=True)

    # Style settings
    theme = Column(String(50), default="default")
    color_scheme = Column(JSON, nullable=True)

    # Access control
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Indexes
    __table_args__ = (Index("ix_report_templates_type", "report_type", "is_active"),)

    def __repr__(self):
        return f"<ReportTemplate(name={self.name}, type={self.report_type})>"
