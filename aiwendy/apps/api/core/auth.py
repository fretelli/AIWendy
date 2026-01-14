"""Authentication utilities."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.database import get_session
from core.exceptions import InvalidTokenError, TokenExpiredError, UserNotFoundError
from domain.user.models import User

settings = get_settings()

# JWT Bearer
security = HTTPBearer(auto_error=False)

GUEST_EMAIL = "guest@local.keeltrader"


async def _ensure_guest_user(session: AsyncSession) -> User:
    """Ensure the single local guest user exists (self-host friendly)."""
    result = await session.execute(select(User).where(User.email == GUEST_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(
        email=GUEST_EMAIL,
        hashed_password=hash_password(uuid.uuid4().hex),
        is_email_verified=True,
        full_name="Guest",
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Best-effort: create a default project for the guest user.
    try:
        from domain.project.models import Project

        project = Project(
            user_id=user.id,
            name="Default Project",
            description="Auto-created for guest mode",
            is_default=True,
        )
        session.add(project)
        await session.commit()
    except Exception:
        await session.rollback()

    return user


def hash_password(password: str) -> str:
    """Hash a password."""
    password_bytes = password.encode("utf-8")
    # Truncate to 72 bytes if needed (bcrypt limitation)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    password_bytes = plain_password.encode("utf-8")
    # Truncate to 72 bytes if needed
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        raise InvalidTokenError()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Get the current authenticated user."""
    if credentials is None:
        if settings.auth_required:
            raise InvalidTokenError()
        return await _ensure_guest_user(session)

    token = credentials.credentials

    try:
        payload = decode_token(token)

        # Check token type
        if payload.get("type") != "access":
            raise InvalidTokenError()

        # Get user ID and session ID
        user_id = payload.get("sub")
        session_id = payload.get("session_id")

        if user_id is None:
            raise InvalidTokenError()

        # Validate session in Redis (if session_id exists in token)
        if session_id:
            from core.cache import get_redis_client

            redis_client = get_redis_client()
            session_key = f"session:{session_id}"
            stored_user_id = redis_client.get(session_key)

            # If session not found in Redis, it was revoked or expired
            if not stored_user_id:
                raise InvalidTokenError()

            # Verify user_id matches
            if str(stored_user_id) != str(user_id):
                raise InvalidTokenError()

    except (InvalidTokenError, TokenExpiredError, JWTError):
        if not settings.auth_required:
            return await _ensure_guest_user(session)
        raise

    # Get user from database
    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        if not settings.auth_required:
            return await _ensure_guest_user(session)
        raise UserNotFoundError(user_id)

    return user


async def get_authenticated_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get authenticated user (never returns guest).
    Use this for sensitive operations that should never allow guest access.
    """
    if credentials is None:
        raise InvalidTokenError()

    token = credentials.credentials

    try:
        payload = decode_token(token)

        # Check token type
        if payload.get("type") != "access":
            raise InvalidTokenError()

        # Get user ID and session ID
        user_id = payload.get("sub")
        session_id = payload.get("session_id")

        if user_id is None:
            raise InvalidTokenError()

        # Validate session in Redis (if session_id exists in token)
        if session_id:
            from core.cache import get_redis_client

            redis_client = get_redis_client()
            session_key = f"session:{session_id}"
            stored_user_id = redis_client.get(session_key)

            # If session not found in Redis, it was revoked or expired
            if not stored_user_id:
                raise InvalidTokenError()

            # Verify user_id matches
            if str(stored_user_id) != str(user_id):
                raise InvalidTokenError()

    except (InvalidTokenError, TokenExpiredError, JWTError):
        raise

    # Get user from database
    result = await session.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise UserNotFoundError(user_id)

    # Reject guest users
    if user.email == GUEST_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This operation requires authentication. Guest access not allowed.",
        )

    return user


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Get the current user if authenticated, otherwise None."""
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, session)
    except Exception:
        return None


class RequireAuth:
    """Dependency to require authentication."""

    def __init__(self, required_tier: Optional[str] = None):
        self.required_tier = required_tier

    async def __call__(
        self,
        user: User = Depends(get_current_user),
    ) -> User:
        """Check if user is authenticated and has required tier."""
        if self.required_tier:
            tiers = {
                "free": 0,
                "pro": 1,
                "elite": 2,
                "enterprise": 3,
            }

            user_tier_level = tiers.get(user.subscription_tier.value, 0)
            required_tier_level = tiers.get(self.required_tier, 0)

            if user_tier_level < required_tier_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {self.required_tier} subscription or higher",
                )

        return user
