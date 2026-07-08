"""Service helpers for journal import route orchestration."""

import json
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException

from core.i18n import t
from domain.journal.models import Journal as JournalModel
from domain.journal.schemas import JournalCreate
from services.journal_importer import MAX_IMPORT_ROWS, build_journal_payload


def parse_journal_import_mapping(mapping_json: str, locale: str) -> Dict[str, str]:
    try:
        raw_mapping = json.loads(mapping_json or "{}")
        if not isinstance(raw_mapping, dict):
            raise ValueError("mapping_json must be an object")
        mapping: Dict[str, str] = {
            str(k): str(v)
            for k, v in raw_mapping.items()
            if v is not None and str(v).strip()
        }
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=t("errors.invalid_mapping_json", locale, error=str(exc)),
        ) from exc

    if "symbol" not in mapping or "direction" not in mapping:
        raise HTTPException(
            status_code=400, detail=t("errors.mapping_missing_symbol_direction", locale)
        )

    return mapping


def clamp_import_max_rows(max_rows: int) -> int:
    if max_rows < 1 or max_rows > MAX_IMPORT_ROWS:
        return MAX_IMPORT_ROWS
    return max_rows


def build_journal_import_models(
    rows: List[Dict[str, object]],
    mapping: Dict[str, str],
    *,
    user_id: UUID,
    project_id: Optional[str],
    strict: bool,
    locale: str,
) -> tuple[List[JournalModel], int, List[str]]:
    created_models: List[JournalModel] = []
    errors: List[str] = []
    skipped = 0

    for idx, row in enumerate(rows, start=2):
        payload, error = build_journal_payload(row, mapping, project_id=project_id)
        if error:
            msg = t("messages.import_row_error", locale, row=idx, error=error)
            if strict:
                raise HTTPException(status_code=400, detail=msg)
            skipped += 1
            if len(errors) < 50:
                errors.append(msg)
            continue

        try:
            entry = JournalCreate(**payload)
        except Exception as exc:
            msg = t("messages.import_row_error", locale, row=idx, error=str(exc))
            if strict:
                raise HTTPException(status_code=400, detail=msg)
            skipped += 1
            if len(errors) < 50:
                errors.append(msg)
            continue

        model_data = entry.dict(exclude_none=True)
        created_models.append(JournalModel(user_id=user_id, **model_data))

    return created_models, skipped, errors
