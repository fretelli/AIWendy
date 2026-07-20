from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class AgentDefinition(Base):
    __tablename__ = "agent_platform_definitions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    role = Column(String(50), nullable=False, default="custom")
    model_profile_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_model_profiles.id"), nullable=True)
    tool_names = Column(JSON, nullable=False, default=list)
    memory_enabled = Column(Boolean, nullable=False, default=True)
    max_steps = Column(Integer, nullable=False, default=12)
    max_parallel = Column(Integer, nullable=False, default=3)
    task_token_budget = Column(Integer, nullable=False, default=50000)
    task_cost_budget_usd = Column(Float, nullable=False, default=5.0)
    is_template = Column(Boolean, nullable=False, default=False)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_definitions_user", "user_id", "created_at"),)


class AgentSession(Base):
    __tablename__ = "agent_platform_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_definition_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_definitions.id"), nullable=True)
    title = Column(String(200), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    interaction_mode = Column(String(20), nullable=False, default="ask")
    company_code = Column(String(20), nullable=True)
    summary = Column(Text, nullable=True)
    context_tokens = Column(Integer, nullable=False, default=0)
    is_pinned = Column(Boolean, nullable=False, default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    last_message_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_sessions_user", "user_id", "updated_at"),)


class AgentMessage(Base):
    __tablename__ = "agent_platform_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="SET NULL"), nullable=True)
    kind = Column(String(30), nullable=False, default="message")
    status = Column(String(30), nullable=False, default="completed")
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_messages_session", "session_id", "created_at"),)


class AgentContextSnapshot(Base):
    """Immutable, user-owned evidence handoff selected explicitly in a market workspace."""
    __tablename__ = "agent_context_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(40), nullable=False)
    resource_id = Column(String(120), nullable=False)
    field = Column(String(80), nullable=True)
    visible_start = Column(String(32), nullable=True)
    visible_end = Column(String(32), nullable=True)
    selected_point = Column(JSON, nullable=True)
    source = Column(String(240), nullable=False)
    methodology = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_context_snapshots_user", "user_id", "created_at"),)


class AgentRun(Base):
    __tablename__ = "agent_platform_runs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_sessions.id", ondelete="CASCADE"), nullable=False)
    agent_definition_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_definitions.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    interaction_mode = Column(String(20), nullable=False, default="ask")
    status = Column(String(30), nullable=False, default="queued")
    plan = Column(JSON, nullable=False, default=list)
    checkpoint = Column(JSON, nullable=False, default=dict)
    current_step = Column(Integer, nullable=False, default=0)
    token_budget = Column(Integer, nullable=False, default=50000)
    cost_budget_usd = Column(Float, nullable=False, default=5.0)
    tokens_used = Column(Integer, nullable=False, default=0)
    cost_used_usd = Column(Float, nullable=False, default=0.0)
    lease_owner = Column(String(100), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    generation = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(120), nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("ix_agent_platform_runs_user", "user_id", "created_at"),
        Index("ix_agent_platform_runs_status", "status", "created_at"),
    )


class AgentRunStep(Base):
    __tablename__ = "agent_platform_run_steps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="CASCADE"), nullable=False)
    sequence = Column(Integer, nullable=False)
    agent_role = Column(String(50), nullable=False)
    tool_name = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    input_json = Column(JSON, nullable=False, default=dict)
    output_json = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    idempotency_key = Column(String(160), nullable=False, unique=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_steps_run", "run_id", "sequence"),)


class AgentRunEvent(Base):
    __tablename__ = "agent_platform_run_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(60), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_events_run", "run_id", "id"),)


class AgentApproval(Base):
    __tablename__ = "agent_platform_approvals"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_run_steps.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(40), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    preview = Column(JSON, nullable=False, default=dict)
    decision_scope = Column(String(30), nullable=True)
    reason = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_approvals_user", "user_id", "status", "created_at"),)


class AgentArtifact(Base):
    __tablename__ = "agent_platform_artifacts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="CASCADE"), nullable=False)
    artifact_type = Column(String(50), nullable=False)
    title = Column(String(240), nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_artifacts_user", "user_id", "created_at"),)


class AgentMemory(Base):
    __tablename__ = "agent_platform_memories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_definition_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_definitions.id"), nullable=True)
    key = Column(String(200), nullable=False)
    value = Column(JSON, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.5)
    version = Column(Integer, nullable=False, default=1)
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_memories_user", "user_id", "is_deleted", "updated_at"),)


class AgentMemoryVersion(Base):
    __tablename__ = "agent_platform_memory_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_memories.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    value = Column(JSON, nullable=False)
    evidence = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_memory_versions", "memory_id", "version", unique=True),)


class AgentModelProfile(Base):
    __tablename__ = "agent_platform_model_profiles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(120), nullable=False)
    provider = Column(String(30), nullable=False)
    base_url = Column(String(500), nullable=True)
    model = Column(String(160), nullable=False)
    api_key_encrypted = Column(Text, nullable=True)
    credential_source = Column(String(20), nullable=False, default="byok")
    managed_slug = Column(String(80), nullable=True, unique=True)
    key_prefix = Column(String(32), nullable=True)
    context_window = Column(Integer, nullable=False)
    max_output_tokens = Column(Integer, nullable=False)
    input_cost_per_million = Column(Float, nullable=False)
    output_cost_per_million = Column(Float, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_models_user", "user_id", "created_at"),)


class AgentCompanyWatchlist(Base):
    __tablename__ = "agent_company_watchlist"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_code = Column(String(20), nullable=False)
    company_name = Column(String(120), nullable=False)
    industry = Column(String(120), nullable=True)
    refresh_enabled = Column(Boolean, nullable=False, default=True)
    added_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("ix_agent_company_watchlist_user", "user_id", "added_at"),
        Index("uq_agent_company_watchlist_user_code", "user_id", "company_code", unique=True),
    )


