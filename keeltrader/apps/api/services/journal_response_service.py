"""Response mapping helpers for journal routes."""

from collections.abc import Sequence

from domain.journal.models import Journal as JournalModel
from domain.journal.schemas import JournalListResponse, JournalResponse


def journal_to_response(journal: JournalModel) -> JournalResponse:
    """Convert a journal ORM model to its public response schema."""
    return JournalResponse.model_validate(journal)


def journals_to_list_response(
    journals: Sequence[JournalModel],
    *,
    total: int,
    page: int,
    per_page: int,
) -> JournalListResponse:
    """Convert journal ORM rows to the paginated public response schema."""
    return JournalListResponse(
        items=[journal_to_response(journal) for journal in journals],
        total=total,
        page=page,
        per_page=per_page,
    )
