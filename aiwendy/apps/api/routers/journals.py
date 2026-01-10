"""Trading journal endpoints."""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.logging import get_logger
from domain.user.models import User
from domain.journal.models import Journal as JournalModel
from domain.journal.schemas import (
    JournalCreate,
    JournalUpdate,
    JournalResponse,
    JournalListResponse,
    JournalStatistics,
    JournalFilter,
    QuickJournalEntry,
)
from domain.journal.repository import JournalRepository
from services.journal_ai_analyzer import JournalAIAnalyzer
from services.journal_importer import (
    MAX_IMPORT_ROWS,
    MAX_PREVIEW_ROWS,
    parse_tabular_file,
    suggest_mapping,
    build_journal_payload,
)
from services.llm_router import LLMRouter

router = APIRouter()
logger = get_logger(__name__)


class JournalImportPreviewResponse(BaseModel):
    columns: List[str]
    sample_rows: List[Dict[str, str]]
    suggested_mapping: Dict[str, Optional[str]]
    warnings: List[str] = Field(default_factory=list)


class JournalImportResponse(BaseModel):
    created: int
    skipped: int
    errors: List[str] = Field(default_factory=list)


@router.post("", response_model=JournalResponse)
@router.post("/", response_model=JournalResponse)
async def create_journal_entry(
    entry: JournalCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new journal entry."""
    try:
        repo = JournalRepository(session)

        # Create journal model
        journal = JournalModel(
            user_id=current_user.id,
            **entry.dict()
        )

        # Calculate computed fields
        if journal.pnl_amount:
            if journal.pnl_amount > 0:
                journal.result = "win"
            elif journal.pnl_amount < 0:
                journal.result = "loss"
            else:
                journal.result = "breakeven"

        # Save to database
        journal = await repo.create(journal)

        logger.info(f"Created journal entry {journal.id} for user {current_user.id}")

        return JournalResponse.from_orm(journal)

    except Exception as e:
        logger.error(f"Failed to create journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create journal entry"
        )


@router.get("", response_model=JournalListResponse)
@router.get("/", response_model=JournalListResponse)
async def list_journal_entries(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    project_id: Optional[UUID] = Query(None),
    symbol: Optional[str] = Query(None),
    direction: Optional[str] = Query(None),
    result: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List user's journal entries with filtering."""
    try:
        repo = JournalRepository(session)

        # Build filter
        filter_params = None
        if any([project_id, symbol, direction, result, date_from, date_to]):
            filter_params = JournalFilter(
                project_id=project_id,
                symbol=symbol,
                direction=direction,
                result=result,
                date_from=date_from,
                date_to=date_to,
            )

        # Calculate offset
        offset = (page - 1) * per_page

        # Get journals
        journals, total = await repo.get_user_journals(
            user_id=current_user.id,
            filter_params=filter_params,
            limit=per_page,
            offset=offset
        )

        # Convert to response models
        items = [JournalResponse.from_orm(j) for j in journals]

        return JournalListResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page
        )

    except Exception as e:
        logger.error(f"Failed to list journal entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list journal entries"
        )


