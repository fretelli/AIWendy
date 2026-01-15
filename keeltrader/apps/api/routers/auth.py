"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)
from core.database import get_session
from core.exceptions import DuplicateResourceError, InvalidCredentialsError
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User, UserSession
from domain.user.schemas import SessionInfo, SessionListResponse

settings = get_settings()
logger = get_logger()
router = APIRouter()


# ========== Request/Response Models ==========
class RegisterRequest(BaseModel):
    """Registration request."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = None

    @field_validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    full_name: Optional[str]
    subscription_tier: str
    created_at: datetime


# ========== Endpoints ==========
@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    locale = get_request_locale(http_request)
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise DuplicateResourceError("User", "email", request.email)

    # Create user
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Ensure every user has at least one default project
    try:
        from domain.project.models import Project

        default_project = Project(
            user_id=user.id,
            name=t("projects.default.name", locale),
            description=t("projects.default.description", locale),
            is_default=True,
        )
        session.add(default_project)
        await session.commit()
    except Exception:
        # Non-fatal: project feature may be disabled/misconfigured
        await session.rollback()

    logger.info("User registered", user_id=str(user.id), email=user.email)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        subscription_tier=user.subscription_tier.value,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Login user and return tokens."""
    # Get user
    result = await session.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    # Verify credentials
    if not user or not verify_password(request.password, user.hashed_password):
        raise InvalidCredentialsError()

    # Update last login
    user.last_login_at = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    await session.commit()

    # Create session record first to get session_id
    user_session = UserSession(
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    )
    session.add(user_session)
    await session.flush()  # Get the session ID without committing

    # Create tokens with session_id in payload
    token_data = {"sub": str(user.id), "session_id": str(user_session.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Update session with tokens
    user_session.access_token = access_token
    user_session.refresh_token = refresh_token
    await session.commit()

    # Store session in Redis for fast validation
    from core.cache import get_redis_client

    redis_client = get_redis_client()
    session_key = f"session:{user_session.id}"
    redis_client.setex(
        session_key,
        settings.jwt_expire_minutes * 60,  # TTL in seconds
        str(user.id),  # Store user_id for validation
    )

    logger.info("User logged in", user_id=str(user.id), email=user.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session),
):
    """Refresh access token."""
    try:
        # Decode refresh token
        payload = decode_token(request.refresh_token)

        # Check token type
        if payload.get("type") != "refresh":
            raise InvalidCredentialsError()

        # Get user
        user_id = payload.get("sub")
        old_session_id = payload.get("session_id")

        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidCredentialsError()

        # Verify old session is still valid (if session_id exists)
        if old_session_id:
            from core.cache import get_redis_client

            redis_client = get_redis_client()
            session_key = f"session:{old_session_id}"
            stored_user_id = redis_client.get(session_key)

            if not stored_user_id or str(stored_user_id) != str(user_id):
                raise InvalidCredentialsError()

            # Revoke old session
            redis_client.delete(session_key)

        # Create new session
        user_session = UserSession(
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
        )
        session.add(user_session)
        await session.flush()

        # Create new tokens with new session_id
        token_data = {"sub": str(user.id), "session_id": str(user_session.id)}
        access_token = create_access_token(token_data)
        refresh_token_new = create_refresh_token(token_data)

        # Update session with tokens
        user_session.access_token = access_token
        user_session.refresh_token = refresh_token_new
        await session.commit()

        # Store new session in Redis
        from core.cache import get_redis_client

        redis_client = get_redis_client()
        new_session_key = f"session:{user_session.id}"
        redis_client.setex(
            new_session_key,
            settings.jwt_expire_minutes * 60,
            str(user.id),
        )

        logger.info("Token refreshed with new session", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_new,
            expires_in=settings.jwt_expire_minutes * 60,
        )

    except Exception as e:
        logger.warning("Token refresh failed", error=str(e))
        raise InvalidCredentialsError()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Logout user (revoke session)."""
    # Extract session_id from JWT token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.info("User logged out (no token)", user_id=str(current_user.id))
        return None

    token = auth_header.split(" ")[1]

    try:
        payload = decode_token(token)
        session_id = payload.get("session_id")

        if session_id:
            # Remove session from Redis
            from core.cache import get_redis_client

            redis_client = get_redis_client()
            session_key = f"session:{session_id}"
            redis_client.delete(session_key)

            # Mark session as revoked in database
            result = await session.execute(
                select(UserSession).where(UserSession.id == session_id)
            )
            user_session = result.scalar_one_or_none()
            if user_session:
                user_session.revoked_at = datetime.utcnow()
                await session.commit()

            logger.info(
                "User logged out (session revoked)",
                user_id=str(current_user.id),
                session_id=session_id,
            )
        else:
            logger.info(
                "User logged out (legacy token without session_id)",
                user_id=str(current_user.id),
            )

    except Exception as e:
        logger.warning(f"Logout error: {str(e)}", user_id=str(current_user.id))

    return None


# ========== Session Management ==========


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all active sessions for the current user."""
    # Get current session_id from token
    current_session_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_token(token)
            current_session_id = payload.get("session_id")
        except Exception:
            pass

    # Query all active sessions for the user
    result = await session.execute(
        select(UserSession)
        .where(
            UserSession.user_id == current_user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.utcnow(),
        )
        .order_by(UserSession.created_at.desc())
    )
    sessions = result.scalars().all()

    # Convert to response format
    session_infos = [
        SessionInfo(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            last_activity_at=s.last_activity_at,
            expires_at=s.expires_at,
            is_current=(str(s.id) == current_session_id),
        )
        for s in sessions
    ]

    return SessionListResponse(sessions=session_infos, total=len(session_infos))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Revoke a specific session."""
    # Get the session
    result = await session.execute(
        select(UserSession).where(
            UserSession.id == session_id, UserSession.user_id == current_user.id
        )
    )
    user_session = result.scalar_one_or_none()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Remove from Redis
    from core.cache import get_redis_client

    redis_client = get_redis_client()
    session_key = f"session:{session_id}"
    redis_client.delete(session_key)

    # Mark as revoked in database
    user_session.revoked_at = datetime.utcnow()
    await session.commit()

    logger.info(
        "Session revoked",
        user_id=str(current_user.id),
        session_id=session_id,
    )

    return None
