"""Custom middleware for the application."""

import time
import uuid
from typing import Callable, Optional

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from sqlalchemy import select

from config import get_settings
from core.i18n import get_request_locale, t
from core.ratelimit import RateLimiter, get_rate_limiter
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
        if request.url.path in ["/", "/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"]:
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
                                select(User).where(User.id == user_id, User.is_active == True)
                            )
                            user = result.scalar_one_or_none()

                            if user:
                                request.state.user = user
            except (JWTError, Exception) as e:
                # Token is invalid, but we don't fail here
                # Let the endpoint handle authentication if required
                logger = structlog.get_logger()
                logger.debug("Auth middleware token validation failed", error=str(e))

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/", "/api/health", "/api/docs", "/api/redoc"]:
            return await call_next(request)

        # Skip if no user in request (auth middleware will handle)
        if not hasattr(request.state, "user"):
            return await call_next(request)

        user = request.state.user
        endpoint = self._get_endpoint_key(request.url.path)

        # Skip if endpoint is not rate limited
        if not endpoint:
            return await call_next(request)

        logger = structlog.get_logger()

        # Get rate limiter (fail open if Redis is unavailable in development)
        try:
            rate_limiter = await get_rate_limiter()
        except Exception as e:
            logger.warning("rate_limit_unavailable", error=str(e))
            return await call_next(request)

        # Get limits based on user tier
        # Handle both string and enum values
        tier = user.subscription_tier.value if hasattr(user.subscription_tier, 'value') else user.subscription_tier
        limits = self._get_limits(tier)
        limit, window = limits.get(endpoint, (None, None))

        if limit is None:
            return await call_next(request)

        # Check rate limit
        key = f"ratelimit:{user.id}:{endpoint}"
        try:
            allowed, remaining = await rate_limiter.is_allowed(key, limit, window)
        except Exception as e:
            logger.warning("rate_limit_check_failed", error=str(e))
            return await call_next(request)

        if not allowed:
            locale = get_request_locale(request)
            # Calculate retry after
            try:
                retry_after = await rate_limiter.get_retry_after(key, window)
            except Exception as e:
                logger.warning("rate_limit_retry_after_failed", error=str(e))
                retry_after = window

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": t("errors.rate_limit_exceeded", locale, limit=limit, window=window),
                        "details": {
                            "limit": limit,
                            "window": window,
                            "retry_after": retry_after,
                        },
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _get_endpoint_key(self, path: str) -> Optional[str]:
        """Extract endpoint key from path."""
        if "/chat" in path:
            return "chat"
        elif "/journals" in path:
            return "journal"
        elif "/analysis" in path:
            return "analysis"
        return None

    def _get_limits(self, tier: str) -> dict[str, tuple[int, int]]:
        """Get rate limits for user tier."""
        if tier == "free":
            return {
                "chat": (settings.rate_limit_free_chat_hourly, 3600),
                "journal": (settings.rate_limit_free_journal_daily, 86400),
                "analysis": (1, 86400),  # 1 per day
            }
        elif tier == "pro":
            return {
                "chat": (settings.rate_limit_pro_chat_hourly, 3600),
                "journal": (settings.rate_limit_pro_journal_daily, 86400),
                "analysis": (10, 86400),  # 10 per day
            }
        elif tier in ["elite", "enterprise"]:
            return {
                "chat": (1000, 3600),  # Very high limits
                "journal": (9999, 86400),
                "analysis": (100, 86400),
            }
        else:
            # Default to free tier limits
            return self._get_limits("free")
