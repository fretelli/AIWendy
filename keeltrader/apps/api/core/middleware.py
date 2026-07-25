"""Custom middleware for the application."""

import time
import uuid
from typing import Callable

import structlog
import jwt
from fastapi import Request, Response
from jwt import PyJWTError
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from core.database import async_session
from domain.user.models import User

settings = get_settings()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Clear and bind context variables
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Get logger
        logger = structlog.get_logger()

        # Log request
        logger.info("request_started")

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "request_failed",
                error=str(e),
                process_time_ms=round(process_time * 1000, 2),
                exc_info=True,
            )
            raise


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and setting user in request state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract user from JWT token and add to request state."""
        # Skip auth for health checks and docs
        if request.url.path in [
            "/",
            "/api/health",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
        ]:
            return await call_next(request)

        # Skip auth for auth endpoints
        if request.url.path.startswith("/api/auth/"):
            return await call_next(request)

        # Get token from authorization header
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]  # Remove "Bearer " prefix

            try:
                # Decode token
                payload = jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                )

                # Check token type
                if payload.get("type") == "access":
                    user_id = payload.get("sub")

                    if user_id:
                        # Get user from database
                        async with async_session() as session:
                            result = await session.execute(
                                select(User).where(
                                    User.id == user_id, User.is_active == True
                                )
                            )
                            user = result.scalar_one_or_none()

                            if user:
                                request.state.user = user
            except (PyJWTError, Exception) as e:
                # Token is invalid, but we don't fail here
                # Let the endpoint handle authentication if required
                logger = structlog.get_logger()
                logger.debug("Auth middleware token validation failed", error=str(e))

        return await call_next(request)
