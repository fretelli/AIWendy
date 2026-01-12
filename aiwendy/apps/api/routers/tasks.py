"""Task management and monitoring API endpoints."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from celery import states
from celery.result import AsyncResult
from core.auth import get_current_user
from core.cache_service import get_cache_service
from core.database import get_session
from core.i18n import get_request_locale, t
from core.logging import get_logger
from core.task_events import record_task_owner, task_event_channel
from domain.knowledge.models import KnowledgeDocument
from domain.user.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from workers.celery_app import celery_app
from workers.knowledge_tasks import ingest_knowledge_document, semantic_search
from workers.report_tasks import (generate_daily_report,
                                  generate_monthly_report,
                                  generate_weekly_report)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])
logger = get_logger(__name__)


class IngestKnowledgeRequest(BaseModel):
    project_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    source_type: str = Field("text", max_length=50)
    source_name: Optional[str] = Field(None, max_length=500)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the status of a background task.
    """
    locale = get_request_locale(http_request)
    try:
        cache = get_cache_service()
        redis_client = await cache.async_client
        owner = await redis_client.get(f"task:owner:{task_id}")
        if (
            owner
            and (str(owner) != str(current_user.id))
            and (not current_user.is_admin)
        ):
            raise HTTPException(
                status_code=403, detail=t("errors.access_denied", locale)
            )

        result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "state": result.state,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "failed": result.failed() if result.ready() else None,
        }

        # Add result or error information
        if result.ready():
            if result.successful():
                response["result"] = result.result
            elif result.failed():
                response["error"] = str(result.info)
                response["traceback"] = result.traceback

        # Add progress info for running tasks
        elif result.state == states.PENDING:
            response["info"] = t("messages.task_waiting", locale)
        elif result.state == states.STARTED:
            response["info"] = t("messages.task_started", locale)
        elif result.state != states.FAILURE:
            # Custom state with progress info
            response["info"] = result.info

        return response

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.get("/stream/{task_id}")
async def stream_task_status(
    task_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Stream task status updates as Server-Sent Events (SSE).

    This uses Redis pub/sub for push, with a best-effort AsyncResult state snapshot/heartbeat.
    """
    locale = get_request_locale(http_request)
    cache = get_cache_service()
    redis_client = await cache.async_client

    owner_key = f"task:owner:{task_id}"
    owner = await redis_client.get(owner_key)
    if owner and (str(owner) != str(current_user.id)) and (not current_user.is_admin):
        raise HTTPException(status_code=403, detail=t("errors.access_denied", locale))

    channel = task_event_channel(task_id)
    result = AsyncResult(task_id, app=celery_app)

    async def _iter():
        pubsub = redis_client.pubsub()
        last_state: Optional[str] = None
        last_sent_at = 0.0
        try:
            await pubsub.subscribe(channel)

            # Send an initial snapshot immediately.
            snapshot = {
                "task_id": task_id,
                "state": result.state,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "result": (
                    result.result if result.ready() and result.successful() else None
                ),
                "error": (
                    str(result.info) if result.ready() and result.failed() else None
                ),
            }
            yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
            if snapshot["ready"]:
                return

            while True:
                # Push events if workers publish.
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message.get("data"):
                    data = message["data"]
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode("utf-8", errors="ignore")
                    yield f"data: {data}\n\n"
                    try:
                        parsed = json.loads(data)
                        if parsed.get("ready") is True:
                            return
                    except Exception:
                        pass

                # Heartbeat / best-effort snapshot on state change.
                if result.state != last_state:
                    last_state = result.state
                    snapshot = {
                        "task_id": task_id,
                        "state": result.state,
                        "ready": result.ready(),
                        "successful": result.successful() if result.ready() else None,
                        "failed": result.failed() if result.ready() else None,
                        "result": (
                            result.result
                            if result.ready() and result.successful()
                            else None
                        ),
                        "error": (
                            str(result.info)
                            if result.ready() and result.failed()
                            else None
                        ),
                    }
                    yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                    if snapshot["ready"]:
                        return

                # Send a ping every ~15s to keep the connection alive.
                now = asyncio.get_running_loop().time()
                if now - last_sent_at > 15:
                    last_sent_at = now
                    yield "event: ping\ndata: {}\n\n"

                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            return
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass
            try:
                await pubsub.close()
            except Exception:
                pass

    return StreamingResponse(_iter(), media_type="text/event-stream")


@router.post("/reports/generate-daily")
async def trigger_daily_report(
    http_request: Request,
    report_date: Optional[str] = None,
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger daily report generation asynchronously.

    Args:
        report_date: Date in YYYY-MM-DD format (default: yesterday)
        project_id: Optional project ID to scope the report
    """
    try:
        locale = get_request_locale(http_request)
        task = generate_daily_report.delay(
            user_id=str(current_user.id),
            report_date=report_date,
            project_id=str(project_id) if project_id else None,
            locale=locale,
        )
        record_task_owner(task.id, str(current_user.id))

        logger.info(f"Daily report generation triggered: {task.id}")

        return {
            "task_id": task.id,
            "status": "queued",
            "message": t("messages.daily_report_queued", locale),
            "check_status_url": f"/api/v1/tasks/status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to trigger daily report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.internal", get_request_locale(http_request)),
        )


