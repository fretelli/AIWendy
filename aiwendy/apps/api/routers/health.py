"""Health check endpoints."""

from datetime import datetime
from enum import Enum

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.database import get_session
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)
router = APIRouter()


class HealthStatus(str, Enum):
    """Health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@router.get("/health")
async def health():
    """Basic health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """Detailed readiness check."""
    checks = {}
    overall_status = HealthStatus.HEALTHY

    # Check database
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = {"status": "ok"}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        checks["database"] = {"status": "error", "error": str(e)}
        overall_status = HealthStatus.UNHEALTHY

    # Check Redis
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        checks["redis"] = {"status": "error", "error": str(e)}
        overall_status = HealthStatus.DEGRADED

    # Check LLM providers (basic connectivity)
    checks["llm"] = {
        "openai": "configured" if settings.openai_api_key else "not_configured",
        "anthropic": "configured" if settings.anthropic_api_key else "not_configured",
    }

    if not settings.openai_api_key and not settings.anthropic_api_key:
        overall_status = HealthStatus.DEGRADED

    return {
        "status": overall_status.value,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
    }


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}
