"""AgentOS fundamental thesis experiment workflows."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agentos.models import FundamentalValidationRun, StrategyHypothesis
from services.agentos.tushare_read import TushareReadService


class AgentOSStrategyService:
    """Fundamental hypotheses and validation records."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tushare = TushareReadService(session)

    async def create_hypothesis(self, user_id: UUID, payload: dict[str, Any]) -> StrategyHypothesis:
        hypothesis = StrategyHypothesis(
            user_id=user_id,
            project_id=payload.get("project_id"),
            name=payload["name"],
            hypothesis=payload["hypothesis"],
            rationale=payload.get("rationale"),
            asset_universe=payload.get("asset_universe") or [],
            frequency=payload.get("frequency", "daily"),
            status="draft",
        )
        self.session.add(hypothesis)
        await self.session.flush()
        return hypothesis

    async def record_validation(
        self,
        user_id: UUID,
        symbol: str,
        strategy: str,
        params: dict[str, Any] | None = None,
        hypothesis_id: UUID | None = None,
    ) -> FundamentalValidationRun:
        """Persist a fundamental validation record.

        The historical table is reused for compatibility, but this workflow
        performs no chart, momentum, or indicator calculations.
        """
        params = params or {}
        hypothesis = None
        if hypothesis_id:
            result = await self.session.execute(
                select(StrategyHypothesis).where(StrategyHypothesis.id == hypothesis_id, StrategyHypothesis.user_id == user_id)
            )
            hypothesis = result.scalar_one_or_none()

        attempt_number = (hypothesis.attempt_count + 1) if hypothesis else 1
        latest_price = (await self.tushare.daily_bars(symbol, limit=1, adjusted=False))[:1]
        financials = await self.tushare.financial_indicators(symbol, limit=4)
        required_sources = ["stock_basic", "fina_indicator", "report-kb"]
        evidence = params.get("evidence") if isinstance(params.get("evidence"), list) else []
        risks = params.get("risks") if isinstance(params.get("risks"), list) else []
        conclusion = str(params.get("conclusion") or "observe")
        passed_gate = conclusion in {"observe", "supported"} and bool(financials) and len(evidence) >= 1
        metrics = {
            "validation_type": "fundamental",
            "conclusion": conclusion,
            "evidence_count": len(evidence),
            "risk_count": len(risks),
            "has_recent_financials": bool(financials),
            "has_latest_price_context": bool(latest_price),
            "required_sources": required_sources,
            "research_only": True,
        }
        notes = str(
            params.get("notes")
            or "Fundamental validation record persisted; no chart signal or trading signal was generated."
        )
        if hypothesis:
            hypothesis.attempt_count = attempt_number
            hypothesis.status = "observing" if passed_gate else "tested"

        run = FundamentalValidationRun(
            user_id=user_id,
            hypothesis_id=hypothesis_id,
            symbol=symbol,
            strategy=strategy or "fundamental_validation",
            params=params,
            metrics=metrics,
            trades=[],
            attempt_number=attempt_number,
            passed_gate=passed_gate,
            notes=notes,
        )
        self.session.add(run)
        await self.session.flush()
        return run
