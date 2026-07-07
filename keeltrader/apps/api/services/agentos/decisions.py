"""AgentOS decision journal and review workflows."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agentos.models import InvestmentDecision, ReviewLesson


class AgentOSDecisionService:
    """Decision logging and review workflows."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_decision(self, user_id: UUID, payload: dict[str, Any]) -> InvestmentDecision:
        human_decision = payload.get("human_decision", "pending")
        decision = InvestmentDecision(
            user_id=user_id,
            project_id=payload.get("project_id"),
            memo_id=payload.get("memo_id"),
            symbol=payload["symbol"],
            market=payload.get("market"),
            action=payload["action"],
            thesis=payload["thesis"],
            confidence=payload.get("confidence"),
            expected_horizon=payload.get("expected_horizon"),
            position_plan=payload.get("position_plan") or {},
            risk_plan=payload.get("risk_plan") or {},
            falsifiers=payload.get("falsifiers") or [],
            human_decision=human_decision,
            human_reason=payload.get("human_reason"),
            decided_at=datetime.utcnow() if human_decision != "pending" else None,
        )
        self.session.add(decision)
        await self.session.flush()
        return decision

    async def update_decision_outcome(
        self,
        user_id: UUID,
        decision_id: UUID,
        outcome: dict[str, Any],
    ) -> InvestmentDecision | None:
        result = await self.session.execute(
            select(InvestmentDecision).where(InvestmentDecision.id == decision_id, InvestmentDecision.user_id == user_id)
        )
        decision = result.scalar_one_or_none()
        if not decision:
            return None
        decision.outcome = outcome
        decision.status = outcome.get("status", "reviewed")
        decision.reviewed_at = datetime.utcnow()
        await self.session.flush()
        return decision

    async def run_weekly_review(self, user_id: UUID, project_id: UUID | None = None) -> list[ReviewLesson]:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=7)
        result = await self.session.execute(
            select(InvestmentDecision).where(
                InvestmentDecision.user_id == user_id,
                InvestmentDecision.created_at >= period_start,
                InvestmentDecision.created_at <= period_end,
            )
        )
        decisions = list(result.scalars().all())
        open_count = sum(1 for d in decisions if d.status == "open")
        accepted = sum(1 for d in decisions if d.human_decision == "accepted")
        rejected = sum(1 for d in decisions if d.human_decision == "rejected")

        lesson = ReviewLesson(
            user_id=user_id,
            project_id=project_id,
            period_start=period_start,
            period_end=period_end,
            title="Weekly decision discipline review",
            lesson=(
                f"Reviewed {len(decisions)} decision(s): {accepted} accepted, "
                f"{rejected} rejected, {open_count} still open. "
                "Approve this lesson only if it reflects a real behavioral pattern."
            ),
            evidence=[
                {"decision_id": str(d.id), "symbol": d.symbol, "action": d.action, "status": d.status}
                for d in decisions[:20]
            ],
            category="discipline",
            approved=False,
        )
        self.session.add(lesson)
        await self.session.flush()
        return [lesson]

    async def approve_lesson(self, user_id: UUID, lesson_id: UUID) -> ReviewLesson | None:
        result = await self.session.execute(
            select(ReviewLesson).where(ReviewLesson.id == lesson_id, ReviewLesson.user_id == user_id)
        )
        lesson = result.scalar_one_or_none()
        if not lesson:
            return None
        lesson.approved = True
        lesson.approved_at = datetime.utcnow()
        await self.session.flush()
        return lesson
