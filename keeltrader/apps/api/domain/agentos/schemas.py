"""AgentOS API schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class BriefRunRequest(BaseModel):
    watchlist: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    project_id: UUID | None = None


class ResearchRunRequest(BaseModel):
    symbol: str
    market: str | None = None
    project_id: UUID | None = None


class DecisionCreateRequest(BaseModel):
    symbol: str
    action: str
    thesis: str
    market: str | None = None
    project_id: UUID | None = None
    memo_id: UUID | None = None
    confidence: float | None = None
    expected_horizon: str | None = None
    position_plan: dict[str, Any] = Field(default_factory=dict)
    risk_plan: dict[str, Any] = Field(default_factory=dict)
    falsifiers: list[Any] = Field(default_factory=list)
    human_decision: str = "pending"
    human_reason: str | None = None


class DecisionOutcomeRequest(BaseModel):
    outcome: dict[str, Any] = Field(default_factory=dict)


class HypothesisCreateRequest(BaseModel):
    name: str
    hypothesis: str
    rationale: str | None = None
    project_id: UUID | None = None
    asset_universe: list[str] = Field(default_factory=list)
    frequency: str = "daily"


class FundamentalValidationRequest(BaseModel):
    symbol: str
    strategy: str = "fundamental_validation"
    params: dict[str, Any] = Field(default_factory=dict)
    hypothesis_id: UUID | None = None


class TushareQueryRequest(BaseModel):
    table: str
    filters: dict[str, Any] = Field(default_factory=dict)
    limit: int = 50


class ReportSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    companies: list[str] = Field(default_factory=list)
