"""Report management endpoints."""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from core.auth import get_current_user
from core.database import get_db
from core.i18n import get_request_locale, t
from domain.report.models import (Report, ReportSchedule, ReportStatus,
                                  ReportType)
from domain.user.models import User
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from services.report_service import ReportService
from sqlalchemy.orm import Session


# Pydantic models for request/response
class ReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    project_id: Optional[UUID] = None
    report_type: str
    title: str
    subtitle: Optional[str]
    period_start: date
    period_end: date
    summary: Optional[str]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: Optional[float]
    total_pnl: float
    avg_pnl: Optional[float]
    max_profit: Optional[float]
    max_loss: Optional[float]
    avg_mood_before: Optional[float]
    avg_mood_after: Optional[float]
    mood_improvement: Optional[float]
    top_mistakes: List
    top_successes: List
    improvements: List
    ai_analysis: Optional[str]
    ai_recommendations: List
    key_insights: List
    action_items: List
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class GenerateReportRequest(BaseModel):
    report_type: ReportType
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    project_id: Optional[UUID] = None


class ScheduleResponse(BaseModel):
    id: UUID
    user_id: UUID
    daily_enabled: bool
    daily_time: str
    weekly_enabled: bool
    weekly_day: int
    weekly_time: str
    monthly_enabled: bool
    monthly_day: int
    monthly_time: str
    email_notification: bool
    in_app_notification: bool
    include_charts: bool
    include_ai_analysis: bool
    include_coach_feedback: bool
    language: str
    timezone: str
    is_active: bool

    class Config:
        orm_mode = True


class UpdateScheduleRequest(BaseModel):
    daily_enabled: Optional[bool] = None
    daily_time: Optional[str] = None
    weekly_enabled: Optional[bool] = None
    weekly_day: Optional[int] = None
    weekly_time: Optional[str] = None
    monthly_enabled: Optional[bool] = None
    monthly_day: Optional[int] = None
    monthly_time: Optional[str] = None
    email_notification: Optional[bool] = None
    in_app_notification: Optional[bool] = None
    include_charts: Optional[bool] = None
    include_ai_analysis: Optional[bool] = None
    include_coach_feedback: Optional[bool] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


router = APIRouter()


