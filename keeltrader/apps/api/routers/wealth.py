from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from domain.user.models import User
from services.agent_platform.wealth import WealthService

router = APIRouter()


def service(session: AsyncSession, user: User) -> WealthService:
    return WealthService(session, user.id)


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    annual_essential_spending: float | None = Field(default=None, ge=0)
    short_bucket_months: int | None = Field(default=None, ge=1, le=120)
    medium_bucket_months: int | None = Field(default=None, ge=2, le=240)
    aspirational_cap: float | None = Field(default=None, ge=0, le=0.20)
    satellite_cap: float | None = Field(default=None, ge=0, le=0.30)
    settings_json: dict[str, Any] | None = None


class MemberBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: Literal["self", "partner", "dependent", "parent", "other"] = "self"
    birth_date: date
    retirement_age: int | None = Field(default=None, ge=18, le=100)
    dependency_end_date: date | None = None
    annual_income: float = Field(default=0, ge=0)
    income_type: str | None = Field(default=None, max_length=40)
    income_stability: Literal["stable", "variable", "uncertain"] | None = None
    is_primary: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class AssetBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: Literal["cash", "financial", "real_estate", "business", "pension", "insurance", "other"]
    value_cny: float = Field(ge=0)
    original_currency: str | None = Field(default=None, max_length=12)
    original_value: float | None = Field(default=None, ge=0)
    liquidity: Literal["liquid", "limited", "illiquid"] = "liquid"
    allocatable: bool = True
    owner_member_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class LiabilityBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: Literal["mortgage", "consumer", "business", "other"]
    balance_cny: float = Field(ge=0)
    monthly_payment_cny: float = Field(default=0, ge=0)
    due_date: date | None = None
    owner_member_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class GoalBody(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    member_id: UUID | None = None
    target_amount_cny: float = Field(gt=0)
    target_date: date
    priority: Literal["essential", "important", "aspirational"] = "important"
    flexibility: Literal["fixed", "flexible"] = "flexible"
    notes: str | None = Field(default=None, max_length=2000)


class AssignmentBody(BaseModel):
    asset_id: UUID
    goal_id: UUID | None = None
    layer: Literal["safety", "market", "aspirational"] | None = None
    amount_cny: float = Field(gt=0)
    notes: str | None = Field(default=None, max_length=1000)


class SaaTarget(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    layer: Literal["safety", "market", "aspirational"]
    target_weight: float = Field(ge=0, le=1)
    min_weight: float = Field(ge=0, le=1)
    max_weight: float = Field(ge=0, le=1)


class SaaCreate(BaseModel):
    framework_version_id: UUID
    source_allocation_policy_version_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    effective_date: date
    review_date: date
    targets: list[SaaTarget] = Field(default_factory=list, max_length=50)


class TaaCreate(BaseModel):
    saa_version_id: UUID
    opportunity_snapshot_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    deltas: dict[str, float]
    rationale: str = Field(min_length=1, max_length=5000)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    falsifiers: list[str] = Field(default_factory=list, max_length=50)
    starts_at: date
    review_at: date
    expires_at: date


def _error(exc: ValueError) -> HTTPException:
    return HTTPException(404 if "不存在" in str(exc) else 400, str(exc))


@router.get("/wealth-profile")
async def get_profile(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).get_profile()


@router.put("/wealth-profile")
async def update_profile(body: ProfileUpdate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).update_profile(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise _error(exc) from exc


async def _create(kind: str, body: BaseModel, session: AsyncSession, user: User):
    try:
        return await service(session, user).create_item(kind, body.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


async def _update(kind: str, item_id: UUID, body: BaseModel, session: AsyncSession, user: User):
    try:
        return await service(session, user).update_item(kind, item_id, body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise _error(exc) from exc


async def _delete(kind: str, item_id: UUID, session: AsyncSession, user: User):
    try:
        await service(session, user).delete_item(kind, item_id)
        return {"ok": True}
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/wealth-profile/members")
async def create_member(body: MemberBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _create("members", body, session, user)


@router.put("/wealth-profile/members/{item_id}")
async def update_member(item_id: UUID, body: MemberBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _update("members", item_id, body, session, user)


@router.delete("/wealth-profile/members/{item_id}")
async def delete_member(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _delete("members", item_id, session, user)


@router.post("/wealth-profile/assets")
async def create_asset(body: AssetBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _create("assets", body, session, user)


@router.put("/wealth-profile/assets/{item_id}")
async def update_asset(item_id: UUID, body: AssetBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _update("assets", item_id, body, session, user)


@router.delete("/wealth-profile/assets/{item_id}")
async def delete_asset(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _delete("assets", item_id, session, user)


@router.post("/wealth-profile/liabilities")
async def create_liability(body: LiabilityBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _create("liabilities", body, session, user)


@router.put("/wealth-profile/liabilities/{item_id}")
async def update_liability(item_id: UUID, body: LiabilityBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _update("liabilities", item_id, body, session, user)


@router.delete("/wealth-profile/liabilities/{item_id}")
async def delete_liability(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _delete("liabilities", item_id, session, user)


@router.post("/wealth-profile/goals")
async def create_goal(body: GoalBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _create("goals", body, session, user)


@router.put("/wealth-profile/goals/{item_id}")
async def update_goal(item_id: UUID, body: GoalBody, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _update("goals", item_id, body, session, user)


@router.delete("/wealth-profile/goals/{item_id}")
async def delete_goal(item_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await _delete("goals", item_id, session, user)


@router.put("/wealth-profile/assignments")
async def replace_assignments(body: list[AssignmentBody], session: AsyncSession = Depends(get_session),
                              user: User = Depends(get_current_user)):
    try:
        return await service(session, user).replace_assignments([item.model_dump() for item in body])
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/wealth-profile/framework-preview")
async def framework_preview(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).framework_preview()


@router.get("/wealth-profile/framework-versions")
async def framework_versions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).framework_versions()


@router.post("/wealth-profile/framework-versions")
async def create_framework_version(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_framework_version()
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/saa-policy-versions")
async def saa_versions(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).saa_versions()


@router.post("/saa-policy-versions")
async def create_saa(body: SaaCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_saa(body.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/saa-policy-versions/{version_id}/confirm")
async def confirm_saa(version_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).confirm_saa(version_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("/taa-overlays")
async def taa_overlays(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await service(session, user).taa_overlays()


@router.post("/taa-overlays")
async def create_taa(body: TaaCreate, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).create_taa(body.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/taa-overlays/{overlay_id}/confirm")
async def confirm_taa(overlay_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).confirm_taa(overlay_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/taa-overlays/{overlay_id}/close")
async def close_taa(overlay_id: UUID, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await service(session, user).close_taa(overlay_id)
    except ValueError as exc:
        raise _error(exc) from exc
