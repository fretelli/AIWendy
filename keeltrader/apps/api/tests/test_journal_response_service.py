"""Journal response mapping regressions."""

from datetime import datetime, timezone
from uuid import uuid4

from domain.journal.models import (
    Journal,
    TradeDirection as ModelTradeDirection,
    TradeResult as ModelTradeResult,
)
from services.journal_response_service import (
    journal_to_response,
    journals_to_list_response,
)


def make_journal(symbol="AAPL"):
    now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    return Journal(
        id=uuid4(),
        user_id=uuid4(),
        symbol=symbol,
        direction=ModelTradeDirection.LONG,
        result=ModelTradeResult.WIN,
        pnl_amount=12.5,
        followed_rules=True,
        rule_violations=[],
        tags=[],
        screenshots=[],
        trade_date=now,
        created_at=now,
        updated_at=now,
    )


def test_journal_to_response_uses_pydantic_v2_validation():
    journal = make_journal()

    response = journal_to_response(journal)

    assert response.id == journal.id
    assert response.user_id == journal.user_id
    assert response.symbol == "AAPL"
    assert response.direction == "long"
    assert response.result == "win"


def test_journals_to_list_response_preserves_pagination_shape():
    response = journals_to_list_response(
        [make_journal("AAPL"), make_journal("MSFT")],
        total=7,
        page=2,
        per_page=2,
    )

    assert response.total == 7
    assert response.page == 2
    assert response.per_page == 2
    assert [item.symbol for item in response.items] == ["AAPL", "MSFT"]
