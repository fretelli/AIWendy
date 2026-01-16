"""Exchange connection domain models."""

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
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class ExchangeType(str, enum.Enum):
    """Supported exchange types."""

    BINANCE = "binance"
    OKX = "okx"
    BYBIT = "bybit"
    COINBASE = "coinbase"
    KRAKEN = "kraken"


class ExchangeConnection(Base):
    """User's exchange API connection."""

    __tablename__ = "exchange_connections"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="exchange_connections")

    # Exchange info
    exchange_type = Column(Enum(ExchangeType), nullable=False)
    name = Column(String(100), nullable=True)  # User-defined name like "My Binance Account"

    # API credentials (encrypted)
    api_key_encrypted = Column(Text, nullable=False)
    api_secret_encrypted = Column(Text, nullable=False)
    passphrase_encrypted = Column(Text, nullable=True)  # For exchanges like OKX

    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_testnet = Column(Boolean, default=False, nullable=False)  # Testnet vs production

    # Metadata
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("idx_exchange_connections_user_id", "user_id"),
        Index("idx_exchange_connections_user_exchange", "user_id", "exchange_type"),
    )

    def __repr__(self):
        return f"<ExchangeConnection(id={self.id}, user_id={self.user_id}, exchange={self.exchange_type})>"
