"""Coach domain models."""

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
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class CoachStyle(str, enum.Enum):
    """Coach interaction styles."""

    EMPATHETIC = "empathetic"  # 温和共情型
    DISCIPLINED = "disciplined"  # 严厉纪律型
    ANALYTICAL = "analytical"  # 数据分析型
    MOTIVATIONAL = "motivational"  # 激励鼓舞型
    SOCRATIC = "socratic"  # 苏格拉底问答型


class LLMProvider(str, enum.Enum):
    """LLM provider options."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


class Coach(Base):
    """Coach model."""

    __tablename__ = "coaches"

    # Primary key
    id = Column(String(50), primary_key=True)  # e.g., "wendy", "marcus"

    # Basic info
    name = Column(String(100), nullable=False)
    avatar_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)  # Detailed background

    # Style and personality
    style = Column(Enum(CoachStyle), nullable=False)
    personality_traits = Column(JSON, default=list)  # List of traits
    specialty = Column(JSON, default=list)  # List of specialties
    language = Column(String(10), default="en")

    # LLM configuration
    llm_provider = Column(
        Enum(
            LLMProvider,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            name="llmprovider",
        ),
        default=LLMProvider.OPENAI,
    )
    llm_model = Column(String(100), nullable=False)  # e.g., "gpt-4o-mini"
    system_prompt = Column(Text, nullable=False)
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)

    # Voice configuration (for future TTS)
    voice_id = Column(String(100), nullable=True)
    voice_settings = Column(JSON, nullable=True)

    # Access control
    is_premium = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    min_subscription_tier = Column(String(20), default="free")
    created_by = Column(UUID(as_uuid=True), nullable=True)  # For custom coaches

    # Statistics
    total_sessions = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    avg_rating = Column(Float, nullable=True)
    rating_count = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="coach", lazy="dynamic")

    # Indexes
    __table_args__ = (
        Index("ix_coaches_style_active", "style", "is_active"),
        Index("ix_coaches_public_premium", "is_public", "is_premium"),
    )

    def __repr__(self):
        return f"<Coach(id={self.id}, name={self.name}, style={self.style})>"


class ChatSession(Base):
    """Chat session between user and coach."""

    __tablename__ = "chat_sessions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    coach_id = Column(String(50), ForeignKey("coaches.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)

    # Session info
    title = Column(String(200), nullable=True)
    context = Column(JSON, nullable=True)  # Additional context for the session
    mood_before = Column(Integer, nullable=True)  # 1-5 scale
    mood_after = Column(Integer, nullable=True)  # 1-5 scale

    # Statistics
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    user_feedback = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    coach = relationship("Coach", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", lazy="dynamic")
    project = relationship("Project", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_chat_sessions_user_created", "user_id", "created_at"),
        Index(
            "ix_chat_sessions_user_project_created",
            "user_id",
            "project_id",
            "created_at",
        ),
        Index("ix_chat_sessions_coach_active", "coach_id", "is_active"),
    )


class ChatMessage(Base):
    """Individual chat messages."""

    __tablename__ = "chat_messages"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False
    )

    # Message content
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)

    # Attachments
    has_attachments = Column(Boolean, default=False)

    # Metadata
    message_metadata = Column(JSON, nullable=True)  # Additional message metadata
    detected_emotions = Column(JSON, nullable=True)  # Detected emotions
    detected_patterns = Column(JSON, nullable=True)  # Detected behavior patterns

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    attachments = relationship(
        "ChatAttachment", back_populates="message", lazy="selectin"
    )

    # Indexes
    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )


class AttachmentType(str, enum.Enum):
    """Attachment type options."""

    IMAGE = "image"
    AUDIO = "audio"
    PDF = "pdf"
    WORD = "word"
    EXCEL = "excel"
    PPT = "ppt"
    TEXT = "text"
    CODE = "code"
    FILE = "file"  # Generic file


class ChatAttachment(Base):
    """Chat message attachments (images, audio, documents, etc.)."""

    __tablename__ = "chat_attachments"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign key
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=False
    )

    # Attachment info
    attachment_type = Column(
        String(20), nullable=False
    )  # 'image', 'audio', 'pdf', etc.
    file_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)

    # Storage
    storage_path = Column(Text, nullable=False)  # Path in storage system

    # Extracted content (for text-based files)
    extracted_text = Column(Text, nullable=True)  # Extracted text from PDF/Office/etc.
    transcription = Column(Text, nullable=True)  # Audio transcription

    # For images: base64 thumbnail
    thumbnail_base64 = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    message = relationship("ChatMessage", back_populates="attachments")

    # Indexes
    __table_args__ = (Index("ix_chat_attachments_message", "message_id"),)


# ============= Roundtable Discussion Models =============


class CoachPreset(Base):
    """Preset combinations of coaches for roundtable discussions."""

    __tablename__ = "coach_presets"

    # Primary key
    id = Column(String(50), primary_key=True)  # e.g., "all_stars", "rational"

    # Basic info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Icon name for frontend

    # Coach configuration
    coach_ids = Column(JSON, nullable=False)  # Array of coach IDs

    # Display
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<CoachPreset(id={self.id}, name={self.name})>"


class RoundtableSession(Base):
    """Roundtable discussion session with multiple coaches."""

    __tablename__ = "roundtable_sessions"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    preset_id = Column(String(50), ForeignKey("coach_presets.id"), nullable=True)

    # Session info
    title = Column(String(200), nullable=True)
    coach_ids = Column(JSON, nullable=False)  # Array of participating coach IDs
    turn_order = Column(
        JSON, nullable=True
    )  # Custom turn order (defaults to coach_ids)
    current_turn = Column(Integer, default=0)  # Index of current coach in turn_order

    # Moderator mode settings
    discussion_mode = Column(String(20), default="free")  # "free" or "moderated"
    moderator_id = Column(
        String(50), ForeignKey("coaches.id"), nullable=True
    )  # Host coach ID

    # Session-level LLM overrides (optional; request-level can override these)
    llm_config_id = Column(
        String(100), nullable=True
    )  # User LLM config id (from /llm-config)
    llm_provider = Column(
        String(50), nullable=True
    )  # Preferred provider hint (e.g. openai/ollama/custom)
    llm_model = Column(String(200), nullable=True)
    llm_temperature = Column(Float, nullable=True)
    llm_max_tokens = Column(Integer, nullable=True)

    # Knowledge base retrieval settings (optional)
    kb_timing = Column(String(20), default="off")  # off|message|round|coach|moderator
    kb_top_k = Column(Integer, default=5)
    kb_max_candidates = Column(Integer, default=400)

    # Statistics
    message_count = Column(Integer, default=0)
    round_count = Column(Integer, default=0)  # Number of discussion rounds completed

    # Status
    is_active = Column(Boolean, default=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user = relationship("User", backref="roundtable_sessions")
    project = relationship("Project", lazy="joined")
    preset = relationship("CoachPreset", lazy="joined")
    moderator = relationship("Coach", foreign_keys=[moderator_id], lazy="joined")
    messages = relationship(
        "RoundtableMessage",
        back_populates="session",
        lazy="dynamic",
        order_by="RoundtableMessage.created_at",
    )

    # Indexes
    __table_args__ = (
        Index("ix_roundtable_sessions_user_created", "user_id", "created_at"),
        Index("ix_roundtable_sessions_active", "is_active"),
    )

    def __repr__(self):
        return f"<RoundtableSession(id={self.id}, coaches={self.coach_ids})>"


class RoundtableMessage(Base):
    """Messages in roundtable discussions."""

    __tablename__ = "roundtable_messages"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign keys
    session_id = Column(
        UUID(as_uuid=True), ForeignKey("roundtable_sessions.id"), nullable=False
    )
    coach_id = Column(
        String(50), ForeignKey("coaches.id"), nullable=True
    )  # NULL = user message

    # Message content
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    attachments = Column(
        JSON, nullable=True
    )  # Optional list of uploaded attachments metadata

    # Message type for moderator mode
    # 'response' = regular coach response (default)
    # 'opening' = moderator opening statement
    # 'summary' = moderator round summary
    # 'closing' = moderator closing remarks
    message_type = Column(String(20), default="response")

    # Discussion tracking
    turn_number = Column(
        Integer, nullable=True
    )  # Which round of discussion (1, 2, 3...)
    sequence_in_turn = Column(
        Integer, nullable=True
    )  # Order within the turn (0, 1, 2...)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    session = relationship("RoundtableSession", back_populates="messages")
    coach = relationship("Coach", lazy="joined")

    # Indexes
    __table_args__ = (
        Index("ix_roundtable_messages_session_created", "session_id", "created_at"),
        Index("ix_roundtable_messages_turn", "session_id", "turn_number"),
    )

    def __repr__(self):
        return f"<RoundtableMessage(id={self.id}, coach={self.coach_id}, role={self.role})>"
