"""Journal import service regressions."""

import pytest
from fastapi import HTTPException

from services.journal_import_service import (
    clamp_import_max_rows,
    parse_journal_import_mapping,
)
from services.journal_importer import MAX_IMPORT_ROWS


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
