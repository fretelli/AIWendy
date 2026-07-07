"""Tests for the file content extraction service."""

import importlib
import warnings
from pathlib import Path

import pytest

from services.file_extractor import (
    can_extract_text,
    extract_text,
    get_file_category,
)


@pytest.mark.parametrize(
    ("module_name", "package_name"),
    [
        ("PyPDF2", "PyPDF2"),
        ("docx", "python-docx"),
        ("openpyxl", "openpyxl"),
        ("pptx", "python-pptx"),
    ],
)
def test_document_extraction_runtime_dependencies_are_available(
    module_name: str, package_name: str
) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        assert importlib.import_module(module_name), f"{package_name} is not installed"


@pytest.mark.asyncio
async def test_extract_text_file_reads_utf8_content(tmp_path: Path) -> None:
    file_path = tmp_path / "memo.txt"
    file_path.write_text("Alpha thesis\nBear case", encoding="utf-8")

    result = await extract_text(file_path, "memo.txt")

    assert result.success is True
    assert result.file_type == "text"
    assert result.text == "Alpha thesis\nBear case"
    assert result.error is None


@pytest.mark.asyncio
async def test_extract_csv_uses_pipe_separated_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "positions.csv"
    file_path.write_text("symbol,weight\nAAPL,0.2\nMSFT,0.3\n", encoding="utf-8")

    result = await extract_text(file_path, "positions.csv")

    assert result.success is True
    assert result.file_type == "csv"
    assert result.text == "symbol | weight\nAAPL | 0.2\nMSFT | 0.3"


def test_binary_file_is_not_extractable() -> None:
    assert get_file_category("archive.zip") == "binary"
    assert can_extract_text("archive.zip") is False


@pytest.mark.asyncio
async def test_extract_binary_file_returns_stable_error(tmp_path: Path) -> None:
    file_path = tmp_path / "archive.zip"
    file_path.write_bytes(b"not a real zip")

    result = await extract_text(file_path, "archive.zip")

    assert result.success is False
    assert result.file_type == "binary"
    assert result.error == "Cannot extract text from binary files"
