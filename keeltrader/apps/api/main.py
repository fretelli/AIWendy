"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from config import get_settings
from core.database import init_database
from core.db_bootstrap import maybe_auto_init_db
from core.exceptions import AppException
from core.i18n import get_request_locale, t
from core.logging import setup_logging
from core.middleware import AuthMiddleware, LoggingMiddleware, RateLimitMiddleware
from routers import (
    analysis,
    auth,
    chat,
    coaches,
    exchanges,
    files,
    health,
    journals,
    knowledge,
    llm_config,
    market_data,
    ollama,
    projects,
    reports,
    roundtable,
    tasks,
    user_exchanges,
    users,
)

# Get settings
settings = get_settings()

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Security validation on startup
    _validate_security_config()

    # Startup
    logger.info("Starting KeelTrader API", version=settings.app_version)

    # Initialize database - Skip auto-creation due to model issues
    # await init_database()
    logger.info("Skipping automatic database initialization (Base.metadata.create_all)")
    await maybe_auto_init_db()

    # Initialize Sentry
    if settings.sentry_dsn and settings.environment != "development":
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("Sentry initialized")

    yield

    # Shutdown
    logger.info("Shutting down KeelTrader API")


def _validate_security_config():
    """Validate security configuration on startup."""
    errors = []

    # Skip validation in test environment
    if settings.environment in ["test", "testing"]:
        logger.info("Skipping security validation in test environment")
        return

    # Check JWT secret
    if settings.jwt_secret in [
        "INSECURE-DEFAULT-CHANGE-ME-32CHARS-MIN",
        "INSECURE-DEFAULT-CHANGE-ME",
        "your-secret-key-change-in-production",
    ]:
        errors.append(
            "CRITICAL: Using default JWT_SECRET! Set a secure random key in environment variables."
        )

    if len(settings.jwt_secret) < 32:
        errors.append(
            f"CRITICAL: JWT_SECRET too short ({len(settings.jwt_secret)} chars). Must be at least 32 characters."
        )

    # Check encryption key
    if settings.encryption_key is None:
        logger.warning(
            "ENCRYPTION_KEY not set. API key encryption will use derived key (less secure)."
        )
    elif len(settings.encryption_key) < 32:
        errors.append(
            f"CRITICAL: ENCRYPTION_KEY too short ({len(settings.encryption_key)} chars). Must be at least 32 characters."
        )

    # Check database password in production
    if settings.environment == "production":
        if "password" in settings.database_url.lower() or "123" in settings.database_url:
            logger.warning(
                "Database URL contains weak password patterns. Use strong passwords in production."
            )

    # Fail fast if critical errors
    if errors:
        for error in errors:
            logger.error(error)
        raise RuntimeError(
            f"Security validation failed with {len(errors)} error(s). Fix configuration and restart."
        )


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if settings.debug else None,
    redoc_url="/api/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)


# Exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions."""
    locale = get_request_locale(request)

    logger.warning(
        "business_error",
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )

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
        content={
            "error": {
                "code": exc.code,
                "message": message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    locale = get_request_locale(request)

    logger.error("unhandled_error", error=str(exc), exc_info=True)

    # Don't expose internal errors in production
    if settings.debug:
        error_message = str(exc)
    else:
        error_message = t("errors.internal", locale)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": error_message,
            }
        },
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(coaches.router, prefix="/api/v1/coaches", tags=["Coaches"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(journals.router, prefix="/api/v1/journals", tags=["Journals"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(ollama.router, prefix="/api/v1/ollama", tags=["Ollama"])
app.include_router(llm_config.router, tags=["LLM Configuration"])
app.include_router(market_data.router, tags=["Market Data"])
app.include_router(exchanges.router, tags=["Exchanges"])
app.include_router(user_exchanges.router, tags=["User Exchanges"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(
    knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"]
)
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(roundtable.router, prefix="/api/v1/roundtable", tags=["Roundtable"])
app.include_router(tasks.router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
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
