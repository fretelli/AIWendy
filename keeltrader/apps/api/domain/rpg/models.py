"""RPG gamification domain models."""

import enum
import uuid
from datetime import datetime, date

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class Rank(str, enum.Enum):
    """Trading character rank."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class AchievementCategory(str, enum.Enum):
    """Achievement categories."""
    TRADING = "trading"
    DISCIPLINE = "discipline"
    MILESTONES = "milestones"
    STREAKS = "streaks"


class AchievementRarity(str, enum.Enum):
    """Achievement rarity levels."""
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class QuestType(str, enum.Enum):
    """Quest types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    SPECIAL = "special"


class QuestStatus(str, enum.Enum):
    """Quest progress status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class PeriodType(str, enum.Enum):
    """Leaderboard period types."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TradingCharacter(Base):
    """Trading RPG character — one per user."""

    __tablename__ = "trading_characters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)

    # Profile
    nickname = Column(String(50), nullable=True)
    avatar_settings = Column(JSON, default=dict)

    # 5 core attributes (0-100)
    discipline = Column(Integer, default=50)
    patience = Column(Integer, default=50)
    risk_management = Column(Integer, default=50)
    decisiveness = Column(Integer, default=50)
    consistency = Column(Integer, default=50)

    # Progression
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    rank = Column(Enum(Rank), default=Rank.BRONZE)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="trading_character")
    achievements = relationship("UserAchievement", back_populates="character", lazy="selectin")
    quests = relationship("UserQuest", back_populates="character", lazy="selectin")

    def __repr__(self):
        return f"<TradingCharacter(user_id={self.user_id}, level={self.level}, rank={self.rank})>"


class Achievement(Base):
    """Achievement template — global definitions."""

    __tablename__ = "achievements"

    id = Column(String(50), primary_key=True)  # e.g. "first_blood"
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(AchievementCategory), nullable=False)
    rarity = Column(Enum(AchievementRarity), nullable=False)
    icon = Column(String(10), default="")
    criteria = Column(JSON, nullable=False)  # e.g. {"type": "win_count", "threshold": 1}
    xp_reward = Column(Integer, default=10)

    def __repr__(self):
        return f"<Achievement(id={self.id}, name={self.name})>"


class UserAchievement(Base):
    """User's unlocked achievement."""

    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    achievement_id = Column(String(50), ForeignKey("achievements.id"), nullable=False)
    unlocked_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    trade_context = Column(JSON, nullable=True)  # Context of the trade that triggered it

    # Relationships
    character = relationship(
        "TradingCharacter",
        primaryjoin="foreign(UserAchievement.user_id) == TradingCharacter.user_id",
        back_populates="achievements",
    )
    achievement = relationship("Achievement", lazy="joined")

    __table_args__ = (
        UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),
    )


class Quest(Base):
    """Quest template — global definitions."""

    __tablename__ = "quests"

    id = Column(String(50), primary_key=True)  # e.g. "daily_journal_2"
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    quest_type = Column(Enum(QuestType), nullable=False)
    criteria = Column(JSON, nullable=False)  # e.g. {"type": "journal_with_notes", "count": 2}
    xp_reward = Column(Integer, default=20)

    def __repr__(self):
        return f"<Quest(id={self.id}, name={self.name})>"


class UserQuest(Base):
    """User's active/completed quest."""

    __tablename__ = "user_quests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    quest_id = Column(String(50), ForeignKey("quests.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress = Column(JSON, default=dict)  # e.g. {"current": 1, "target": 2}
    status = Column(Enum(QuestStatus), default=QuestStatus.ACTIVE)

    # Relationships
    character = relationship(
        "TradingCharacter",
        primaryjoin="foreign(UserQuest.user_id) == TradingCharacter.user_id",
        back_populates="quests",
    )
    quest = relationship("Quest", lazy="joined")

    __table_args__ = (
        Index("ix_user_quests_user_status", "user_id", "status"),
    )


class LeaderboardEntry(Base):
    """Leaderboard snapshot."""

    __tablename__ = "leaderboard_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    period_type = Column(Enum(PeriodType), nullable=False)
    period_start = Column(Date, nullable=False)

    # Stats
    xp = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    achievement_count = Column(Integer, default=0)
    rank_position = Column(Integer, nullable=True)

    # Timestamps
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "period_type", "period_start", name="uq_leaderboard_entry"),
        Index("ix_leaderboard_period", "period_type", "period_start"),
    )
