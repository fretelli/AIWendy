"""Uploaded file metadata models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class UploadedFile(Base):
    """User-owned uploaded file metadata."""

    __tablename__ = "uploaded_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_category = Column(String(50), nullable=False)
    storage_path = Column(Text, nullable=False, unique=True)
    thumbnail_base64 = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_uploaded_files_user_created", "user_id", "created_at"),
        Index("ix_uploaded_files_storage_path", "storage_path"),
    )