@router.get("/statistics", response_model=JournalStatistics)
async def get_journal_statistics(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get user's trading statistics."""
    try:
        repo = JournalRepository(session)
        stats = await repo.get_user_statistics(current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.post("/import/preview", response_model=JournalImportPreviewResponse)
async def preview_journal_import(
    file: UploadFile = File(...),
    preview_rows: int = Query(20, ge=1, le=MAX_PREVIEW_ROWS),
    current_user: User = Depends(get_current_user),
):
    """Preview an import file and return detected columns plus a suggested mapping."""
    del current_user

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    parsed = parse_tabular_file(file.filename, content, max_rows=preview_rows)
    suggested = suggest_mapping(parsed.columns)

    sample_rows: List[Dict[str, str]] = []
    for row in parsed.rows[:preview_rows]:
        sample_rows.append({col: str(row.get(col, "") or "") for col in parsed.columns})

    return JournalImportPreviewResponse(
        columns=parsed.columns,
        sample_rows=sample_rows,
        suggested_mapping=suggested,
        warnings=parsed.warnings,
    )


@router.post("/import", response_model=JournalImportResponse)
async def import_journal_entries(
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
    project_id: Optional[str] = Form(None),
    strict: bool = Form(False),
    dry_run: bool = Form(False),
    max_rows: int = Form(MAX_IMPORT_ROWS),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Import journal entries from a CSV/XLSX file using a client-provided column mapping.

    - `mapping_json`: JSON dict like {"symbol":"Symbol","direction":"Side",...}
    - `strict`: stop on first invalid row (otherwise skip invalid rows)
    - `dry_run`: validate only, do not write to DB
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    if project_id is not None and not project_id.strip():
        project_id = None

    try:
        raw_mapping = json.loads(mapping_json or "{}")
        if not isinstance(raw_mapping, dict):
            raise ValueError("mapping_json must be an object")
        mapping: Dict[str, str] = {
            str(k): str(v) for k, v in raw_mapping.items() if v is not None and str(v).strip()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid mapping_json: {e}")

    if "symbol" not in mapping or "direction" not in mapping:
        raise HTTPException(status_code=400, detail="Mapping must include 'symbol' and 'direction'")

    if max_rows < 1 or max_rows > MAX_IMPORT_ROWS:
        max_rows = MAX_IMPORT_ROWS

    content = await file.read()
    parsed = parse_tabular_file(file.filename, content, max_rows=max_rows)

    created_models: List[JournalModel] = []
    errors: List[str] = []
    skipped = 0

    for idx, row in enumerate(parsed.rows, start=2):
        payload, error = build_journal_payload(row, mapping, project_id=project_id)
        if error:
            msg = f"Row {idx}: {error}"
            if strict:
                raise HTTPException(status_code=400, detail=msg)
            skipped += 1
            if len(errors) < 50:
                errors.append(msg)
            continue

        try:
            entry = JournalCreate(**payload)
        except Exception as e:
            msg = f"Row {idx}: {e}"
            if strict:
                raise HTTPException(status_code=400, detail=msg)
            skipped += 1
            if len(errors) < 50:
                errors.append(msg)
            continue

        model_data: Dict[str, Any] = entry.dict(exclude_none=True)
        journal = JournalModel(user_id=current_user.id, **model_data)
        created_models.append(journal)

    if not dry_run and created_models:
        try:
            session.add_all(created_models)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to import journal entries: {e}")
            raise HTTPException(status_code=500, detail="Failed to import journal entries")

    return JournalImportResponse(
        created=len(created_models),
        skipped=skipped,
        errors=errors + parsed.warnings,
    )


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal_entry(
    journal_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get journal entry details."""
    try:
        repo = JournalRepository(session)
        journal = await repo.get_by_id(journal_id, current_user.id)

        if not journal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )

        return JournalResponse.from_orm(journal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get journal entry"
        )


@router.put("/{journal_id}", response_model=JournalResponse)
async def update_journal_entry(
    journal_id: UUID,
    entry: JournalUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update journal entry."""
    try:
        repo = JournalRepository(session)
        journal = await repo.get_by_id(journal_id, current_user.id)

        if not journal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )

        # Update fields
        for field, value in entry.dict(exclude_unset=True).items():
            setattr(journal, field, value)

        # Recalculate result if PnL changed
        if entry.pnl_amount is not None:
            if entry.pnl_amount > 0:
                journal.result = "win"
            elif entry.pnl_amount < 0:
                journal.result = "loss"
            else:
                journal.result = "breakeven"

        # Save changes
        journal = await repo.update(journal)

        return JournalResponse.from_orm(journal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update journal entry"
        )


@router.delete("/{journal_id}")
async def delete_journal_entry(
    journal_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete journal entry (soft delete)."""
    try:
        repo = JournalRepository(session)
        success = await repo.delete(journal_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )

        return {"message": "Journal entry deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete journal entry"
        )


@router.post("/quick", response_model=JournalResponse)
async def create_quick_journal_entry(
    entry: QuickJournalEntry,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a quick journal entry for fast logging."""
    try:
        repo = JournalRepository(session)

        # Create full journal from quick entry
        journal_data = JournalCreate(
            symbol=entry.symbol,
            direction=entry.direction,
            result=entry.result,
            pnl_amount=entry.pnl_amount,
            emotion_after=entry.emotion_after,
            followed_rules=not entry.violated_rules,
            notes=entry.quick_note,
            trade_date=datetime.utcnow()
        )

        journal = JournalModel(
            user_id=current_user.id,
            **journal_data.dict()
        )

        journal = await repo.create(journal)

        logger.info(f"Created quick journal entry {journal.id} for user {current_user.id}")

        return JournalResponse.from_orm(journal)

    except Exception as e:
        logger.error(f"Failed to create quick journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quick journal entry"
        )


@router.post("/{journal_id}/analyze")
async def analyze_journal_entry(
    journal_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Analyze a single journal entry with AI."""
    try:
        repo = JournalRepository(session)

        # Get the journal entry
        journal = await repo.get_by_id(journal_id, current_user.id)
        if not journal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Journal entry not found"
            )

        # Get user statistics for context
        stats = await repo.get_user_statistics(current_user.id)

        # Initialize AI analyzer with user's LLM settings
        llm_router = LLMRouter(user=current_user)
        analyzer = JournalAIAnalyzer(llm_router)

        # Perform analysis
        analysis = await analyzer.analyze_single_journal(
            JournalResponse.from_orm(journal),
            stats
        )

        # Update journal with AI insights
        journal.ai_insights = analysis.get("analysis", "")
        journal.detected_patterns = analysis.get("detected_patterns", [])
        await session.commit()

        logger.info(f"Analyzed journal entry {journal_id} for user {current_user.id}")

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze journal entry"
        )


@router.get("/analyze/patterns")
async def analyze_trading_patterns(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Analyze recent trading patterns with AI."""
    try:
        repo = JournalRepository(session)

        # Get recent journal entries
        journals = await repo.get_user_journals(
            user_id=current_user.id,
            limit=limit,
            offset=0
        )

        if not journals:
            return {
                "message": "No journal entries found for analysis",
                "patterns": [],
                "recommendations": []
            }

        # Get user statistics
        stats = await repo.get_user_statistics(current_user.id)

        # Initialize AI analyzer
        llm_router = LLMRouter(user=current_user)
        analyzer = JournalAIAnalyzer(llm_router)

        # Perform pattern analysis
        journal_responses = [JournalResponse.from_orm(j) for j in journals]
        analysis = await analyzer.analyze_recent_trades(journal_responses, stats)

        logger.info(f"Analyzed trading patterns for user {current_user.id}")

        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze trading patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze trading patterns"
        )


@router.get("/analyze/improvement-plan")
async def generate_improvement_plan(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate personalized improvement plan with AI."""
    try:
        repo = JournalRepository(session)

        # Get recent journal entries
        journals = await repo.get_user_journals(
            user_id=current_user.id,
            limit=30,
            offset=0
        )

        if not journals:
            return {
                "message": "Not enough data to generate improvement plan",
                "plan": "Start journaling your trades consistently for at least 10 trades to get a personalized improvement plan."
            }

        # Get user statistics
        stats = await repo.get_user_statistics(current_user.id)

        # Initialize AI analyzer
        llm_router = LLMRouter(user=current_user)
        analyzer = JournalAIAnalyzer(llm_router)

        # Generate improvement plan
        journal_responses = [JournalResponse.from_orm(j) for j in journals]
        plan = await analyzer.generate_improvement_plan(journal_responses, stats)

        logger.info(f"Generated improvement plan for user {current_user.id}")

        return plan

    except Exception as e:
        logger.error(f"Failed to generate improvement plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate improvement plan"
        )
