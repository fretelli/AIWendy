from __future__ import annotations

from datetime import datetime
import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from core.logging import get_logger
from domain.user.models import User
from services.agent_platform.allocation import AllocationService
from services.agent_platform.tushare import TushareReadService

router = APIRouter()
logger = get_logger(__name__)


class FutureCashNeed(BaseModel):
    date: str = Field(min_length=10, max_length=10)
    amount: float = Field(gt=0)
    note: str | None = Field(default=None, max_length=240)


class AllocationAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    base_currency: Literal["CNY"] = "CNY"
    capital: float = Field(gt=0)
    horizon_months: int = Field(ge=1, le=1200)
    liquidity_reserve: float = Field(default=0, ge=0)
    max_drawdown: float = Field(gt=0, le=1)
    max_leverage: float = Field(default=1, gt=0, le=5)
    future_cash_needs: list[FutureCashNeed] = Field(default_factory=list, max_length=100)
    allowed_markets: list[str] = Field(default_factory=lambda: ["CN"], max_length=20)
    allowed_instruments: list[str] = Field(default_factory=lambda: ["fund", "etf"], max_length=20)
    hard_restrictions: list[str] = Field(default_factory=list, max_length=30)


class AllocationAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    capital: float | None = Field(default=None, gt=0)
    horizon_months: int | None = Field(default=None, ge=1, le=1200)
    liquidity_reserve: float | None = Field(default=None, ge=0)
    max_drawdown: float | None = Field(default=None, gt=0, le=1)
    max_leverage: float | None = Field(default=None, gt=0, le=5)
    future_cash_needs: list[FutureCashNeed] | None = Field(default=None, max_length=100)
    allowed_markets: list[str] | None = Field(default=None, max_length=20)
    allowed_instruments: list[str] | None = Field(default=None, max_length=20)
    hard_restrictions: list[str] | None = Field(default=None, max_length=30)
    status: Literal["active", "archived"] | None = None


class TacticalTilt(BaseModel):
    sleeve_key: str = Field(min_length=1, max_length=40)
    weight_delta: float = Field(gt=-1, lt=1)
    thesis_id: UUID
    thesis_version_id: UUID
    review_at: datetime
    expires_at: datetime


class GeneratePolicyRequest(BaseModel):
    tactical_tilts: list[TacticalTilt] = Field(default_factory=list, max_length=20)


def service(session: AsyncSession, user: User) -> AllocationService:
    return AllocationService(session, TushareReadService(session), user.id)


@router.get("/allocation/data-status")
async def data_status(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).data_status()


@router.get("/allocation/universe")
async def universe(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).universe()


@router.get("/allocation/series/{series_id}")
async def series_history(series_id: str, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        return await service(session, user).series_history(series_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/allocation-accounts")
async def list_accounts(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).list_accounts()


@router.post("/allocation-accounts")
async def create_account(body: AllocationAccountCreate, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_account(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/allocation-accounts/{account_id}")
async def update_account(account_id: UUID, body: AllocationAccountUpdate,
                         session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).update_account(account_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(404 if "not found" in str(exc).lower() else 400, str(exc)) from exc


@router.delete("/allocation-accounts/{account_id}")
async def delete_account(account_id: UUID, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    try:
        await service(session, user).delete_account(account_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/allocation-accounts/{account_id}/policy-versions")
async def list_versions(account_id: UUID, session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)):
    try:
        return await service(session, user).list_versions(account_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/allocation-accounts/{account_id}/policy-versions")
async def generate_version(account_id: UUID, body: GeneratePolicyRequest,
                           session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    started = time.perf_counter()
    try:
        result = await service(session, user).generate_version(account_id, [item.model_dump() for item in body.tactical_tilts])
        logger.info("allocation_policy_generation", account_id=str(account_id), user_id=str(user.id),
                    status=result.get("feasibility_status"), quality_status=result.get("quality_status"),
                    duration_ms=round((time.perf_counter() - started) * 1000, 1))
        return result
    except ValueError as exc:
        logger.warning("allocation_policy_generation_failed", account_id=str(account_id), user_id=str(user.id),
                       error=str(exc), duration_ms=round((time.perf_counter() - started) * 1000, 1))
        raise HTTPException(400, str(exc)) from exc


@router.get("/allocation-policy-versions/{version_id}")
async def version_detail(version_id: UUID, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    item = await service(session, user).version_detail(version_id)
    if item is None:
        raise HTTPException(404, "Allocation policy version not found")
    return item


@router.post("/allocation-accounts/{account_id}/policy-versions/{version_id}/confirm")
async def confirm_version(account_id: UUID, version_id: UUID, session: AsyncSession = Depends(get_session),
                          user: User = Depends(get_current_user)):
    try:
        return await service(session, user).confirm_version(account_id, version_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
