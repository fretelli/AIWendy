"""Journal domain schemas."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class TradeDirection(str, Enum):
    """Trade direction enum."""

    long = "long"
    short = "short"


class TradeResult(str, Enum):
    """Trade result enum."""

    win = "win"
    loss = "loss"
    breakeven = "breakeven"
    open = "open"


class RuleViolationType(str, Enum):
    """Rule violation types."""

    early_exit = "early_exit"
    late_exit = "late_exit"
    no_stop_loss = "no_stop_loss"
    over_leverage = "over_leverage"
    revenge_trade = "revenge_trade"
    fomo = "fomo"
    position_size = "position_size"
    other = "other"


class JournalBase(BaseModel):
    """Base journal schema."""

    project_id: Optional[uuid.UUID] = None

    # Trade information
    symbol: str = Field(..., max_length=20, description="Trading symbol")
    market: Optional[str] = Field(None, max_length=20, description="Market type")
    direction: TradeDirection
    trade_date: Optional[datetime] = None

    # Entry
    entry_time: Optional[datetime] = None
    entry_price: Optional[float] = None
    position_size: Optional[float] = None

    # Exit
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None

    # Results
    result: TradeResult = TradeResult.open
    pnl_amount: Optional[float] = None
    pnl_percentage: Optional[float] = None

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # Emotions (1-5 scale)
    emotion_before: Optional[int] = Field(None, ge=1, le=5)
    emotion_during: Optional[int] = Field(None, ge=1, le=5)
    emotion_after: Optional[int] = Field(None, ge=1, le=5)

    # Psychology
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    stress_level: Optional[int] = Field(None, ge=1, le=5)
    followed_rules: bool = True
    rule_violations: List[RuleViolationType] = []

    # Notes
    setup_description: Optional[str] = None
    exit_reason: Optional[str] = None
    lessons_learned: Optional[str] = None
    notes: Optional[str] = None

    # Tags and strategy
    tags: List[str] = []
    strategy_name: Optional[str] = None

    # Attachments
    screenshots: List[str] = []

    @validator("pnl_percentage")
    def validate_pnl_percentage(cls, v):
        """Validate PnL percentage is reasonable."""
        if v is not None and abs(v) > 1000:  # More than 1000% seems unrealistic
            raise ValueError("PnL percentage seems unrealistic")
        return v

    class Config:
        use_enum_values = True


class JournalCreate(JournalBase):
    """Journal creation schema."""

    pass


class JournalUpdate(BaseModel):
    """Journal update schema - all fields optional."""

    project_id: Optional[uuid.UUID] = None

    # Trade information
    symbol: Optional[str] = None
    market: Optional[str] = None
    direction: Optional[TradeDirection] = None
    trade_date: Optional[datetime] = None

    # Entry
    entry_time: Optional[datetime] = None
    entry_price: Optional[float] = None
    position_size: Optional[float] = None

    # Exit
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None

    # Results
    result: Optional[TradeResult] = None
    pnl_amount: Optional[float] = None
    pnl_percentage: Optional[float] = None

    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

    # Emotions
    emotion_before: Optional[int] = Field(None, ge=1, le=5)
    emotion_during: Optional[int] = Field(None, ge=1, le=5)
    emotion_after: Optional[int] = Field(None, ge=1, le=5)

    # Psychology
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    stress_level: Optional[int] = Field(None, ge=1, le=5)
    followed_rules: Optional[bool] = None
    rule_violations: Optional[List[RuleViolationType]] = None

    # Notes
    setup_description: Optional[str] = None
    exit_reason: Optional[str] = None
    lessons_learned: Optional[str] = None
    notes: Optional[str] = None

    # Tags and strategy
    tags: Optional[List[str]] = None
    strategy_name: Optional[str] = None

    # Attachments
    screenshots: Optional[List[str]] = None

    class Config:
        use_enum_values = True


class JournalResponse(JournalBase):
    """Journal response schema."""

    id: uuid.UUID
    user_id: uuid.UUID

    # AI Analysis
    ai_insights: Optional[str] = None
    detected_patterns: Optional[List[str]] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_winner: bool = False
    is_rule_violation: bool = False

    class Config:
        orm_mode = True
        use_enum_values = True


class JournalListResponse(BaseModel):
    """Journal list response."""

    items: List[JournalResponse]
    total: int
    page: int = 1
    per_page: int = 20


class JournalStatistics(BaseModel):
    """Journal statistics."""

    # Trade counts
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    open_trades: int = 0

    # Financial metrics
    total_pnl: float = 0
    average_win: float = 0
    average_loss: float = 0
    best_trade: float = 0
    worst_trade: float = 0

    # Performance ratios
    win_rate: float = 0
    profit_factor: float = 0  # Total wins / Total losses

    # Psychology metrics
    average_confidence: float = 0
    average_stress: float = 0
    rule_violation_rate: float = 0

    # Streaks
    current_streak: int = 0  # Positive = winning, Negative = losing
    best_streak: int = 0
    worst_streak: int = 0


class JournalFilter(BaseModel):
    """Journal filter parameters."""

    project_id: Optional[uuid.UUID] = None
    symbol: Optional[str] = None
    market: Optional[str] = None
    direction: Optional[TradeDirection] = None
    result: Optional[TradeResult] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[List[str]] = None
    followed_rules: Optional[bool] = None


class QuickJournalEntry(BaseModel):
    """Quick journal entry for fast logging."""

    symbol: str
    direction: TradeDirection
    result: TradeResult
    pnl_amount: Optional[float] = None
    emotion_after: int = Field(..., ge=1, le=5)
    violated_rules: bool = False
    quick_note: Optional[str] = Field(None, max_length=500)
