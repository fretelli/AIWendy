"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "aiwendy",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.tasks",
        "workers.report_tasks",
        "workers.knowledge_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    task_soft_time_limit=1500,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-expired-user-sessions": {
        "task": "workers.tasks.cleanup_expired_user_sessions",
        "schedule": crontab(minute="0", hour="*/6"),  # Every 6 hours
    },
    "update-subscription-status": {
        "task": "workers.tasks.update_subscription_status",
        "schedule": crontab(minute="0", hour="*/12"),  # Every 12 hours
    },
    "generate-scheduled-reports": {
        "task": "workers.report_tasks.generate_scheduled_reports",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    "cleanup-old-reports": {
        "task": "workers.report_tasks.cleanup_old_reports",
        "schedule": crontab(
            minute="0", hour="4", day_of_week="0"
        ),  # Weekly on Sunday at 4 AM
    },
}
