"""Knowledge base domain models."""

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from core.database import Base


class KnowledgeDocument(Base):
    """A user-provided document for a project knowledge base."""

    __tablename__ = "knowledge_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    title = Column(String(255), nullable=False)
    source_type = Column(String(50), default="text")  # text/file/url
    source_name = Column(Text, nullable=True)

    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict)

    chunk_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_kb_documents_user_project_created",
            "user_id",
            "project_id",
            "created_at",
        ),
        Index("ix_kb_documents_user_title", "user_id", "title"),
    )


class KnowledgeChunk(Base):
    """A chunk of a knowledge document with embedding metadata."""

    __tablename__ = "knowledge_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("knowledge_documents.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    embedding_vector = Column(Vector, nullable=True)
    embedding_dim = Column(Integer, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    embedding_provider = Column(String(50), nullable=True)
    token_count = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        Index("ix_kb_chunks_document_index", "document_id", "chunk_index"),
        Index(
            "ix_kb_chunks_user_project_created", "user_id", "project_id", "created_at"
        ),
        Index(
            "ix_kb_chunks_user_project_dim", "user_id", "project_id", "embedding_dim"
        ),
    )
