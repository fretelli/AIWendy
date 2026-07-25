"""User identity and basic profile endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_authenticated_user, get_current_user, hash_password
from core.database import get_session
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.auth_schemas import UserResponse, validate_password_strength
from domain.user.models import User

router = APIRouter()
logger = get_logger(__name__)


class UserUpdateRequest(BaseModel):
    """Editable identity and profile fields."""

    full_name: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=50)
    language: Optional[str] = Field(default=None, max_length=10)
    bio: Optional[str] = Field(default=None, max_length=5000)
    avatar_url: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        return validate_password_strength(value) if value else value


def _profile(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        display_name=user.display_name,
        timezone=user.timezone or "UTC",
        language=user.language or "en",
        bio=user.bio,
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the current user's identity and basic profile."""
    return _profile(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
) -> UserResponse:
    """Update the current user's identity and basic profile."""
    locale = get_request_locale(http_request)

    if update_data.email and update_data.email != current_user.email:
        existing = await session.scalar(select(User).where(User.email == update_data.email))
        if existing:
            raise HTTPException(
                status_code=400,
                detail=t("errors.email_already_exists", locale),
            )
        current_user.email = update_data.email

    if update_data.password:
        current_user.hashed_password = hash_password(update_data.password)

    for field in (
        "full_name",
        "display_name",
        "timezone",
        "language",
        "bio",
        "avatar_url",
    ):
        value = getattr(update_data, field)
        if value is not None:
            setattr(current_user, field, value)

    try:
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)
    except Exception as exc:
        await session.rollback()
        logger.exception("user_profile_update_failed", user_id=str(current_user.id), error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=t("errors.failed_update_profile", locale),
        ) from exc

    logger.info("user_profile_updated", user_id=str(current_user.id))
    return _profile(current_user)
