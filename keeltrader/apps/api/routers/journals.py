"""Trading journal endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_authenticated_user, get_current_user
from core.database import get_session
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.journal.repository import JournalRepository
from domain.journal.schemas import (
    JournalCreate,
    JournalFilter,
    JournalImportPreviewResponse,
    JournalImportResponse,
    JournalListResponse,
    JournalResponse,
    JournalStatistics,
    JournalUpdate,
    QuickJournalEntry,
)
from domain.user.models import User
from services.journal_importer import (
    MAX_IMPORT_ROWS,
    MAX_PREVIEW_ROWS,
)
from services.journal_import_service import (
    import_journal_file,
    preview_journal_import_file,
)
from services.journal_analysis_service import (
    analyze_journal_entry_for_user,
    analyze_recent_trades_or_fallback,
    generate_improvement_plan_or_fallback,
)
from services.journal_entry_service import (
    apply_journal_update,
    create_journal_model,
    quick_entry_to_create,
)
from services.journal_response_service import (
    journal_to_response,
    journals_to_list_response,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=JournalResponse)
@router.post("/", response_model=JournalResponse)
async def create_journal_entry(
    entry: JournalCreate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Create a new journal entry."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)

        journal = create_journal_model(current_user.id, entry)
        journal = await repo.create(journal)

        logger.info(f"Created journal entry {journal.id} for user {current_user.id}")

        return journal_to_response(journal)

    except Exception as e:
        logger.error(f"Failed to create journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_create_journal_entry", locale),
        )


@router.get("", response_model=JournalListResponse)
@router.get("/", response_model=JournalListResponse)
async def list_journal_entries(
    http_request: Request,
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
    locale = get_request_locale(http_request)
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
            offset=offset,
        )

        return journals_to_list_response(
            journals,
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as e:
        logger.error(f"Failed to list journal entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_list_journal_entries", locale),
        )


@router.get("/statistics", response_model=JournalStatistics)
async def get_journal_statistics(
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get user's trading statistics."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)
        stats = await repo.get_user_statistics(current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_get_journal_statistics", locale),
        )


@router.post("/import/preview", response_model=JournalImportPreviewResponse)
async def preview_journal_import(
    http_request: Request,
    file: UploadFile = File(...),
    preview_rows: int = Query(20, ge=1, le=MAX_PREVIEW_ROWS),
    current_user: User = Depends(get_current_user),
):
    """Preview an import file and return detected columns plus a suggested mapping."""
    del current_user

    locale = get_request_locale(http_request)

    content = await file.read()
    return preview_journal_import_file(
        file.filename,
        content,
        preview_rows=preview_rows,
        locale=locale,
    )


@router.post("/import", response_model=JournalImportResponse)
async def import_journal_entries(
    http_request: Request,
    file: UploadFile = File(...),
    mapping_json: str = Form(...),
    project_id: Optional[str] = Form(None),
    strict: bool = Form(False),
    dry_run: bool = Form(False),
    max_rows: int = Form(MAX_IMPORT_ROWS),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """
    Import journal entries from a CSV/XLSX file using a client-provided column mapping.

    - `mapping_json`: JSON dict like {"symbol":"Symbol","direction":"Side",...}
    - `strict`: stop on first invalid row (otherwise skip invalid rows)
    - `dry_run`: validate only, do not write to DB
    """
    locale = get_request_locale(http_request)
    content = await file.read()
    return await import_journal_file(
        session,
        file.filename,
        content,
        mapping_json=mapping_json,
        project_id=project_id,
        strict=strict,
        dry_run=dry_run,
        max_rows=max_rows,
        user_id=current_user.id,
        locale=locale,
    )


@router.get("/{journal_id}", response_model=JournalResponse)
async def get_journal_entry(
    journal_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get journal entry details."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)
        journal = await repo.get_by_id(journal_id, current_user.id)

        if not journal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("errors.journal_entry_not_found", locale),
            )

        return journal_to_response(journal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_get_journal_entry", locale),
        )


@router.put("/{journal_id}", response_model=JournalResponse)
async def update_journal_entry(
    journal_id: UUID,
    entry: JournalUpdate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Update journal entry."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)
        journal = await repo.get_by_id(journal_id, current_user.id)

        if not journal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("errors.journal_entry_not_found", locale),
            )

        apply_journal_update(journal, entry)
        journal = await repo.update(journal)

        return journal_to_response(journal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_update_journal_entry", locale),
        )


@router.delete("/{journal_id}")
async def delete_journal_entry(
    journal_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Delete journal entry (soft delete)."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)
        success = await repo.delete(journal_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=t("errors.journal_entry_not_found", locale),
            )

        return {"message": t("messages.journal_entry_deleted", locale)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_delete_journal_entry", locale),
        )


@router.post("/quick", response_model=JournalResponse)
async def create_quick_journal_entry(
    entry: QuickJournalEntry,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Create a quick journal entry for fast logging."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)

        journal_data = quick_entry_to_create(entry)
        journal = create_journal_model(current_user.id, journal_data)
        journal = await repo.create(journal)

        logger.info(
            f"Created quick journal entry {journal.id} for user {current_user.id}"
        )

        return journal_to_response(journal)

    except Exception as e:
        logger.error(f"Failed to create quick journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_create_quick_journal_entry", locale),
        )


@router.post("/{journal_id}/analyze")
async def analyze_journal_entry(
    journal_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Analyze a single journal entry with AI."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)

        analysis = await analyze_journal_entry_for_user(
            repo, session, current_user, journal_id, locale
        )

        logger.info(f"Analyzed journal entry {journal_id} for user {current_user.id}")

        return analysis

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze journal entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_analyze_journal_entry", locale),
        )


@router.get("/analyze/patterns")
async def analyze_trading_patterns(
    http_request: Request,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Analyze recent trading patterns with AI."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)

        analysis = await analyze_recent_trades_or_fallback(
            repo, current_user, limit, locale
        )

        logger.info(f"Analyzed trading patterns for user {current_user.id}")

        return analysis

    except Exception as e:
        logger.error(f"Failed to analyze trading patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_analyze_trading_patterns", locale),
        )


@router.get("/analyze/improvement-plan")
async def generate_improvement_plan(
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate personalized improvement plan with AI."""
    locale = get_request_locale(http_request)
    try:
        repo = JournalRepository(session)

        plan = await generate_improvement_plan_or_fallback(repo, current_user, locale)

        logger.info(f"Generated improvement plan for user {current_user.id}")

        return plan

    except Exception as e:
        logger.error(f"Failed to generate improvement plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=t("errors.failed_to_generate_improvement_plan", locale),
        )
