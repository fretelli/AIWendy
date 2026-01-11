"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
import re

from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from core.i18n import get_request_locale, t
from core.logging import get_logger
from domain.user.models import User

router = APIRouter()
logger = get_logger(__name__)
encryption = get_encryption_service()


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


@router.put("/me")
async def update_current_user_profile(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile."""
    # TODO: Implement profile update
    return {"message": "Profile update endpoint - to be implemented"}


@router.get("/me/api-keys")
async def get_api_keys(
    current_user: User = Depends(get_current_user),
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
    return bool(re.match(r'^sk-[a-zA-Z0-9]{20,}', key))


def validate_anthropic_key(key: str) -> bool:
    """Validate Anthropic API key format."""
    return bool(re.match(r'^sk-ant-[a-zA-Z0-9]{20,}', key))


@router.put("/me/api-keys")
async def update_api_keys(
    keys: APIKeysUpdate,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
                current_user.anthropic_api_key = encryption.encrypt(keys.anthropic_api_key)
                logger.info(f"Updated Anthropic API key for user {current_user.email}")

        # Save to database
        session.add(current_user)
        await session.commit()

        return {"message": t("messages.api_keys_updated", locale)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API keys: {e}")
        raise HTTPException(status_code=500, detail=t("errors.failed_update_api_keys", locale))


@router.delete("/me/api-keys/{provider}")
async def delete_api_key(
    provider: str,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
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
