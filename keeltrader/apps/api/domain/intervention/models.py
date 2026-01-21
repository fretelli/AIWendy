"""Pre-trade checklist and intervention models."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class ChecklistItemType(str, enum.Enum):
    """Types of checklist items."""

    RISK_CHECK = "risk_check"
    EMOTIONAL_CHECK = "emotional_check"
    STRATEGY_CHECK = "strategy_check"
    POSITION_SIZE_CHECK = "position_size_check"
    MARKET_CONDITION_CHECK = "market_condition_check"
    RULE_COMPLIANCE_CHECK = "rule_compliance_check"


class InterventionAction(str, enum.Enum):
    """Actions that can be taken by the intervention system."""

    BLOCK_TRADE = "block_trade"
    WARN_USER = "warn_user"
    REQUIRE_CONFIRMATION = "require_confirmation"
    SUGGEST_ALTERNATIVE = "suggest_alternative"
    NONE = "none"


class InterventionReason(str, enum.Enum):
    """Reasons for intervention."""

    REVENGE_TRADING_DETECTED = "revenge_trading_detected"
    OVERTRADING_DETECTED = "overtrading_detected"
    EXCESSIVE_RISK = "excessive_risk"
    EMOTIONAL_STATE_POOR = "emotional_state_poor"
    RULE_VIOLATION = "rule_violation"
    POSITION_SIZE_TOO_LARGE = "position_size_too_large"
    DAILY_LOSS_LIMIT_REACHED = "daily_loss_limit_reached"
    CHECKLIST_INCOMPLETE = "checklist_incomplete"


class PreTradeChecklist(Base):
    """Pre-trade checklist template."""

    __tablename__ = "pre_trade_checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    # Checklist info
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_required = Column(Boolean, default=False, nullable=False)  # Must complete before trading

    # Checklist items (JSON array)
    items = Column(JSON, nullable=False)  # [{"type": "risk_check", "question": "...", "required": true}]

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class PreTradeChecklistCompletion(Base):
    """Record of completed pre-trade checklist."""

    __tablename__ = "pre_trade_checklist_completions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    checklist_id = Column(UUID(as_uuid=True), ForeignKey("pre_trade_checklists.id"), nullable=False)
    checklist = relationship("PreTradeChecklist")

    # Associated trade (if any)
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journals.id"), nullable=True)
    journal = relationship("Journal")

    # Completion data
    responses = Column(JSON, nullable=False)  # {"item_id": {"checked": true, "notes": "..."}}
    all_required_completed = Column(Boolean, nullable=False)

    # Timestamps
    completed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class TradingIntervention(Base):
    """Record of trading interventions."""

    __tablename__ = "trading_interventions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    # Intervention details
    reason = Column(Enum(InterventionReason), nullable=False)
    action = Column(Enum(InterventionAction), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)  # Additional context

    # User response
    user_acknowledged = Column(Boolean, default=False, nullable=False)
    user_proceeded = Column(Boolean, default=False, nullable=False)  # Did user proceed despite warning?
    user_notes = Column(Text, nullable=True)
    gate_token = Column(UUID(as_uuid=True), nullable=True)
    gate_expires_at = Column(DateTime(timezone=True), nullable=True)
    gate_used_at = Column(DateTime(timezone=True), nullable=True)

    # Associated trade (if any)
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journals.id"), nullable=True)
    journal = relationship("Journal")

    # Timestamps
    triggered_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)


class TradingSession(Base):
    """Active trading session tracking."""

    __tablename__ = "trading_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User")

    # Session info
    is_active = Column(Boolean, default=True, nullable=False)
    trades_count = Column(Integer, default=0, nullable=False)
    session_pnl = Column(Integer, default=0, nullable=False)  # In cents

    # Risk metrics
    max_daily_loss_limit = Column(Integer, nullable=True)  # In cents
    max_trades_per_day = Column(Integer, nullable=True)
    enforce_trade_block = Column(Boolean, default=False, nullable=False)
    gate_timeout_minutes = Column(Integer, default=15, nullable=False)

    # Timestamps
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
