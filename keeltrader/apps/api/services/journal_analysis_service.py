"""AI analysis orchestration for journal routes."""

from typing import Any, Callable, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

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
