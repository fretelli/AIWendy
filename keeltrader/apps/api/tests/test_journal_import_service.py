"""Journal import service regressions."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from services.journal_import_service import (
    clamp_import_max_rows,
    import_journal_file,
    parse_journal_import_mapping,
    preview_journal_import_file,
)
from services.journal_importer import MAX_IMPORT_ROWS


class FakeSession:
    def __init__(self, *, fail_commit=False):
        self.fail_commit = fail_commit
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def add_all(self, models):
        self.added.extend(models)

    async def commit(self):
        self.commits += 1
        if self.fail_commit:
            raise RuntimeError("db down")

    async def rollback(self):
        self.rollbacks += 1


def test_parse_journal_import_mapping_filters_empty_values():
    assert parse_journal_import_mapping(
        '{"symbol":"Symbol","direction":"Side","notes":"","pnl_amount":null}',
        "en",
    ) == {"symbol": "Symbol", "direction": "Side"}


def test_parse_journal_import_mapping_requires_object():
    with pytest.raises(HTTPException) as exc:
        parse_journal_import_mapping('["symbol"]', "en")

    assert exc.value.status_code == 400


def test_parse_journal_import_mapping_requires_symbol_and_direction():
    with pytest.raises(HTTPException) as exc:
        parse_journal_import_mapping('{"symbol":"Symbol"}', "en")

    assert exc.value.status_code == 400


def test_clamp_import_max_rows_uses_import_limit_for_out_of_range_values():
    assert clamp_import_max_rows(0) == MAX_IMPORT_ROWS
    assert clamp_import_max_rows(MAX_IMPORT_ROWS + 1) == MAX_IMPORT_ROWS
    assert clamp_import_max_rows(25) == 25


def test_preview_journal_import_file_returns_sample_and_mapping():
    response = preview_journal_import_file(
        "trades.csv",
        b"Symbol,Side,Notes\nAAPL,long,good entry\nMSFT,short,late\n",
        preview_rows=1,
        locale="en",
    )

    assert response.columns == ["Symbol", "Side", "Notes"]
    assert response.sample_rows == [
        {"Symbol": "AAPL", "Side": "long", "Notes": "good entry"}
    ]
    assert response.suggested_mapping["symbol"] == "Symbol"
    assert response.suggested_mapping["direction"] == "Side"


def test_preview_journal_import_file_requires_filename():
    with pytest.raises(HTTPException) as exc:
        preview_journal_import_file(
            None,
            b"Symbol,Side\nAAPL,long\n",
            preview_rows=1,
            locale="en",
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_import_journal_file_dry_run_does_not_write():
    session = FakeSession()

    response = await import_journal_file(
        session,
        "trades.csv",
        b"Symbol,Side,PnL\nAAPL,long,12.5\n",
        mapping_json='{"symbol":"Symbol","direction":"Side","pnl_amount":"PnL"}',
        project_id="   ",
        strict=False,
        dry_run=True,
        max_rows=10,
        user_id=uuid4(),
        locale="en",
    )

    assert response.created == 1
    assert response.skipped == 0
    assert session.added == []
    assert session.commits == 0


@pytest.mark.asyncio
async def test_import_journal_file_persists_valid_rows():
    session = FakeSession()

    response = await import_journal_file(
        session,
        "trades.csv",
        b"Symbol,Side,PnL\nAAPL,long,12.5\n",
        mapping_json='{"symbol":"Symbol","direction":"Side","pnl_amount":"PnL"}',
        project_id=None,
        strict=False,
        dry_run=False,
        max_rows=10,
        user_id=uuid4(),
        locale="en",
    )

    assert response.created == 1
    assert len(session.added) == 1
    assert session.commits == 1
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_import_journal_file_rolls_back_on_commit_failure():
    session = FakeSession(fail_commit=True)

    with pytest.raises(HTTPException) as exc:
        await import_journal_file(
            session,
            "trades.csv",
            b"Symbol,Side,PnL\nAAPL,long,12.5\n",
            mapping_json='{"symbol":"Symbol","direction":"Side","pnl_amount":"PnL"}',
            project_id=None,
            strict=False,
            dry_run=False,
            max_rows=10,
            user_id=uuid4(),
            locale="en",
        )

    assert exc.value.status_code == 500
    assert session.rollbacks == 1
