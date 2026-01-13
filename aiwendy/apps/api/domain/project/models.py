"""Project domain models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class Project(Base):
    """User project/workspace for grouping data."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    is_default = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = relationship("User", back_populates="projects")

    __table_args__ = (
        Index("ix_projects_user_updated", "user_id", "updated_at"),
        Index("ix_projects_user_default", "user_id", "is_default"),
    )
