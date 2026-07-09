"""AI analysis orchestration for journal routes."""

from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.i18n import t
from domain.journal.models import Journal as JournalModel
from domain.journal.repository import JournalRepository
from domain.journal.schemas import JournalResponse
from domain.user.models import User

AnalysisPayload = Dict[str, Any]
AnalyzerFactory = Callable[[User], Any]


def create_journal_analyzer(user: User) -> Any:
    from services.journal_ai_analyzer import JournalAIAnalyzer
    from services.llm_router import LLMRouter

    return JournalAIAnalyzer(LLMRouter(user=user))


async def analyze_journal_with_ai(
    repo: JournalRepository,
    session: AsyncSession,
    user: User,
    journal: JournalModel,
    analyzer_factory: AnalyzerFactory = create_journal_analyzer,
) -> AnalysisPayload:
    """Analyze one journal and persist AI insights back to the entry."""
    stats = await repo.get_user_statistics(user.id)
    analyzer = analyzer_factory(user)
    analysis = await analyzer.analyze_single_journal(
        JournalResponse.model_validate(journal), stats
    )

    journal.ai_insights = analysis.get("analysis", "")
    journal.detected_patterns = analysis.get("detected_patterns", [])
    await session.commit()

    return analysis


async def analyze_recent_trades_with_ai(
    repo: JournalRepository,
    user: User,
    limit: int,
    analyzer_factory: AnalyzerFactory = create_journal_analyzer,
) -> Optional[AnalysisPayload]:
    """Analyze recent journal entries, returning None when no data exists."""
    journals, _ = await repo.get_user_journals(user_id=user.id, limit=limit, offset=0)
    if not journals:
        return None

    stats = await repo.get_user_statistics(user.id)
    analyzer = analyzer_factory(user)
    journal_responses = [
        JournalResponse.model_validate(journal) for journal in journals
    ]
    return await analyzer.analyze_recent_trades(journal_responses, stats)


async def generate_journal_improvement_plan(
    repo: JournalRepository,
    user: User,
    analyzer_factory: AnalyzerFactory = create_journal_analyzer,
) -> Optional[AnalysisPayload]:
    """Generate an improvement plan, returning None when no journal data exists."""
    journals, _ = await repo.get_user_journals(user_id=user.id, limit=30, offset=0)
    if not journals:
        return None

    stats = await repo.get_user_statistics(user.id)
    analyzer = analyzer_factory(user)
    journal_responses = [
        JournalResponse.model_validate(journal) for journal in journals
    ]
    return await analyzer.generate_improvement_plan(journal_responses, stats)


async def analyze_journal_entry_for_user(
    repo: JournalRepository,
    session: AsyncSession,
    user: User,
    journal_id: Any,
    locale: str,
) -> AnalysisPayload:
    """Fetch and analyze one journal entry for route handlers."""
    journal = await repo.get_by_id(journal_id, user.id)
    if not journal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=t("errors.journal_entry_not_found", locale),
        )

    return await analyze_journal_with_ai(repo, session, user, journal)


async def analyze_recent_trades_or_fallback(
    repo: JournalRepository,
    user: User,
    limit: int,
    locale: str,
) -> AnalysisPayload:
    """Analyze recent trades or return the existing no-data response."""
    analysis = await analyze_recent_trades_with_ai(repo, user, limit)
    if analysis is None:
        return {
            "message": t("messages.no_journal_entries_for_analysis", locale),
            "patterns": [],
            "recommendations": [],
        }
    return analysis


async def generate_improvement_plan_or_fallback(
    repo: JournalRepository,
    user: User,
    locale: str,
) -> AnalysisPayload:
    """Generate an improvement plan or return the existing no-data response."""
    plan = await generate_journal_improvement_plan(repo, user)
    if plan is None:
        return {
            "message": t("messages.not_enough_data_for_improvement_plan", locale),
            "plan": t("messages.improvement_plan_start_journaling", locale),
        }
    return plan
