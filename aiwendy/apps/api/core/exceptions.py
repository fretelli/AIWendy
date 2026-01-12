"""Custom exception classes."""

from typing import Any, Optional


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        message_key: Optional[str] = None,
        message_params: Optional[dict[str, Any]] = None,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.message_key = message_key
        self.message_params = message_params or {}
        self.status_code = status_code
        super().__init__(message)


# ========== Auth Exceptions ==========
class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            message_key="errors.authentication_failed",
            status_code=401,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""

    def __init__(self):
        super().__init__(message="Invalid email or password")
        self.message_key = "errors.invalid_credentials"


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self):
        super().__init__(message="Token has expired")
        self.message_key = "errors.token_expired"


class InvalidTokenError(AuthenticationError):
    """Invalid JWT token."""

    def __init__(self):
        super().__init__(message="Invalid token")
        self.message_key = "errors.invalid_token"


# ========== Authorization Exceptions ==========
class AuthorizationError(AppException):
    """Authorization failed."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message,
            message_key="errors.not_authorized",
            status_code=403,
        )


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str):
        super().__init__(
            message=f"Insufficient permissions. Required: {required_permission}"
        )


class InsufficientQuotaError(AuthorizationError):
    """User lacks required subscription tier."""

    def __init__(self, feature: str, required_tier: str):
        super().__init__(
            message=f"Feature '{feature}' requires {required_tier} subscription"
        )


# ========== Resource Exceptions ==========
class ResourceNotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} with id '{identifier}' not found",
            status_code=404,
        )


class UserNotFoundError(ResourceNotFoundError):
    """User not found."""

    def __init__(self, user_id: str):
        super().__init__(resource="User", identifier=user_id)


class CoachNotFoundError(ResourceNotFoundError):
    """Coach not found."""

    def __init__(self, coach_id: str):
        super().__init__(resource="Coach", identifier=coach_id)


class JournalNotFoundError(ResourceNotFoundError):
    """Journal entry not found."""

    def __init__(self, journal_id: str):
        super().__init__(resource="Journal entry", identifier=journal_id)


# ========== Validation Exceptions ==========
class ValidationError(AppException):
    """Validation failed."""

    def __init__(self, field: str, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=f"Validation failed for field '{field}': {message}",
            details={"field": field, "error": message},
            message_key="errors.validation_failed",
            message_params={"field": field, "error": message},
            status_code=422,
        )


class DuplicateResourceError(AppException):
    """Resource already exists."""

    def __init__(self, resource: str, field: str, value: Any):
        super().__init__(
            code="DUPLICATE_RESOURCE",
            message=f"{resource} with {field} '{value}' already exists",
            details={"resource": resource, "field": field, "value": value},
            message_key="errors.duplicate_resource",
            message_params={"resource": resource, "field": field, "value": value},
            status_code=409,
        )


# ========== Rate Limit Exceptions ==========
class RateLimitExceededError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self, limit: int, window_seconds: int, retry_after: Optional[int] = None
    ):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit of {limit} per {window_seconds}s exceeded",
            details={
                "limit": limit,
                "window": window_seconds,
                "retry_after": retry_after,
            },
            message_key="errors.rate_limit_exceeded",
            message_params={"limit": limit, "window": window_seconds},
            status_code=429,
        )


# ========== External Service Exceptions ==========
class ExternalServiceError(AppException):
    """External service error."""

    def __init__(self, service: str, message: str):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service} service error: {message}",
            details={"service": service},
            status_code=503,
        )


class LLMError(ExternalServiceError):
    """General LLM error."""

    def __init__(self, message: str):
        super().__init__(service="LLM", message=message)


class LLMProviderError(ExternalServiceError):
    """LLM provider error."""

    def __init__(self, provider: str, message: str):
        super().__init__(service=f"LLM ({provider})", message=message)


class PaymentProviderError(ExternalServiceError):
    """Payment provider error."""

    def __init__(self, message: str):
        super().__init__(service="Payment", message=message)


# ========== System Exceptions ==========
class SystemError(AppException):
    """System error."""

    def __init__(self, message: str):
        super().__init__(
            code="SYSTEM_ERROR",
            message=message,
            message_key="errors.internal",
            status_code=500,
        )


class DatabaseError(SystemError):
    """Database operation failed."""

    def __init__(self, operation: str, details: Optional[str] = None):
        message = f"Database {operation} failed"
        if details:
            message += f": {details}"
        super().__init__(message=message)