# Report Generation
@router.post("/generate", response_model=ReportResponse)
def generate_report(
    request: GenerateReportRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a report for the current user."""
    locale = get_request_locale(http_request)
    service = ReportService(db)

    try:
        if request.report_type == ReportType.DAILY:
            report = service.generate_daily_report(
                user_id=current_user.id,
                report_date=request.period_start,
                locale=locale,
                project_id=request.project_id,
            )
        elif request.report_type == ReportType.WEEKLY:
            report = service.generate_weekly_report(
                user_id=current_user.id,
                week_start=request.period_start,
                locale=locale,
                project_id=request.project_id,
            )
        elif request.report_type == ReportType.MONTHLY:
            if request.period_start:
                year = request.period_start.year
                month = request.period_start.month
            else:
                year = month = None
            report = service.generate_monthly_report(
                user_id=current_user.id,
                year=year,
                month=month,
                locale=locale,
                project_id=request.project_id,
            )
        else:
            raise HTTPException(
                status_code=400, detail=t("errors.unsupported_report_type", locale)
            )
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=t("errors.report_generation_failed", locale)
        )

    return report


# Report Retrieval
@router.get("", response_model=List[ReportResponse])
@router.get("/", response_model=List[ReportResponse])
def get_reports(
    http_request: Request,
    report_type: Optional[ReportType] = Query(
        None, description="Filter by report type"
    ),
    project_id: Optional[UUID] = Query(None, description="Filter by project_id"),
    limit: int = Query(10, le=50, description="Maximum number of reports to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's reports."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    reports = service.get_user_reports(
        user_id=current_user.id,
        report_type=report_type,
        project_id=project_id,
        limit=limit,
    )
    return reports


@router.get("/latest/{report_type}", response_model=ReportResponse)
def get_latest_report(
    report_type: ReportType,
    http_request: Request,
    project_id: Optional[UUID] = Query(None, description="Optional project scope"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the latest report of a specific type."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    report = service.get_latest_report(
        user_id=current_user.id,
        report_type=report_type,
        project_id=project_id,
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail=t(
                "errors.no_report_found_for_user", locale, report_type=report_type.value
            ),
        )

    return report


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific report."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    report = service.get_report_by_id(report_id)

    if not report:
        raise HTTPException(
            status_code=404, detail=t("errors.report_not_found", locale)
        )

    # Verify user owns this report
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    return report


# Schedule Management
@router.get("/schedule/current", response_model=ScheduleResponse)
def get_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's report schedule preferences."""
    service = ReportService(db)
    schedule = service.get_user_schedule(current_user.id)

    if not schedule:
        # Create default schedule
        schedule = service.create_or_update_schedule(
            user_id=current_user.id, schedule_data={}
        )

    return schedule


@router.put("/schedule", response_model=ScheduleResponse)
def update_schedule(
    request: UpdateScheduleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user's report schedule preferences."""
    service = ReportService(db)

    # Convert request to dict and remove None values
    schedule_data = {k: v for k, v in request.dict().items() if v is not None}

    schedule = service.create_or_update_schedule(
        user_id=current_user.id, schedule_data=schedule_data
    )

    return schedule


# Quick Actions
@router.post("/generate/daily", response_model=ReportResponse)
def generate_daily_report(
    http_request: Request,
    project_id: Optional[UUID] = Query(None, description="Optional project scope"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate yesterday's daily report."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    try:
        report = service.generate_daily_report(
            current_user.id, locale=locale, project_id=project_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=t("errors.report_generation_failed", locale)
        )
    return report


@router.post("/generate/weekly", response_model=ReportResponse)
def generate_weekly_report(
    http_request: Request,
    project_id: Optional[UUID] = Query(None, description="Optional project scope"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate last week's weekly report."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    try:
        report = service.generate_weekly_report(
            current_user.id, locale=locale, project_id=project_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=t("errors.report_generation_failed", locale)
        )
    return report


@router.post("/generate/monthly", response_model=ReportResponse)
def generate_monthly_report(
    http_request: Request,
    project_id: Optional[UUID] = Query(None, description="Optional project scope"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate last month's monthly report."""
    locale = get_request_locale(http_request)
    service = ReportService(db)
    try:
        report = service.generate_monthly_report(
            current_user.id, locale=locale, project_id=project_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=t("errors.report_generation_failed", locale)
        )
    return report


# Report Statistics
@router.get("/stats/overview")
def get_report_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get report generation statistics."""
    service = ReportService(db)

    # Get counts by type
    daily_count = len(
        service.get_user_reports(current_user.id, ReportType.DAILY, limit=100)
    )
    weekly_count = len(
        service.get_user_reports(current_user.id, ReportType.WEEKLY, limit=100)
    )
    monthly_count = len(
        service.get_user_reports(current_user.id, ReportType.MONTHLY, limit=100)
    )

    # Get latest reports
    latest_daily = service.get_latest_report(current_user.id, ReportType.DAILY)
    latest_weekly = service.get_latest_report(current_user.id, ReportType.WEEKLY)
    latest_monthly = service.get_latest_report(current_user.id, ReportType.MONTHLY)

    return {
        "total_reports": daily_count + weekly_count + monthly_count,
        "by_type": {
            "daily": daily_count,
            "weekly": weekly_count,
            "monthly": monthly_count,
        },
        "latest": {
            "daily": latest_daily.created_at if latest_daily else None,
            "weekly": latest_weekly.created_at if latest_weekly else None,
            "monthly": latest_monthly.created_at if latest_monthly else None,
        },
    }
