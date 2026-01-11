"""Report generation tasks (Celery)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from celery import Task

from core.database import SessionLocal
from core.logging import get_logger
from domain.report.models import Report, ReportSchedule, ReportType
from services.report_service import ReportService
from core.task_events import publish_task_event
from workers.celery_app import celery_app

logger = get_logger(__name__)


def _invalidate_user_report_caches(user_id: str) -> None:
    try:
        from core.cache import get_redis_client

        redis_client = get_redis_client()
        for key in redis_client.scan_iter(match=f"analysis:*:{user_id}:*"):
            redis_client.delete(key)
        for key in redis_client.scan_iter(match=f"reports:*:{user_id}:*"):
            redis_client.delete(key)
    except Exception:
        return


class ReportTask(Task):
    """Base task for report generation."""

    def _get_db(self):
        return SessionLocal()


@celery_app.task(bind=True, base=ReportTask)
def generate_daily_report(
    self,
    user_id: str,
    report_date: Optional[str] = None,
    project_id: Optional[str] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a daily report."""
    task_id = self.request.id
    db = self._get_db()
    now = datetime.utcnow()
    try:
        publish_task_event(task_id, {"task_id": task_id, "state": "STARTED", "ready": False})
        user_uuid = UUID(user_id)
        project_uuid = UUID(project_id) if project_id else None

        if report_date:
            parsed_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        else:
            parsed_date = date.today() - timedelta(days=1)

        service = ReportService(db)
        report = service.generate_daily_report(
            user_id=user_uuid,
            report_date=parsed_date,
            locale=locale,
            project_id=project_uuid,
        )

        schedule = db.query(ReportSchedule).filter(ReportSchedule.user_id == user_uuid).first()
        if schedule:
            schedule.last_daily_generated = now
            db.commit()

        _invalidate_user_report_caches(user_id)
        logger.info("daily_report_generated", user_id=user_id, report_id=str(report.id))
        payload = {
            "status": "success",
            "report_id": str(report.id),
            "report_type": "daily",
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
        publish_task_event(task_id, {"task_id": task_id, "state": "SUCCESS", "ready": True, "successful": True, "result": payload})
        return payload
    except Exception as e:
        db.rollback()
        logger.error("daily_report_failed", user_id=user_id, error=str(e))
        publish_task_event(task_id, {"task_id": task_id, "state": "FAILURE", "ready": True, "successful": False, "error": str(e)})
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, base=ReportTask)
def generate_weekly_report(
    self,
    user_id: str,
    week_start: Optional[str] = None,
    project_id: Optional[str] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a weekly report."""
    task_id = self.request.id
    db = self._get_db()
    now = datetime.utcnow()
    try:
        publish_task_event(task_id, {"task_id": task_id, "state": "STARTED", "ready": False})
        user_uuid = UUID(user_id)
        project_uuid = UUID(project_id) if project_id else None

        if week_start:
            parsed_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        else:
            today = date.today()
            days_since_monday = today.weekday()
            parsed_date = today - timedelta(days=days_since_monday + 7)

        service = ReportService(db)
        report = service.generate_weekly_report(
            user_id=user_uuid,
            week_start=parsed_date,
            locale=locale,
            project_id=project_uuid,
        )

        schedule = db.query(ReportSchedule).filter(ReportSchedule.user_id == user_uuid).first()
        if schedule:
            schedule.last_weekly_generated = now
            db.commit()

        _invalidate_user_report_caches(user_id)
        logger.info("weekly_report_generated", user_id=user_id, report_id=str(report.id))
        payload = {
            "status": "success",
            "report_id": str(report.id),
            "report_type": "weekly",
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
        publish_task_event(task_id, {"task_id": task_id, "state": "SUCCESS", "ready": True, "successful": True, "result": payload})
        return payload
    except Exception as e:
        db.rollback()
        logger.error("weekly_report_failed", user_id=user_id, error=str(e))
        publish_task_event(task_id, {"task_id": task_id, "state": "FAILURE", "ready": True, "successful": False, "error": str(e)})
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, base=ReportTask)
def generate_monthly_report(
    self,
    user_id: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    project_id: Optional[str] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a monthly report."""
    task_id = self.request.id
    db = self._get_db()
    now = datetime.utcnow()
    try:
        publish_task_event(task_id, {"task_id": task_id, "state": "STARTED", "ready": False})
        user_uuid = UUID(user_id)
        project_uuid = UUID(project_id) if project_id else None

        if not year or not month:
            today = date.today()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        service = ReportService(db)
        report = service.generate_monthly_report(
            user_id=user_uuid,
            year=year,
            month=month,
            locale=locale,
            project_id=project_uuid,
        )

        schedule = db.query(ReportSchedule).filter(ReportSchedule.user_id == user_uuid).first()
        if schedule:
            schedule.last_monthly_generated = now
            db.commit()

        _invalidate_user_report_caches(user_id)
        logger.info("monthly_report_generated", user_id=user_id, report_id=str(report.id))
        payload = {
            "status": "success",
            "report_id": str(report.id),
            "report_type": "monthly",
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
        publish_task_event(task_id, {"task_id": task_id, "state": "SUCCESS", "ready": True, "successful": True, "result": payload})
        return payload
    except Exception as e:
        db.rollback()
        logger.error("monthly_report_failed", user_id=user_id, error=str(e))
        publish_task_event(task_id, {"task_id": task_id, "state": "FAILURE", "ready": True, "successful": False, "error": str(e)})
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


@celery_app.task(bind=True, base=ReportTask)
def generate_scheduled_reports(self) -> Dict[str, Any]:
    """Trigger due scheduled reports for all active schedules."""
    db = self._get_db()
    now = datetime.utcnow()
    try:
        schedules = db.query(ReportSchedule).filter(ReportSchedule.is_active == True).all()
        generated = {"daily": 0, "weekly": 0, "monthly": 0, "errors": []}

        for schedule in schedules:
            uid = str(schedule.user_id)
            service = ReportService(db)

            should, for_date = service.should_generate_report(UUID(uid), ReportType.DAILY)
            if should:
                try:
                    generate_daily_report.delay(
                        uid,
                        report_date=(for_date.isoformat() if for_date else None),
                        locale=schedule.language,
                    )
                    generated["daily"] += 1
                except Exception as e:
                    generated["errors"].append(f"daily:{uid}:{str(e)}")

            should, for_date = service.should_generate_report(UUID(uid), ReportType.WEEKLY)
            if should:
                try:
                    generate_weekly_report.delay(
                        uid,
                        week_start=(for_date.isoformat() if for_date else None),
                        locale=schedule.language,
                    )
                    generated["weekly"] += 1
                except Exception as e:
                    generated["errors"].append(f"weekly:{uid}:{str(e)}")

            should, _ = service.should_generate_report(UUID(uid), ReportType.MONTHLY)
            if should:
                try:
                    generate_monthly_report.delay(uid, locale=schedule.language)
                    generated["monthly"] += 1
                except Exception as e:
                    generated["errors"].append(f"monthly:{uid}:{str(e)}")

        logger.info("generate_scheduled_reports_done", totals=generated)
        return {"status": "success", "generated": generated, "timestamp": now.isoformat()}
    except Exception as e:
        db.rollback()
        logger.error("generate_scheduled_reports_failed", error=str(e))
        return {"status": "error", "error": str(e), "timestamp": now.isoformat()}
    finally:
        db.close()


@celery_app.task(bind=True, base=ReportTask)
def cleanup_old_reports(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """Delete reports older than `days_to_keep`."""
    db = self._get_db()
    cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
    try:
        old_reports = db.query(Report).filter(Report.created_at < cutoff).all()
        deleted = len(old_reports)
        for report in old_reports:
            db.delete(report)
        db.commit()
        logger.info("cleanup_old_reports_done", deleted=deleted)
        return {"status": "success", "deleted": deleted, "cutoff": cutoff.isoformat()}
    except Exception as e:
        db.rollback()
        logger.error("cleanup_old_reports_failed", error=str(e))
        return {"status": "error", "error": str(e)}
    finally:
        db.close()