@router.post("/reports/generate-weekly")
async def trigger_weekly_report(
    http_request: Request,
    week_start: Optional[str] = None,
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger weekly report generation asynchronously.

    Args:
        week_start: Week start date in YYYY-MM-DD format (default: last week)
        project_id: Optional project ID to scope the report
    """
    try:
        locale = get_request_locale(http_request)
        task = generate_weekly_report.delay(
            user_id=str(current_user.id),
            week_start=week_start,
            project_id=str(project_id) if project_id else None,
            locale=locale,
        )
        record_task_owner(task.id, str(current_user.id))

        logger.info(f"Weekly report generation triggered: {task.id}")

        return {
            "task_id": task.id,
            "status": "queued",
            "message": t("messages.weekly_report_queued", locale),
            "check_status_url": f"/api/v1/tasks/status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to trigger weekly report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.internal", get_request_locale(http_request)),
        )


@router.post("/reports/generate-monthly")
async def trigger_monthly_report(
    http_request: Request,
    year: Optional[int] = None,
    month: Optional[int] = None,
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger monthly report generation asynchronously.

    Args:
        year: Year (default: last month's year)
        month: Month 1-12 (default: last month)
        project_id: Optional project ID to scope the report
    """
    try:
        locale = get_request_locale(http_request)
        task = generate_monthly_report.delay(
            user_id=str(current_user.id),
            year=year,
            month=month,
            project_id=str(project_id) if project_id else None,
            locale=locale,
        )
        record_task_owner(task.id, str(current_user.id))

        logger.info(f"Monthly report generation triggered: {task.id}")

        return {
            "task_id": task.id,
            "status": "queued",
            "message": t("messages.monthly_report_queued", locale),
            "check_status_url": f"/api/v1/tasks/status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to trigger monthly report: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.internal", get_request_locale(http_request)),
        )


