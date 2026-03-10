"""KeelTrader v2 — AI Native Trading Assistant.

Simplified FastAPI app with 5 route groups + MCP Server + asyncio scheduler.
"""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from core.db_bootstrap import maybe_auto_init_db
from core.exceptions import AppException
from core.i18n import get_request_locale, t
from core.logging import setup_logging
from core.middleware import AuthMiddleware, LoggingMiddleware

# Get settings
settings = get_settings()

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    _validate_security_config()

    logger.info("Starting KeelTrader v2 API", version=settings.app_version)

    # Import all domain models so SQLAlchemy can resolve string relationships
    import domain.analysis.models  # noqa
    import domain.coach.models  # noqa
    import domain.exchange.models  # noqa
    import domain.journal.models  # noqa
    import domain.knowledge.models  # noqa
    import domain.notification.models  # noqa
    import domain.project.models  # noqa
    import domain.report.models  # noqa
    import domain.user.models  # noqa

    # Initialize database
    logger.info("Skipping automatic database initialization (Base.metadata.create_all)")
    await maybe_auto_init_db()

    # Start asyncio scheduler (replaces Celery worker/beat)
    from scheduler import start_scheduler, stop_scheduler
    await start_scheduler()

    # Mount MCP Server (SSE transport)
    try:
        from mcp_server import mount_mcp_sse
        mount_mcp_sse(app)
    except Exception as e:
        logger.warning("MCP Server mount failed (optional)", error=str(e))

    yield

    # Shutdown
    await stop_scheduler()
    logger.info("Shutting down KeelTrader v2 API")


def _validate_security_config():
    """Validate security configuration on startup."""
    errors = []

    if settings.environment in ["test", "testing"]:
        logger.info("Skipping security validation in test environment")
        return

    if settings.jwt_secret in [
        "INSECURE-DEFAULT-CHANGE-ME-32CHARS-MIN",
        "INSECURE-DEFAULT-CHANGE-ME",
        "your-secret-key-change-in-production",
    ]:
        errors.append("CRITICAL: Using default JWT_SECRET!")

    if len(settings.jwt_secret) < 32:
        errors.append(f"CRITICAL: JWT_SECRET too short ({len(settings.jwt_secret)} chars)")

    if settings.encryption_key is None:
        logger.warning("ENCRYPTION_KEY not set. Using derived key (less secure).")
    elif len(settings.encryption_key) < 32:
        errors.append(f"CRITICAL: ENCRYPTION_KEY too short ({len(settings.encryption_key)} chars)")

    if errors:
        for error in errors:
            logger.error(error)
        raise RuntimeError(f"Security validation failed with {len(errors)} error(s)")


# Create FastAPI app
app = FastAPI(
    title="KeelTrader v2",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    locale = get_request_locale(request)
    logger.warning("business_error", code=exc.code, message=exc.message, details=exc.details)

    message = exc.message
    if exc.message_key:
        params: dict = {}
        if exc.details:
            params.update(exc.details)
        if exc.message_params:
            params.update(exc.message_params)
        message = t(exc.message_key, locale, **params)

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": message, "details": exc.details}},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    locale = get_request_locale(request)
    logger.error("unhandled_error", error=str(exc), exc_info=True)
    error_message = str(exc) if settings.debug else t("errors.internal", locale)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": error_message}},
    )


# === Route Groups ===
from routers import auth, health
from routers.users import router as users_router
from routers.chat_v2 import router as chat_v2_router
from routers.settings_v2 import router as settings_v2_router
from routers.webhook import router as webhook_router

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(chat_v2_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(settings_v2_router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(webhook_router, prefix="/api/v1/webhook", tags=["Webhook"])


@app.get("/")
async def root():
    return {
        "name": "KeelTrader v2",
        "version": settings.app_version,
        "status": "running",
        "mode": "ai-native",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
