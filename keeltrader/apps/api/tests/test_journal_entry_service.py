"""Journal entry service regressions."""

from datetime import datetime, timezone
from uuid import uuid4

from domain.journal.schemas import (
    JournalCreate,
    JournalUpdate,
    QuickJournalEntry,
    TradeDirection,
    TradeResult,
)
from services.journal_entry_service import (
    apply_journal_update,
    create_journal_model,
    infer_trade_result_from_pnl,
    quick_entry_to_create,
)


def test_infer_trade_result_from_pnl():
    assert infer_trade_result_from_pnl(12.5) == "win"
    assert infer_trade_result_from_pnl(-0.01) == "loss"
    assert infer_trade_result_from_pnl(0) == "breakeven"


def test_create_journal_model_infers_nonzero_pnl_result():
    journal = create_journal_model(
        uuid4(),
        JournalCreate(
            symbol="AAPL",
            direction=TradeDirection.long,
            pnl_amount=3.2,
        ),
    )

    assert journal.result == "win"


def test_create_journal_model_preserves_result_for_zero_pnl():
    journal = create_journal_model(
        uuid4(),
        JournalCreate(
            symbol="AAPL",
            direction=TradeDirection.long,
            result=TradeResult.open,
            pnl_amount=0,
        ),
    )

    assert journal.result == TradeResult.open


def test_apply_journal_update_recalculates_zero_pnl_result():
    journal = create_journal_model(
        uuid4(),
        JournalCreate(
            symbol="AAPL",
            direction=TradeDirection.long,
            result=TradeResult.open,
        ),
    )

    updated = apply_journal_update(
        journal,
        JournalUpdate(
            symbol="MSFT",
            pnl_amount=0,
        ),
    )

    assert updated.symbol == "MSFT"
    assert updated.result == "breakeven"


def test_quick_entry_to_create_maps_fast_fields():
    trade_date = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    entry = quick_entry_to_create(
        QuickJournalEntry(
            symbol="BTCUSDT",
            direction=TradeDirection.short,
            result=TradeResult.loss,
            pnl_amount=-10,
            emotion_after=2,
            violated_rules=True,
            quick_note="chased move",
        ),
        trade_date=trade_date,
    )

    assert entry.symbol == "BTCUSDT"
    assert entry.direction == TradeDirection.short
    assert entry.result == TradeResult.loss
    assert entry.pnl_amount == -10
    assert entry.emotion_after == 2
    assert entry.followed_rules is False
    assert entry.notes == "chased move"
    assert entry.trade_date == trade_date
