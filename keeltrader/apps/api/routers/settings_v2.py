"""Settings v2 — merged settings page API."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.encryption import get_encryption_service
from core.logging import get_logger
from domain.exchange.models import ExchangeConnection
from domain.user.models import User

router = APIRouter()
logger = get_logger(__name__)
encryption = get_encryption_service()


class ExchangeConnectionRequest(BaseModel):
    exchange: str  # okx, bybit, coinbase, kraken, ibkr
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None
    trading_mode: str = "swap"
    is_testnet: bool = False
    sync_symbols: Optional[list[str]] = None


class RiskSettingsRequest(BaseModel):
    max_order_value_usd: Optional[float] = None
    max_daily_loss_usd: Optional[float] = None
    max_positions: Optional[int] = None
    require_confirmation: Optional[bool] = None


class PushSettingsRequest(BaseModel):
    push_morning_report: Optional[bool] = None
    push_evening_report: Optional[bool] = None
    push_trade_alerts: Optional[bool] = None
    push_risk_alerts: Optional[bool] = None


@router.get("/exchanges")
async def list_exchanges(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List connected exchanges."""
    stmt = select(ExchangeConnection).where(
        ExchangeConnection.user_id == current_user.id,
        ExchangeConnection.is_active == True,
    )
    result = await session.execute(stmt)
    connections = result.scalars().all()

    return {
        "exchanges": [
            {
                "id": str(c.id),
                "exchange": c.exchange_type.value,
                "trading_mode": c.trading_mode.value if c.trading_mode else "swap",
                "is_testnet": c.is_testnet,
                "sync_symbols": c.sync_symbols,
                "last_sync": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in connections
        ],
    }


@router.post("/exchanges")
async def add_exchange(
    request: ExchangeConnectionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Add an exchange connection."""
    # Test connection first
    from apps.exchange.factory import create_adapter

    try:
        adapter = create_adapter(
            exchange_name=request.exchange,
            api_key=request.api_key,
            api_secret=request.api_secret,
            passphrase=request.passphrase,
            trading_mode=request.trading_mode,
            is_testnet=request.is_testnet,
            use_cache=False,
        )
        test_result = await adapter.test_connection()
        await adapter.close()
        if not test_result.get("success"):
            raise HTTPException(status_code=400, detail=f"连接测试失败: {test_result.get('message')}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(e)}")

    conn = ExchangeConnection(
        user_id=current_user.id,
        exchange_type=request.exchange,
        api_key_encrypted=encryption.encrypt(request.api_key),
        api_secret_encrypted=encryption.encrypt(request.api_secret),
        passphrase_encrypted=encryption.encrypt(request.passphrase) if request.passphrase else None,
        trading_mode=request.trading_mode,
        is_testnet=request.is_testnet,
        sync_symbols=request.sync_symbols,
        is_active=True,
    )
    session.add(conn)
    await session.commit()

    return {"message": f"{request.exchange} 连接成功", "id": str(conn.id)}


@router.delete("/exchanges/{exchange_id}")
async def remove_exchange(
    exchange_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Remove an exchange connection."""
    stmt = select(ExchangeConnection).where(
        ExchangeConnection.id == exchange_id,
        ExchangeConnection.user_id == current_user.id,
    )
    result = await session.execute(stmt)
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="连接不存在")

    conn.is_active = False
    await session.commit()
    return {"message": "已断开连接"}


@router.get("/risk")
async def get_risk_settings(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get risk settings."""
    settings = (current_user.api_keys_encrypted or {}).get("risk_settings", {})
    defaults = {
        "max_order_value_usd": 5000.0,
        "max_daily_loss_usd": 500.0,
        "max_positions": 5,
        "require_confirmation": True,
    }
    return {**defaults, **settings}


@router.put("/risk")
async def update_risk_settings(
    request: RiskSettingsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update risk settings."""
    from tools.settings_tools import update_settings
    settings_dict = {k: v for k, v in request.model_dump().items() if v is not None}
    return await update_settings(session, current_user.id, settings_dict)


@router.get("/push")
async def get_push_settings(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get push notification settings."""
    settings = (current_user.api_keys_encrypted or {}).get("risk_settings", {})
    defaults = {
        "push_morning_report": True,
        "push_evening_report": True,
        "push_trade_alerts": True,
        "push_risk_alerts": True,
    }
    return {k: settings.get(k, v) for k, v in defaults.items()}


@router.put("/push")
async def update_push_settings(
    request: PushSettingsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update push notification settings."""
    from tools.settings_tools import update_settings
    settings_dict = {k: v for k, v in request.model_dump().items() if v is not None}
    return await update_settings(session, current_user.id, settings_dict)
