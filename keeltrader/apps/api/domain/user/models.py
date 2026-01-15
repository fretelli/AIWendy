"""User domain models."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class SubscriptionTier(str, enum.Enum):
    """User subscription tiers."""

    free = "free"
    pro = "pro"
    elite = "elite"
    enterprise = "enterprise"


class TradingType(str, enum.Enum):
    """Types of trading."""

    STOCKS = "stocks"
    FUTURES = "futures"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTIONS = "options"
    OTHER = "other"


class User(Base):
    """User model."""

    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255), nullable=True)

    # Profile
    full_name = Column(String(255), nullable=True)
    display_name = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")

    # Trading preferences
    trading_types = Column(JSON, default=list)  # List of TradingType
    main_concern = Column(Text, nullable=True)  # Main trading concern
    preferred_coach_id = Column(String(50), nullable=True)
    preferred_coach_style = Column(String(50), nullable=True)

    # Subscription
    subscription_tier = Column(
        Enum(SubscriptionTier),
        default=SubscriptionTier.free,
        nullable=False,
    )
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)

    # API Keys (encrypted)
    openai_api_key = Column(Text, nullable=True)  # Encrypted
    anthropic_api_key = Column(Text, nullable=True)  # Encrypted
    api_keys_encrypted = Column(JSON, nullable=True, default={})  # For future providers

    # Settings
    notification_preferences = Column(
        JSON,
        default={
            "email_daily_summary": False,
            "email_weekly_report": True,
            "push_notifications": True,
            "sms_alerts": False,
        },
    )
    privacy_settings = Column(
        JSON,
        default={
            "share_analytics": True,
            "public_profile": False,
        },
    )

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete

    # Relationships - Using string references to avoid circular imports
    projects = relationship("Project", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user")
    reports = relationship("Report", back_populates="user")
    report_schedule = relationship(
        "ReportSchedule", back_populates="user", uselist=False
    )
    sessions = relationship("UserSession", back_populates="user")
    exchange_connections = relationship("ExchangeConnection", back_populates="user")

    # Indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
        Index("ix_users_subscription", "subscription_tier", "subscription_expires_at"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"

    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription."""
        return self.subscription_tier != SubscriptionTier.free

    @property
    def is_subscription_active(self) -> bool:
        """Check if subscription is active."""
        if self.subscription_tier == SubscriptionTier.free:
            return True
        if self.subscription_expires_at is None:
            return False
        return self.subscription_expires_at > datetime.utcnow()


class UserSession(Base):
    """User session model for tracking."""

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Session info
    access_token = Column(Text, nullable=False, unique=True)
    refresh_token = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Index
    __table_args__ = (Index("ix_user_sessions_user_active", "user_id", "expires_at"),)

    user = relationship("User", back_populates="sessions")
