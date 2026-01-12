"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from config import get_settings
from core.auth import (create_access_token, create_refresh_token, decode_token,
                       get_current_user, hash_password, verify_password)
from core.database import get_session
from core.exceptions import DuplicateResourceError, InvalidCredentialsError
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User, UserSession
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

settings = get_settings()
logger = get_logger(__name__)
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

    # Create tokens
    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store session
    user_session = UserSession(
        user_id=user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    )
    session.add(user_session)
    await session.commit()

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
        result = await session.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidCredentialsError()

        # Create new tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        logger.info("Token refreshed", user_id=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,
            expires_in=settings.jwt_expire_minutes * 60,
        )

    except Exception as e:
        logger.warning("Token refresh failed", error=str(e))
        raise InvalidCredentialsError()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Logout user (revoke session)."""
    # TODO: Implement session revocation
    logger.info("User logged out", user_id=str(current_user.id))
    return None
