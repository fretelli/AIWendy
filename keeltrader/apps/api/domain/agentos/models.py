from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class PortfolioAccount(Base):
    __tablename__ = "portfolio_accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(160), nullable=False)
    account_type = Column(String(30), nullable=False, default="manual")
    base_currency = Column(String(12), nullable=False, default="CNY")
    status = Column(String(30), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_portfolio_accounts_user_status", "user_id", "status", "updated_at"),)


class PortfolioInstrument(Base):
    __tablename__ = "portfolio_instruments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(80), nullable=False)
    name = Column(String(160), nullable=False)
    market = Column(String(30), nullable=False)
    asset_class = Column(String(40), nullable=False)
    currency = Column(String(12), nullable=False, default="CNY")
    direction = Column(String(12), nullable=False, default="long")
    multiplier = Column(Numeric(24, 8), nullable=False, default=1)
    expiry = Column(Date, nullable=True)
    strike = Column(Numeric(24, 8), nullable=True)
    option_type = Column(String(12), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_portfolio_instrument_user_symbol", "user_id", "symbol", "market", unique=True),
        Index("ix_portfolio_instrument_user_asset", "user_id", "asset_class"),
    )


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_instruments.id", ondelete="RESTRICT"), nullable=True)
    transaction_type = Column(String(30), nullable=False)
    trade_date = Column(Date, nullable=False)
    quantity = Column(Numeric(28, 10), nullable=False, default=0)
    price = Column(Numeric(28, 10), nullable=True)
    cash_amount = Column(Numeric(28, 10), nullable=False, default=0)
    fee = Column(Numeric(24, 8), nullable=False, default=0)
    currency = Column(String(12), nullable=False, default="CNY")
    external_ref = Column(String(160), nullable=True)
    note = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("ix_portfolio_transactions_user_date", "user_id", "trade_date", "created_at"),
        Index("ix_portfolio_transactions_account_date", "account_id", "trade_date", "created_at"),
        Index("uq_portfolio_transactions_external", "account_id", "external_ref", unique=True),
    )


class PortfolioImportBatch(Base):
    __tablename__ = "portfolio_import_batches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False)
    import_type = Column(String(30), nullable=False)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)
    mapping_json = Column(JSON, nullable=False, default=dict)
    rows_json = Column(JSON, nullable=False, default=list)
    row_count = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="preview")
    error_json = Column(JSON, nullable=False, default=list)
    committed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_portfolio_import_user_hash", "user_id", "account_id", "content_hash", unique=True),
        Index("ix_portfolio_import_user_status", "user_id", "status", "created_at"),
    )


class PortfolioManualPrice(Base):
    __tablename__ = "portfolio_manual_prices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_instruments.id", ondelete="CASCADE"), nullable=False)
    price_date = Column(Date, nullable=False)
    price = Column(Numeric(28, 10), nullable=False)
    currency = Column(String(12), nullable=False)
    source_note = Column(String(240), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_portfolio_manual_price", "user_id", "instrument_id", "price_date", unique=True),
        Index("ix_portfolio_manual_price_lookup", "instrument_id", "price_date"),
    )


class PortfolioDailySnapshot(Base):
    __tablename__ = "portfolio_daily_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("portfolio_accounts.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    base_currency = Column(String(12), nullable=False)
    nav = Column(Numeric(28, 10), nullable=False)
    net_flow = Column(Numeric(28, 10), nullable=False, default=0)
    data_status = Column(String(20), nullable=False, default="complete")
    positions_json = Column(JSON, nullable=False, default=list)
    attribution_json = Column(JSON, nullable=False, default=dict)
    source_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_portfolio_daily_snapshot", "account_id", "snapshot_date", unique=True),
        Index("ix_portfolio_daily_user_date", "user_id", "snapshot_date"),
    )


class ResearchHypothesis(Base):
    __tablename__ = "research_hypotheses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(240), nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    current_version = Column(Integer, nullable=False, default=1)
    review_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_research_hypotheses_user_status", "user_id", "status", "updated_at"),)


class ResearchHypothesisRevision(Base):
    __tablename__ = "research_hypothesis_revisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hypothesis_id = Column(UUID(as_uuid=True), ForeignKey("research_hypotheses.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    thesis = Column(Text, nullable=False)
    falsification = Column(Text, nullable=False)
    evidence_json = Column(JSON, nullable=False, default=list)
    outcome_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(30), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_research_hypothesis_revision", "hypothesis_id", "version", unique=True),)


class DecisionRecord(Base):
    __tablename__ = "decision_records"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(240), nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    current_version = Column(Integer, nullable=False, default=1)
    hypothesis_id = Column(UUID(as_uuid=True), ForeignKey("research_hypotheses.id", ondelete="SET NULL"), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    review_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_decision_records_user_status", "user_id", "status", "updated_at"),)


class DecisionRevision(Base):
    __tablename__ = "decision_revisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decision_records.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    rationale = Column(Text, nullable=False)
    action_json = Column(JSON, nullable=False, default=dict)
    conditions_json = Column(JSON, nullable=False, default=list)
    evidence_json = Column(JSON, nullable=False, default=list)
    attribution_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(30), nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("uq_decision_revision", "decision_id", "version", unique=True),)


class StrategyExperiment(Base):
    __tablename__ = "strategy_experiments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(180), nullable=False)
    template_key = Column(String(40), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    parameters_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_strategy_experiments_user", "user_id", "status", "updated_at"),)


class StrategyRunVersion(Base):
    __tablename__ = "strategy_run_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("strategy_experiments.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String(30), nullable=False, default="queued")
    parameters_json = Column(JSON, nullable=False, default=dict)
    data_snapshot = Column(JSON, nullable=False, default=dict)
    metrics_json = Column(JSON, nullable=False, default=dict)
    series_json = Column(JSON, nullable=False, default=list)
    trades_json = Column(JSON, nullable=False, default=list)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("uq_strategy_run_version", "experiment_id", "version", unique=True),)


class ConsensusSnapshot(Base):
    __tablename__ = "consensus_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_type = Column(String(30), nullable=False)
    subject_code = Column(String(80), nullable=False)
    as_of = Column(Date, nullable=False)
    status = Column(String(30), nullable=False, default="insufficient_evidence")
    claims_json = Column(JSON, nullable=False, default=list)
    summary_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_consensus_user_subject", "user_id", "subject_type", "subject_code", "as_of"),)


class ResearchDocument(Base):
    __tablename__ = "research_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(240), nullable=False)
    document_type = Column(String(40), nullable=False, default="research_note")
    current_version = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="draft")
    agent_artifact_id = Column(UUID(as_uuid=True), ForeignKey("agent_platform_artifacts.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    __table_args__ = (Index("ix_research_documents_user", "user_id", "status", "updated_at"),)


class ResearchDocumentVersion(Base):
    __tablename__ = "research_document_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("research_documents.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    locale = Column(String(12), nullable=False)
    template_version = Column(String(40), nullable=False)
    markdown_body = Column(Text, nullable=False)
    structured_json = Column(JSON, nullable=False, default=dict)
    source_snapshot = Column(JSON, nullable=False, default=dict)
    storage_path = Column(String(500), nullable=True)
    content_sha256 = Column(String(64), nullable=True)
    mime_type = Column(String(120), nullable=False, default="application/pdf")
    size_bytes = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    __table_args__ = (
        Index("uq_research_document_version_locale", "document_id", "version", "locale", unique=True),
        Index("ix_research_document_versions_document", "document_id", "version"),
    )
