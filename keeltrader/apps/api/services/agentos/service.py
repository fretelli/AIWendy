"""Application facade for AgentOS workflows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from domain.agentos.models import (
    BacktestRun,
    InvestmentBrief,
    InvestmentDecision,
    InvestmentMemo,
    ReviewLesson,
    StrategyHypothesis,
)
from services.agentos.decisions import AgentOSDecisionService
from services.agentos.research import AgentOSResearchService
from services.agentos.strategy import AgentOSStrategyService


class AgentOSService:
    """Compatibility facade over focused AgentOS workflow services."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.research = AgentOSResearchService(session)
        self.decisions = AgentOSDecisionService(session)
        self.strategy = AgentOSStrategyService(session)

    async def run_daily_brief(
        self,
        user_id: UUID,
        watchlist: list[str] | None = None,
        project_id: UUID | None = None,
    ) -> InvestmentBrief:
        return await self.research.run_daily_brief(user_id, watchlist, project_id)

    async def latest_brief(self, user_id: UUID) -> InvestmentBrief | None:
        return await self.research.latest_brief(user_id)

    async def run_deep_research(
        self,
        user_id: UUID,
        symbol: str,
        market: str | None = None,
        project_id: UUID | None = None,
    ) -> InvestmentMemo:
        return await self.research.run_deep_research(user_id, symbol, market, project_id)

    async def search_reports(
        self,
        query: str,
        top_k: int = 5,
        companies: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return await self.research.search_reports(query, top_k, companies)

    async def get_memo(self, user_id: UUID, memo_id: UUID) -> InvestmentMemo | None:
        return await self.research.get_memo(user_id, memo_id)

    async def record_decision(self, user_id: UUID, payload: dict[str, Any]) -> InvestmentDecision:
        return await self.decisions.record_decision(user_id, payload)

    async def update_decision_outcome(
        self,
        user_id: UUID,
        decision_id: UUID,
        outcome: dict[str, Any],
    ) -> InvestmentDecision | None:
        return await self.decisions.update_decision_outcome(user_id, decision_id, outcome)

    async def run_weekly_review(self, user_id: UUID, project_id: UUID | None = None) -> list[ReviewLesson]:
        return await self.decisions.run_weekly_review(user_id, project_id)

    async def approve_lesson(self, user_id: UUID, lesson_id: UUID) -> ReviewLesson | None:
        return await self.decisions.approve_lesson(user_id, lesson_id)

    async def create_hypothesis(self, user_id: UUID, payload: dict[str, Any]) -> StrategyHypothesis:
        return await self.strategy.create_hypothesis(user_id, payload)

    async def record_backtest(
        self,
        user_id: UUID,
        symbol: str,
        strategy: str,
        params: dict[str, Any] | None = None,
        hypothesis_id: UUID | None = None,
    ) -> BacktestRun:
        return await self.strategy.record_backtest(user_id, symbol, strategy, params, hypothesis_id)
