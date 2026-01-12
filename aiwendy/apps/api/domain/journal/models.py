"""Journal domain models."""

import enum
# from pgvector.sqlalchemy import Vector  # Commented out until pgvector is installed
import uuid
from datetime import datetime
from typing import Optional

from core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship


class TradeDirection(str, enum.Enum):
    """Trade direction."""

    LONG = "long"
    SHORT = "short"


class TradeResult(str, enum.Enum):
    """Trade result."""

    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"
    OPEN = "open"  # Still open


class RuleViolationType(str, enum.Enum):
    """Types of trading rule violations."""

    EARLY_EXIT = "early_exit"  # 提前止盈
    LATE_EXIT = "late_exit"  # 晚止损
    NO_STOP_LOSS = "no_stop_loss"  # 没有止损
    OVER_LEVERAGE = "over_leverage"  # 过度杠杆
    REVENGE_TRADE = "revenge_trade"  # 报复性交易
    FOMO = "fomo"  # 追涨杀跌
    POSITION_SIZE = "position_size"  # 仓位过大
    OTHER = "other"


class Journal(Base):
    """Trading journal entry."""

    __tablename__ = "journals"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Trade information
    trade_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    symbol = Column(String(20), nullable=False)  # e.g., "AAPL", "BTCUSDT"
    market = Column(String(20), nullable=True)  # e.g., "stocks", "crypto"
    direction = Column(Enum(TradeDirection), nullable=False)

    # Entry
    entry_time = Column(DateTime(timezone=True), nullable=True)
    entry_price = Column(Float, nullable=True)
    position_size = Column(Float, nullable=True)

    # Exit
    exit_time = Column(DateTime(timezone=True), nullable=True)
    exit_price = Column(Float, nullable=True)

    # Results
    result = Column(Enum(TradeResult), default=TradeResult.OPEN)
    pnl_amount = Column(Float, nullable=True)  # Profit/Loss amount
    pnl_percentage = Column(Float, nullable=True)  # Profit/Loss percentage

    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)

    # Emotions (1-5 scale)
    emotion_before = Column(Integer, nullable=True)  # 1=very anxious, 5=very calm
    emotion_during = Column(Integer, nullable=True)
    emotion_after = Column(Integer, nullable=True)

    # Psychology
    confidence_level = Column(Integer, nullable=True)  # 1-5 scale
    stress_level = Column(Integer, nullable=True)  # 1-5 scale
    followed_rules = Column(Boolean, default=True)
    rule_violations = Column(JSON, default=list)  # List of RuleViolationType

    # Notes
    setup_description = Column(Text, nullable=True)  # Why entered
    exit_reason = Column(Text, nullable=True)  # Why exited
    lessons_learned = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)  # General notes

    # AI Analysis
    ai_insights = Column(Text, nullable=True)  # AI-generated insights
    detected_patterns = Column(JSON, nullable=True)  # Detected behavior patterns
    # embedding = Column(Vector(1536), nullable=True)  # For semantic search (requires pgvector)

    # Tags and categories
    tags = Column(JSON, default=list)  # User-defined tags
    strategy_name = Column(String(100), nullable=True)

    # Attachments
    screenshots = Column(JSON, default=list)  # List of screenshot URLs

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships
    # user = relationship("User", back_populates="journals")  # Commented to avoid circular import

    # Indexes
    __table_args__ = (
        Index("ix_journals_user_date", "user_id", "trade_date"),
        Index("ix_journals_user_project_date", "user_id", "project_id", "trade_date"),
        Index("ix_journals_symbol", "symbol"),
        Index("ix_journals_result", "result"),
    )

    @hybrid_property
    def is_winner(self) -> bool:
        """Check if trade was profitable."""
        return self.result == TradeResult.WIN

    @hybrid_property
    def is_rule_violation(self) -> bool:
        """Check if any rules were violated."""
        return not self.followed_rules or len(self.rule_violations) > 0

    def __repr__(self):
        return f"<Journal(id={self.id}, symbol={self.symbol}, pnl={self.pnl_amount})>"


class JournalTemplate(Base):
    """Template for quick journal entry."""

    __tablename__ = "journal_templates"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Template info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Default values
    default_values = Column(JSON, nullable=False)  # JSON with default field values

    # Usage
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