class AgentHolderWatchlist(Base):
    __tablename__ = "agent_holder_watchlist"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    holder_name = Column(String(500), nullable=False)
    normalized_name = Column(String(500), nullable=False)
    holder_type = Column(String(80), nullable=False, default="未知")
    aliases = Column(JSON, nullable=False, default=list)
    enabled = Column(Boolean, nullable=False, default=True)
    last_scanned_at = Column(DateTime(timezone=True), nullable=True)
    last_source_watermark = Column(String(80), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("ix_agent_holder_watchlist_user", "user_id", "created_at"),
        Index("uq_agent_holder_watchlist_user_match", "user_id", "normalized_name", "holder_type", unique=True),
    )


class AgentHolderEvent(Base):
    __tablename__ = "agent_holder_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    watch_id = Column(UUID(as_uuid=True), ForeignKey("agent_holder_watchlist.id", ondelete="CASCADE"), nullable=False)
    event_key = Column(String(64), nullable=False)
    ts_code = Column(String(20), nullable=False)
    company_name = Column(String(120), nullable=True)
    holder_name = Column(String(500), nullable=False)
    holder_type = Column(String(80), nullable=False, default="未知")
    event_type = Column(String(40), nullable=False)
    end_date = Column(String(8), nullable=False)
    ann_date = Column(String(8), nullable=True)
    previous_end_date = Column(String(8), nullable=True)
    values = Column(JSON, nullable=False, default=dict)
    read_at = Column(DateTime(timezone=True), nullable=True)
    detected_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_agent_holder_event_period", "watch_id", "ts_code", "end_date", unique=True),
        Index("ix_agent_holder_events_user_unread", "user_id", "read_at", "detected_at"),
        Index("ix_agent_holder_events_watch", "watch_id", "end_date"),
    )


class AgentCompanyDossier(Base):
    __tablename__ = "agent_company_dossiers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_code = Column(String(20), nullable=False)
    company_name = Column(String(120), nullable=False)
    industry = Column(String(120), nullable=True)
    current_version = Column(Integer, nullable=False, default=0)
    source_fingerprint = Column(String(64), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    stale = Column(Boolean, nullable=False, default=True)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    calculation_version = Column(String(40), nullable=True)
    financial_as_of = Column(String(20), nullable=True)
    calculation_errors = Column(JSON, nullable=False, default=list)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_agent_company_dossier_user_code", "user_id", "company_code", unique=True),)


class AgentBackgroundJob(Base):
    __tablename__ = "agent_background_jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(40), nullable=False)
    entity_key = Column(String(240), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(String(30), nullable=False, default="queued")
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    available_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    lease_owner = Column(String(120), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        Index("ix_agent_background_jobs_claim", "status", "available_at", "lease_expires_at"),
        Index("ix_agent_background_jobs_entity", "kind", "entity_key"),
    )


class AgentCompanyDossierVersion(Base):
    __tablename__ = "agent_company_dossier_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("agent_company_dossiers.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    source_fingerprint = Column(String(64), nullable=False)
    snapshot = Column(JSON, nullable=False)
    diff = Column(JSON, nullable=False, default=dict)
    calculation_version = Column(String(40), nullable=False, default="fundamental-v2")
    financial_as_of = Column(String(20), nullable=True)
    quality = Column(JSON, nullable=False, default=dict)
    calculation_errors = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_agent_company_dossier_version", "dossier_id", "version", unique=True),)


class AgentCompanyEvidence(Base):
    __tablename__ = "agent_company_evidence"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dossier_version_id = Column(UUID(as_uuid=True), ForeignKey("agent_company_dossier_versions.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(30), nullable=False)
    citation = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_company_evidence_version", "dossier_version_id"),)


class AgentMCPServer(Base):
    __tablename__ = "agent_platform_mcp_servers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    url = Column(String(500), nullable=False)
    auth_encrypted = Column(Text, nullable=True)
    auth_prefix = Column(String(32), nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    tools_snapshot = Column(JSON, nullable=False, default=list)
    schema_digest = Column(String(64), nullable=True)
    allow_private_network = Column(Boolean, nullable=False, default=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_mcp_user", "user_id", "created_at"),)


class AgentToolGrant(Base):
    __tablename__ = "agent_platform_tool_grants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_definition_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_definitions.id"), nullable=True)
    mcp_server_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_mcp_servers.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(160), nullable=False)
    scope = Column(String(30), nullable=False, default="always")
    schema_digest = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_grants_unique", "user_id", "mcp_server_id", "tool_name", "agent_definition_id", unique=True),)


class AgentSchedule(Base):
    __tablename__ = "agent_platform_schedules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_definition_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_definitions.id"), nullable=False)
    name = Column(String(160), nullable=False)
    prompt = Column(Text, nullable=False)
    cron = Column(String(80), nullable=False)
    timezone = Column(String(80), nullable=False, default="Asia/Shanghai")
    enabled = Column(Boolean, nullable=False, default=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_schedules_due", "enabled", "next_run_at"),)


class AgentUsageLedger(Base):
    __tablename__ = "agent_platform_usage_ledger"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_runs.id", ondelete="SET NULL"), nullable=True)
    model_profile_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_model_profiles.id", ondelete="SET NULL"), nullable=True)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_agent_platform_usage_user", "user_id", "created_at"),)
