"""KeelTrader v2 API."""

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
from core.model_registry import register_domain_models

# Get settings
settings = get_settings()

# Setup structured logging
setup_logging()
logger = structlog.get_logger()


def _import_domain_models():
    """Register SQLAlchemy models before routes can trigger mapper configuration."""
    register_domain_models()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    _validate_security_config()

    logger.info("Starting KeelTrader v2 API", version=settings.app_version)

    # Import all domain models so SQLAlchemy can resolve string relationships
    _import_domain_models()

    # Initialize database
    logger.info("Skipping automatic database initialization (Base.metadata.create_all)")
    await maybe_auto_init_db()

    yield

    # Shutdown
    await market_data_service.close()
    await market_data_ws_service.close()
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
        if settings.environment.lower() in {"production", "prod"}:
            errors.append("CRITICAL: ENCRYPTION_KEY is required in production")
        else:
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
_import_domain_models()

from routers import auth, health
from routers.agent_platform import router as agent_platform_router
from routers.allocation import router as allocation_router
from routers.markets import router as markets_router
from routers.wealth import router as wealth_router
from routers.research_cloud import router as research_cloud_router
from routers.users import router as users_router
from routers.files import router as files_router
from routers.market_data import (
    market_data_service,
    market_data_ws_service,
    router as market_data_router,
)

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(files_router, prefix="/api/v1/files", tags=["Files"])
app.include_router(agent_platform_router, prefix="/api/v1/agent", tags=["Agent Platform"])
app.include_router(allocation_router, prefix="/api/v1/agent", tags=["Asset Allocation"])
app.include_router(wealth_router, prefix="/api/v1/agent", tags=["Household Wealth"])
app.include_router(markets_router, prefix="/api/v1/markets", tags=["Markets"])
app.include_router(
    research_cloud_router,
    prefix="/api/v1/research-cloud",
    tags=["Research Cloud"],
)
app.include_router(market_data_router, prefix="/api/v1/market-data", tags=["Market Data"])


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
