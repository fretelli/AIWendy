"""
User exchange connection API endpoints
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.i18n import get_request_locale, t
from domain.exchange.models import ExchangeType
from domain.user.models import User
from services.user_exchange_service import UserExchangeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user/exchanges", tags=["user-exchanges"])


# Request/Response Models
class CreateExchangeConnectionRequest(BaseModel):
    """Request to create exchange connection"""

    exchange_type: ExchangeType = Field(..., description="Exchange type")
    name: Optional[str] = Field(None, description="Custom name for the connection")
    api_key: str = Field(..., min_length=10, description="Exchange API key")
    api_secret: str = Field(..., min_length=10, description="Exchange API secret")
    passphrase: Optional[str] = Field(None, description="Passphrase (for OKX, etc.)")
    is_testnet: bool = Field(False, description="Whether this is a testnet connection")


class UpdateExchangeConnectionRequest(BaseModel):
    """Request to update exchange connection"""

    name: Optional[str] = Field(None, description="Custom name")
    api_key: Optional[str] = Field(None, min_length=10, description="New API key")
    api_secret: Optional[str] = Field(None, min_length=10, description="New API secret")
    passphrase: Optional[str] = Field(None, description="New passphrase")
    is_active: Optional[bool] = Field(None, description="Active status")


class ExchangeConnectionResponse(BaseModel):
    """Exchange connection response (with masked keys)"""

    id: str
    exchange_type: str
    name: str
    api_key_masked: str
    is_active: bool
    is_testnet: bool
    last_sync_at: Optional[str]
    last_error: Optional[str]
    created_at: str
    updated_at: str


class TestConnectionResponse(BaseModel):
    """Test connection response"""

    success: bool
    message: str
    data: Optional[dict] = None


# Endpoints
@router.get("/", response_model=List[ExchangeConnectionResponse])
async def get_user_exchanges(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    active_only: bool = True,
):
    """
    Get all exchange connections for the current user

    Args:
        active_only: Only return active connections

    Returns:
        List of exchange connections with masked credentials
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)
        connections = await service.get_user_connections(current_user.id, active_only)

        # Mask sensitive data
        return [service.mask_connection(conn) for conn in connections]

    except Exception as e:
        logger.error(f"Error fetching user exchanges: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_fetch_failed", locale),
        )


@router.post("/", response_model=ExchangeConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_connection(
    http_request: Request,
    request: CreateExchangeConnectionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new exchange connection

    Creates and securely stores encrypted API credentials for an exchange.
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)

        # Create connection
        connection = await service.create_connection(
            user_id=current_user.id,
            exchange_type=request.exchange_type,
            api_key=request.api_key,
            api_secret=request.api_secret,
            passphrase=request.passphrase,
            name=request.name,
            is_testnet=request.is_testnet,
        )

        return service.mask_connection(connection)

    except Exception as e:
        logger.error(f"Error creating exchange connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_create_failed", locale),
        )


@router.get("/{connection_id}", response_model=ExchangeConnectionResponse)
async def get_exchange_connection(
    http_request: Request,
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific exchange connection

    Returns:
        Exchange connection with masked credentials
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)
        connection = await service.get_connection(connection_id, current_user.id)

        if not connection:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_connection_not_found", locale),
            )

        return service.mask_connection(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching exchange connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_fetch_failed", locale),
        )


@router.put("/{connection_id}", response_model=ExchangeConnectionResponse)
async def update_exchange_connection(
    http_request: Request,
    connection_id: UUID,
    request: UpdateExchangeConnectionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update an exchange connection

    Can update name, credentials, or active status.
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)

        connection = await service.update_connection(
            connection_id=connection_id,
            user_id=current_user.id,
            name=request.name,
            api_key=request.api_key,
            api_secret=request.api_secret,
            passphrase=request.passphrase,
            is_active=request.is_active,
        )

        if not connection:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_connection_not_found", locale),
            )

        return service.mask_connection(connection)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating exchange connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_update_failed", locale),
        )


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_connection(
    http_request: Request,
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete an exchange connection

    Permanently removes the connection and its credentials.
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)
        success = await service.delete_connection(connection_id, current_user.id)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_connection_not_found", locale),
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exchange connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_delete_failed", locale),
        )


@router.post("/{connection_id}/test", response_model=TestConnectionResponse)
async def test_exchange_connection(
    http_request: Request,
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Test an exchange connection

    Attempts to connect to the exchange and fetch account data to verify credentials.
    """
    locale = get_request_locale(http_request)

    try:
        service = UserExchangeService(session)
        result = await service.test_connection(connection_id, current_user.id)

        return result

    except Exception as e:
        logger.error(f"Error testing exchange connection: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_test_failed", locale),
        )