@router.post("/knowledge/ingest")
async def trigger_knowledge_ingest(
    request: IngestKnowledgeRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a knowledge document and ingest it asynchronously."""
    locale = get_request_locale(http_request)
    try:
        title = request.title.strip()
        content = request.content.strip()
        if not title or not content:
            raise HTTPException(
                status_code=400, detail=t("errors.title_and_content_required", locale)
            )

        doc = KnowledgeDocument(
            user_id=current_user.id,
            project_id=request.project_id,
            title=title,
            source_type=request.source_type,
            source_name=request.source_name,
            content=content,
            metadata_=request.metadata or {},
            chunk_count=0,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        task = ingest_knowledge_document.delay(
            document_id=str(doc.id),
            user_id=str(current_user.id),
            embedding_provider=request.embedding_provider,
            embedding_model=request.embedding_model,
            overwrite=True,
        )
        record_task_owner(task.id, str(current_user.id))

        logger.info(f"Document processing triggered: {task.id}")

        return {
            "task_id": task.id,
            "document_id": str(doc.id),
            "status": "queued",
            "message": t("messages.knowledge_ingestion_queued", locale),
            "check_status_url": f"/api/v1/tasks/status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to trigger knowledge ingest: {str(e)}")
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.post("/knowledge/search")
async def trigger_semantic_search(
    query: str,
    http_request: Request,
    top_k: int = Query(5, ge=1, le=20),
    project_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Trigger semantic search in knowledge base.

    Args:
        query: Search query
        top_k: Number of results to return (1-20)
        project_id: Optional project ID to scope the search
    """
    locale = get_request_locale(http_request)
    try:
        task = semantic_search.delay(
            query=query,
            user_id=str(current_user.id),
            top_k=top_k,
            project_id=str(project_id) if project_id else None,
        )
        record_task_owner(task.id, str(current_user.id))

        logger.info(f"Semantic search triggered: {task.id}")

        return {
            "task_id": task.id,
            "status": "queued",
            "message": t("messages.semantic_search_queued", locale),
            "check_status_url": f"/api/v1/tasks/status/{task.id}",
        }

    except Exception as e:
        logger.error(f"Failed to trigger semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.get("/active")
async def get_active_tasks(
    http_request: Request,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get list of active tasks for the current user.
    Admin users can see all tasks.
    """
    locale = get_request_locale(http_request)
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()

        if not active_tasks:
            return {"tasks": [], "total": 0, "timestamp": datetime.utcnow().isoformat()}

        # Filter tasks for current user (unless admin)
        user_tasks = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                # Check if task belongs to current user
                task_args = task.get("args", [])
                task_kwargs = task.get("kwargs", {})

                # Check if user_id matches (in args or kwargs)
                user_id_match = (
                    str(current_user.id) in task_args
                    or task_kwargs.get("user_id") == str(current_user.id)
                    or current_user.is_admin
                )

                if user_id_match:
                    user_tasks.append(
                        {
                            "task_id": task.get("id"),
                            "name": task.get("name"),
                            "worker": worker,
                            "args": task.get("args"),
                            "kwargs": task.get("kwargs"),
                            "time_start": task.get("time_start"),
                        }
                    )

        # Limit results
        user_tasks = user_tasks[:limit]

        return {
            "tasks": user_tasks,
            "total": len(user_tasks),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get active tasks: {str(e)}")
        return {
            "tasks": [],
            "total": 0,
            "error": t("errors.internal", locale),
            "timestamp": datetime.utcnow().isoformat(),
        }


@router.get("/scheduled")
async def get_scheduled_tasks(
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get list of scheduled periodic tasks.
    Admin only endpoint.
    """
    locale = get_request_locale(http_request)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail=t("errors.admin_access_required", locale)
        )

    try:
        # Get scheduled tasks from Celery Beat
        scheduled_tasks = []

        for task_name, task_info in celery_app.conf.beat_schedule.items():
            scheduled_tasks.append(
                {
                    "name": task_name,
                    "task": task_info.get("task"),
                    "schedule": str(task_info.get("schedule")),
                    "args": task_info.get("args", []),
                    "kwargs": task_info.get("kwargs", {}),
                }
            )

        return {
            "scheduled_tasks": scheduled_tasks,
            "total": len(scheduled_tasks),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.post("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Cancel a running task.
    Users can only cancel their own tasks unless they are admin.
    """
    locale = get_request_locale(http_request)
    try:
        # Get task result
        result = AsyncResult(task_id, app=celery_app)

        # Check if task exists and is not finished
        if result.state in [states.SUCCESS, states.FAILURE]:
            raise HTTPException(
                status_code=400,
                detail=t("errors.task_already_completed", locale, task_id=task_id),
            )

        # TODO: Add user validation (check if task belongs to user)
        # This would require storing user_id with task metadata

        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)

        logger.info(f"Task {task_id} cancelled by user {current_user.id}")

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": t("messages.task_cancelled", locale),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {str(e)}")
        raise HTTPException(status_code=500, detail=t("errors.internal", locale))


@router.get("/stats")
async def get_task_stats(
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get task queue statistics.
    Admin only endpoint.
    """
    locale = get_request_locale(http_request)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail=t("errors.admin_access_required", locale)
        )

    try:
        inspect = celery_app.control.inspect()

        # Get various stats
        stats = inspect.stats()
        active = inspect.active()
        scheduled = inspect.scheduled()
        reserved = inspect.reserved()

        # Count tasks
        active_count = sum(len(tasks) for tasks in (active or {}).values())
        scheduled_count = sum(len(tasks) for tasks in (scheduled or {}).values())
        reserved_count = sum(len(tasks) for tasks in (reserved or {}).values())

        # Get worker stats
        worker_stats = []
        if stats:
            for worker, worker_info in stats.items():
                worker_stats.append(
                    {
                        "worker": worker,
                        "pool": worker_info.get("pool", {}).get("implementation"),
                        "max_concurrency": worker_info.get("pool", {}).get(
                            "max-concurrency"
                        ),
                        "processes": worker_info.get("pool", {}).get("processes"),
                        "total_tasks": worker_info.get("total", {}),
                    }
                )

        return {
            "queue_stats": {
                "active_tasks": active_count,
                "scheduled_tasks": scheduled_count,
                "reserved_tasks": reserved_count,
            },
            "workers": worker_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get task stats: {str(e)}")
        return {
            "queue_stats": {
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "reserved_tasks": 0,
            },
            "workers": [],
            "error": t("errors.internal", locale),
            "timestamp": datetime.utcnow().isoformat(),
        }
