from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class ResearchCloudConnection(Base):
    __tablename__ = "research_cloud_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    base_url = Column(String(500), nullable=False)
    status = Column(String(32), nullable=False, default="pending")
    client_id = Column(String(100), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    key_prefix = Column(String(64), nullable=True)
    scopes = Column(JSON, nullable=False, default=list)
    plan_code = Column(String(100), nullable=True)
    pending_device_code_encrypted = Column(Text, nullable=True)
    user_code = Column(String(32), nullable=True)
    verification_uri = Column(String(500), nullable=True)
    device_expires_at = Column(DateTime(timezone=True), nullable=True)
    cloud_auto_context = Column(Boolean, nullable=False, default=False)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
