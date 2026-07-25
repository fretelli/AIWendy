"""Health check endpoints."""

from datetime import datetime
import redis.asyncio as redis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.build_info import get_build_info
from core.database import get_session
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        **get_build_info(),
    }


@router.get("/health/ready")
async def readiness_check(
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Return readiness without exposing infrastructure exception details."""
    checks = {}
    ready = True

    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as exc:
        logger.exception("database_readiness_failed", error=str(exc))
        checks["database"] = {"status": "error", "code": "database_unavailable"}
        ready = False

    # Check Redis
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = {"status": "ok"}
    except Exception as exc:
        logger.exception("redis_readiness_failed", error=str(exc))
        checks["redis"] = {"status": "error", "code": "redis_unavailable"}
        ready = False

    response.status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        **get_build_info(),
    }


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", **get_build_info()}
