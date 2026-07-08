"""Pure helpers for journal entry creation and updates."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.journal.models import Journal as JournalModel
from domain.journal.schemas import JournalCreate, JournalUpdate, QuickJournalEntry


def infer_trade_result_from_pnl(pnl_amount: float) -> str:
    """Infer a closed trade result from a PnL amount."""
    if pnl_amount > 0:
        return "win"
    if pnl_amount < 0:
        return "loss"
    return "breakeven"


def create_journal_model(user_id: UUID, entry: JournalCreate) -> JournalModel:
    """Create a journal model from a validated create payload."""
    journal = JournalModel(user_id=user_id, **entry.model_dump())

    if journal.pnl_amount:
        journal.result = infer_trade_result_from_pnl(journal.pnl_amount)

    return journal


def apply_journal_update(journal: JournalModel, entry: JournalUpdate) -> JournalModel:
    """Apply a validated update payload to an existing journal model."""
    update_data = entry.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(journal, field, value)

    pnl_amount = update_data.get("pnl_amount")
    if pnl_amount is not None:
        journal.result = infer_trade_result_from_pnl(pnl_amount)

    return journal


def quick_entry_to_create(
    entry: QuickJournalEntry, trade_date: Optional[datetime] = None
) -> JournalCreate:
    """Convert a quick-entry payload into the full journal create schema."""
    return JournalCreate(
        symbol=entry.symbol,
        direction=entry.direction,
        result=entry.result,
        pnl_amount=entry.pnl_amount,
        emotion_after=entry.emotion_after,
        followed_rules=not entry.violated_rules,
        notes=entry.quick_note,
        trade_date=trade_date or datetime.utcnow(),
    )
