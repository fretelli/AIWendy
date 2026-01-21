"""User management endpoints."""

import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_authenticated_user, get_current_user, hash_password
from core.database import get_session
from core.encryption import get_encryption_service
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User

router = APIRouter()
logger = get_logger(__name__)
encryption = get_encryption_service()


class UserUpdateRequest(BaseModel):
    """User profile update request."""

    full_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    trading_types: Optional[List[str]] = None
    main_concern: Optional[str] = None
    preferred_coach_id: Optional[str] = None
    preferred_coach_style: Optional[str] = None
    notification_preferences: Optional[Dict] = None
    privacy_settings: Optional[Dict] = None


class UserResponse(BaseModel):
    """User profile response."""

    id: str
    email: str
    full_name: Optional[str]
    display_name: Optional[str]
    timezone: str
    language: str
    bio: Optional[str]
    avatar_url: Optional[str]
    subscription_tier: str
    trading_types: List[str]
    main_concern: Optional[str]
    preferred_coach_id: Optional[str]
    preferred_coach_style: Optional[str]


class APIKeysUpdate(BaseModel):
    """API keys update request."""

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None


class APIKeysResponse(BaseModel):
    """API keys response (masked)."""

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    has_openai: bool = False
    has_anthropic: bool = False


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "subscription_tier": current_user.subscription_tier.value,
        "created_at": current_user.created_at,
    }


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdateRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
):
    """Update current user profile."""
    locale = get_request_locale(http_request)

    try:
        # Update email if provided and different
        if update_data.email and update_data.email != current_user.email:
            # Check email uniqueness
            stmt = select(User).where(User.email == update_data.email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail=t("errors.email_already_exists", locale),
                )
            current_user.email = update_data.email
            logger.info(f"User {current_user.id} changed email to {update_data.email}")

        # Update password if provided
        if update_data.password:
            if len(update_data.password) < 8:
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 8 characters",
                )
            current_user.hashed_password = hash_password(update_data.password)
            logger.info(f"User {current_user.id} changed password")

        # Update profile fields
        if update_data.full_name is not None:
            current_user.full_name = update_data.full_name
        if update_data.display_name is not None:
            current_user.display_name = update_data.display_name
        if update_data.timezone is not None:
            current_user.timezone = update_data.timezone
        if update_data.language is not None:
            current_user.language = update_data.language
        if update_data.bio is not None:
            current_user.bio = update_data.bio
        if update_data.avatar_url is not None:
            current_user.avatar_url = update_data.avatar_url
        if update_data.trading_types is not None:
            current_user.trading_types = update_data.trading_types
        if update_data.main_concern is not None:
            current_user.main_concern = update_data.main_concern
        if update_data.preferred_coach_id is not None:
            current_user.preferred_coach_id = update_data.preferred_coach_id
        if update_data.preferred_coach_style is not None:
            current_user.preferred_coach_style = update_data.preferred_coach_style
        if update_data.notification_preferences is not None:
            current_user.notification_preferences = update_data.notification_preferences
        if update_data.privacy_settings is not None:
            current_user.privacy_settings = update_data.privacy_settings

        # Save to database
        session.add(current_user)
        await session.commit()
        await session.refresh(current_user)

        logger.info(f"User {current_user.id} profile updated successfully")

        # Return updated profile
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            full_name=current_user.full_name,
            display_name=current_user.display_name,
            timezone=current_user.timezone,
            language=current_user.language,
            bio=current_user.bio,
            avatar_url=current_user.avatar_url,
            subscription_tier=current_user.subscription_tier.value,
            trading_types=current_user.trading_types or [],
            main_concern=current_user.main_concern,
            preferred_coach_id=current_user.preferred_coach_id,
            preferred_coach_style=current_user.preferred_coach_style,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=t("errors.failed_update_profile", locale),
        )


@router.get("/me/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_authenticated_user),
) -> APIKeysResponse:
    """Get current user's API keys (masked)."""
    response = APIKeysResponse()

    # Check and mask OpenAI key
    if current_user.openai_api_key:
        decrypted_key = encryption.decrypt(current_user.openai_api_key)
        if decrypted_key:
            response.openai_api_key = encryption.mask_api_key(decrypted_key)
            response.has_openai = True

    # Check and mask Anthropic key
    if current_user.anthropic_api_key:
        decrypted_key = encryption.decrypt(current_user.anthropic_api_key)
        if decrypted_key:
            response.anthropic_api_key = encryption.mask_api_key(decrypted_key)
            response.has_anthropic = True

    return response


def validate_openai_key(key: str) -> bool:
    """Validate OpenAI API key format."""
    return bool(re.match(r"^sk-[a-zA-Z0-9]{20,}", key))


def validate_anthropic_key(key: str) -> bool:
    """Validate Anthropic API key format."""
    return bool(re.match(r"^sk-ant-[a-zA-Z0-9]{20,}", key))


@router.put("/me/api-keys")
async def update_api_keys(
    keys: APIKeysUpdate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
) -> Dict[str, str]:
    """Update user's API keys."""
    locale = get_request_locale(http_request)
    try:
        # Validate and encrypt OpenAI key if provided
        if keys.openai_api_key is not None:
            if keys.openai_api_key == "":
                # Empty string means delete the key
                current_user.openai_api_key = None
                logger.info(f"Removed OpenAI API key for user {current_user.email}")
            else:
                # Validate format
                if not validate_openai_key(keys.openai_api_key):
                    raise HTTPException(
                        status_code=400,
                        detail=t("errors.invalid_openai_api_key_format", locale),
                    )
                # Encrypt and save
                current_user.openai_api_key = encryption.encrypt(keys.openai_api_key)
                logger.info(f"Updated OpenAI API key for user {current_user.email}")

        # Validate and encrypt Anthropic key if provided
        if keys.anthropic_api_key is not None:
            if keys.anthropic_api_key == "":
                # Empty string means delete the key
                current_user.anthropic_api_key = None
                logger.info(f"Removed Anthropic API key for user {current_user.email}")
            else:
                # Validate format
                if not validate_anthropic_key(keys.anthropic_api_key):
                    raise HTTPException(
                        status_code=400,
                        detail=t("errors.invalid_anthropic_api_key_format", locale),
                    )
                # Encrypt and save
                current_user.anthropic_api_key = encryption.encrypt(
                    keys.anthropic_api_key
                )
                logger.info(f"Updated Anthropic API key for user {current_user.email}")

        # Save to database
        session.add(current_user)
        await session.commit()

        return {"message": t("messages.api_keys_updated", locale)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        raise HTTPException(
            status_code=500, detail=t("errors.failed_update_api_keys", locale)
        )


@router.delete("/me/api-keys/{provider}")
async def delete_api_key(
    provider: str,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_authenticated_user),
) -> Dict[str, str]:
    """Delete a specific API key."""
    provider = provider.lower()
    locale = get_request_locale(http_request)

    if provider == "openai":
        current_user.openai_api_key = None
        logger.info(f"Deleted OpenAI API key for user {current_user.email}")
    elif provider == "anthropic":
        current_user.anthropic_api_key = None
        logger.info(f"Deleted Anthropic API key for user {current_user.email}")
    else:
        raise HTTPException(
            status_code=400,
            detail=t("errors.unknown_api_key_provider", locale, provider=provider),
        )

    session.add(current_user)
    await session.commit()

    return {"message": t("messages.api_key_deleted", locale, provider=provider)}
