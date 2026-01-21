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
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
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
    exchange_trades = relationship("ExchangeTrade", back_populates="exchange_connection")

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
    sync_symbols = Column(JSON, default=list)

    # Metadata
    last_sync_at = Column(DateTime, nullable=True)
    last_trade_sync_at = Column(DateTime, nullable=True)
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


class ExchangeTrade(Base):
    """Raw trade data pulled from exchanges."""

    __tablename__ = "exchange_trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exchange_connection_id = Column(
        UUID(as_uuid=True), ForeignKey("exchange_connections.id"), nullable=False
    )
    journal_id = Column(UUID(as_uuid=True), ForeignKey("journals.id"), nullable=True)

    exchange_trade_id = Column(String(200), nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=True)
    price = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    cost = Column(Float, nullable=True)
    fee_cost = Column(Float, nullable=True)
    fee_currency = Column(String(20), nullable=True)
    fee_rate = Column(Float, nullable=True)
    trade_timestamp = Column(DateTime(timezone=True), nullable=True)

    raw = Column(JSON, nullable=True)
    is_imported = Column(Boolean, default=False, nullable=False)
    imported_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    exchange_connection = relationship(
        "ExchangeConnection", back_populates="exchange_trades"
    )

    __table_args__ = (
        Index(
            "ix_exchange_trades_connection_trade_id",
            "exchange_connection_id",
            "exchange_trade_id",
            unique=True,
        ),
        Index("ix_exchange_trades_user_time", "user_id", "trade_timestamp"),
        Index("ix_exchange_trades_symbol", "symbol"),
    )

    def __repr__(self):
        return (
            f"<ExchangeTrade(id={self.id}, exchange_trade_id={self.exchange_trade_id}, symbol={self.symbol})>"
        )
