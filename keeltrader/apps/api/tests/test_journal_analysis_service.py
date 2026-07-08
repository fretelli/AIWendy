"""Journal AI analysis orchestration regressions."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from domain.journal.models import (
    Journal,
    TradeDirection as ModelTradeDirection,
    TradeResult as ModelTradeResult,
)
from domain.journal.schemas import JournalStatistics
from services.journal_analysis_service import (
    analyze_journal_with_ai,
    analyze_recent_trades_with_ai,
    generate_journal_improvement_plan,
)


class FakeRepo:
    def __init__(self, journals):
        self.journals = journals
        self.statistics_calls = 0
        self.journal_limits = []

    async def get_user_journals(self, user_id, limit, offset):
        del user_id, offset
        self.journal_limits.append(limit)
        return self.journals, len(self.journals)

    async def get_user_statistics(self, user_id):
        del user_id
        self.statistics_calls += 1
        return JournalStatistics(total_trades=len(self.journals))


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class FakeAnalyzer:
    def __init__(self):
        self.recent_trade_count = 0
        self.plan_trade_count = 0

    async def analyze_single_journal(self, journal, stats):
        del journal, stats
        return {"analysis": "tight stop worked", "detected_patterns": ["discipline"]}

    async def analyze_recent_trades(self, journals, stats):
        del stats
        self.recent_trade_count = len(journals)
        return {"patterns": ["late_entry"], "recommendations": ["wait"]}

    async def generate_improvement_plan(self, journals, stats):
        del stats
        self.plan_trade_count = len(journals)
        return {"plan": "reduce size after rule breaks"}


def make_journal(user_id):
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    return Journal(
        id=uuid4(),
        user_id=user_id,
        symbol="AAPL",
        direction=ModelTradeDirection.LONG,
        result=ModelTradeResult.WIN,
        pnl_amount=1.5,
        followed_rules=True,
        rule_violations=[],
        tags=[],
        screenshots=[],
        trade_date=now,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_analyze_journal_with_ai_persists_insights():
    user = SimpleNamespace(id=uuid4())
    journal = make_journal(user.id)
    repo = FakeRepo([journal])
    session = FakeSession()
    analyzer = FakeAnalyzer()

    result = await analyze_journal_with_ai(
        repo,
        session,
        user,
        journal,
        analyzer_factory=lambda _: analyzer,
    )

    assert result["analysis"] == "tight stop worked"
    assert journal.ai_insights == "tight stop worked"
    assert journal.detected_patterns == ["discipline"]
    assert session.commits == 1
    assert repo.statistics_calls == 1


@pytest.mark.asyncio
async def test_analyze_recent_trades_returns_none_without_journals():
    user = SimpleNamespace(id=uuid4())
    repo = FakeRepo([])

    result = await analyze_recent_trades_with_ai(repo, user, 10)

    assert result is None
    assert repo.statistics_calls == 0


@pytest.mark.asyncio
async def test_analyze_recent_trades_passes_only_journal_rows_to_analyzer():
    user = SimpleNamespace(id=uuid4())
    repo = FakeRepo([make_journal(user.id), make_journal(user.id)])
    analyzer = FakeAnalyzer()

    result = await analyze_recent_trades_with_ai(
        repo,
        user,
        10,
        analyzer_factory=lambda _: analyzer,
    )

    assert result == {"patterns": ["late_entry"], "recommendations": ["wait"]}
    assert analyzer.recent_trade_count == 2
    assert repo.journal_limits == [10]


@pytest.mark.asyncio
async def test_generate_journal_improvement_plan_uses_fixed_recent_window():
    user = SimpleNamespace(id=uuid4())
    repo = FakeRepo([make_journal(user.id)])
    analyzer = FakeAnalyzer()

    result = await generate_journal_improvement_plan(
        repo,
        user,
        analyzer_factory=lambda _: analyzer,
    )

    assert result == {"plan": "reduce size after rule breaks"}
    assert analyzer.plan_trade_count == 1
    assert repo.journal_limits == [30]
