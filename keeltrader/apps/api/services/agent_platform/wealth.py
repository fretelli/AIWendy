"""Household wealth, strategic allocation and tactical overlay planning."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import (
    AllocationAccount,
    AllocationPolicySleeve,
    AllocationPolicyVersion,
    HouseholdMember,
    MarketOpportunity,
    MarketOpportunitySnapshot,
    SaaPolicyVersion,
    TaaOverlay,
    WealthAsset,
    WealthAssignment,
    WealthFrameworkVersion,
    WealthGoal,
    WealthLiability,
    WealthProfile,
)


def _json(value: Any) -> Any:
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value


def _response_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {key: _response_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_response_json(item) for item in value]
    return value


def stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(_json(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def age_on(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def months_until(target: date, today: date | None = None) -> int:
    today = today or date.today()
    months = (target.year - today.year) * 12 + target.month - today.month
    if target.day < today.day:
        months -= 1
    return max(0, months)


def horizon_bucket(target: date, short_months: int = 24, medium_months: int = 60,
                   today: date | None = None) -> str:
    months = months_until(target, today)
    if months <= short_months:
        return "short"
    if months <= medium_months:
        return "medium"
    return "long"


class WealthService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def _profile(self, *, create: bool = False, lock: bool = False) -> WealthProfile | None:
        query = select(WealthProfile).where(WealthProfile.user_id == self.user_id)
        if lock:
            query = query.with_for_update()
        row = (await self.session.execute(query)).scalar_one_or_none()
        if row is None and create:
            await self.session.execute(
                pg_insert(WealthProfile)
                .values(user_id=self.user_id)
                .on_conflict_do_nothing(index_elements=[WealthProfile.user_id])
            )
            await self.session.commit()
            row = (await self.session.execute(query)).scalar_one()
        return row

    async def get_profile(self) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        return await self._aggregate(profile)

    async def update_profile(self, values: dict[str, Any]) -> dict[str, Any]:
        profile = await self._profile(create=True, lock=True)
        assert profile is not None
        short = int(values.get("short_bucket_months", profile.short_bucket_months))
        medium = int(values.get("medium_bucket_months", profile.medium_bucket_months))
        if short <= 0 or medium <= short:
            raise ValueError("期限分层必须满足 0 < 短期边界 < 中期边界")
        aspirational = float(values.get("aspirational_cap", profile.aspirational_cap))
        satellite = float(values.get("satellite_cap", profile.satellite_cap))
        if not 0 <= aspirational <= 0.20 or not 0 <= satellite <= 0.30:
            raise ValueError("进取层或卫星上限超出允许范围")
        allowed = {"name", "annual_essential_spending", "short_bucket_months", "medium_bucket_months",
                   "aspirational_cap", "satellite_cap", "settings_json"}
        for key, value in values.items():
            if key in allowed:
                setattr(profile, key, value)
        profile.updated_at = datetime.now(UTC)
        await self.session.commit()
        return await self._aggregate(profile)

    async def create_item(self, kind: str, values: dict[str, Any]) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        models = {"members": HouseholdMember, "assets": WealthAsset, "liabilities": WealthLiability, "goals": WealthGoal}
        model = models[kind]
        if kind == "members" and values.get("role") == "self":
            existing = (await self.session.execute(select(HouseholdMember).where(
                HouseholdMember.profile_id == profile.id, HouseholdMember.role == "self"))).scalar_one_or_none()
            if existing:
                raise ValueError("家庭财富档案只能有一名本人")
            values["is_primary"] = True
        elif kind == "members":
            values["is_primary"] = False
        await self._validate_item_references(profile, kind, values)
        row = model(profile_id=profile.id, **values)
        self.session.add(row)
        await self.session.commit()
        return self._row(row)

    async def update_item(self, kind: str, item_id: UUID, values: dict[str, Any]) -> dict[str, Any]:
        row = await self._owned(kind, item_id, lock=True)
        if row is None:
            raise ValueError("记录不存在")
        profile = await self._profile()
        assert profile is not None
        if kind == "members" and values.get("role") == "self" and row.role != "self":
            existing = (await self.session.execute(select(HouseholdMember.id).where(
                HouseholdMember.profile_id == profile.id, HouseholdMember.role == "self"))).scalar_one_or_none()
            if existing:
                raise ValueError("家庭财富档案只能有一名本人")
            values["is_primary"] = True
        if kind == "members" and row.role == "self" and values.get("role", "self") != "self":
            raise ValueError("不能把家庭财富档案中的本人改为其他角色")
        if kind == "members":
            values["is_primary"] = values.get("role", row.role) == "self"
        await self._validate_item_references(profile, kind, values)
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await self.session.commit()
        return self._row(row)

    async def delete_item(self, kind: str, item_id: UUID) -> None:
        row = await self._owned(kind, item_id)
        if row is None:
            raise ValueError("记录不存在")
        if kind == "members" and row.role == "self":
            raise ValueError("不能删除家庭财富档案中的本人")
        await self.session.delete(row)
        await self.session.commit()

    async def replace_assignments(self, values: list[dict[str, Any]]) -> dict[str, Any]:
        profile = await self._profile(create=True, lock=True)
        assert profile is not None
        assets = {row.id: row for row in (await self.session.execute(select(WealthAsset).where(
            WealthAsset.profile_id == profile.id))).scalars().all()}
        goals = {row.id: row for row in (await self.session.execute(select(WealthGoal).where(
            WealthGoal.profile_id == profile.id))).scalars().all()}
        totals: dict[UUID, float] = {}
        for item in values:
            asset_id = UUID(str(item["asset_id"]))
            goal_id = UUID(str(item["goal_id"])) if item.get("goal_id") else None
            if asset_id not in assets or (goal_id and goal_id not in goals):
                raise ValueError("资金指定引用了不属于当前用户的资产或目标")
            if not goal_id and item.get("layer") not in {"safety", "market", "aspirational"}:
                raise ValueError("资金指定必须选择目标或财富层")
            if goal_id and not item.get("layer"):
                raise ValueError("目标资金指定必须同时标明安全、市场或进取层")
            amount = float(item["amount_cny"])
            totals[asset_id] = totals.get(asset_id, 0) + amount
            if totals[asset_id] > float(assets[asset_id].value_cny) + 1e-6:
                raise ValueError(f"资产“{assets[asset_id].name}”的指定金额超过当前价值")
            if goal_id:
                goal = goals[goal_id]
                if goal.priority == "essential" and item.get("layer") == "aspirational":
                    raise ValueError(f"必须保障目标“{goal.name}”不能使用进取层资金")
                if (horizon_bucket(goal.target_date, profile.short_bucket_months,
                                   profile.medium_bucket_months) == "short"
                        and assets[asset_id].liquidity == "illiquid"):
                    raise ValueError(f"短期目标“{goal.name}”不能依赖非流动资产“{assets[asset_id].name}”")
        await self.session.execute(delete(WealthAssignment).where(WealthAssignment.profile_id == profile.id))
        for item in values:
            self.session.add(WealthAssignment(profile_id=profile.id, **item))
        await self.session.commit()
        return await self._aggregate(profile)

    async def framework_preview(self) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        aggregate = await self._aggregate(profile)
        return {"preview": True, "write_performed": False, **aggregate["framework"]}

    async def create_framework_version(self) -> dict[str, Any]:
        profile = await self._profile(create=True, lock=True)
        assert profile is not None
        aggregate = await self._aggregate(profile)
        if not aggregate["framework"]["ready"]:
            raise ValueError("请先解决财富框架中的硬冲突，再确认版本")
        snapshot = {key: aggregate[key] for key in ("profile", "members", "assets", "liabilities", "goals", "assignments")}
        content = {"snapshot": snapshot, "summary": aggregate["framework"]["summary"],
                   "conflicts": aggregate["framework"]["conflicts"]}
        fingerprint = stable_hash(content)
        existing = (await self.session.execute(select(WealthFrameworkVersion).where(
            WealthFrameworkVersion.profile_id == profile.id,
            WealthFrameworkVersion.content_hash == fingerprint))).scalar_one_or_none()
        if existing:
            return self._framework_version(existing)
        version = int((await self.session.execute(select(func.coalesce(func.max(WealthFrameworkVersion.version), 0)).where(
            WealthFrameworkVersion.profile_id == profile.id))).scalar_one()) + 1
        row = WealthFrameworkVersion(profile_id=profile.id, version=version, snapshot=snapshot,
            summary=aggregate["framework"]["summary"], conflicts=aggregate["framework"]["conflicts"],
            content_hash=fingerprint)
        self.session.add(row)
        await self.session.commit()
        return self._framework_version(row)

    async def framework_versions(self) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        rows = (await self.session.execute(select(WealthFrameworkVersion).where(
            WealthFrameworkVersion.profile_id == profile.id).order_by(desc(WealthFrameworkVersion.version)))).scalars().all()
        return {"items": [self._framework_version(row) for row in rows]}

    async def create_saa(self, values: dict[str, Any]) -> dict[str, Any]:
        profile = await self._profile(create=True, lock=True)
        assert profile is not None
        framework = await self.session.get(WealthFrameworkVersion, UUID(str(values["framework_version_id"])))
        if framework is None or framework.profile_id != profile.id:
            raise ValueError("家庭财富框架版本不存在")
        source_id = values.get("source_allocation_policy_version_id")
        targets = values.get("targets") or []
        source_type = "manual"
        if source_id:
            policy = await self.session.get(AllocationPolicyVersion, UUID(str(source_id)))
            if policy is None:
                raise ValueError("配置版本不存在")
            account = await self.session.get(AllocationAccount, policy.account_id)
            if account is None or account.user_id != self.user_id:
                raise ValueError("配置版本不存在")
            sleeves = (await self.session.execute(select(AllocationPolicySleeve).where(
                AllocationPolicySleeve.policy_version_id == policy.id))).scalars().all()
            targets = [{"key": row.sleeve_key, "label": row.label, "layer": "safety" if row.sleeve_key == "cny_cash" else "market",
                        "target_weight": float(row.target_weight), "min_weight": float(row.min_weight),
                        "max_weight": float(row.max_weight)} for row in sleeves]
            source_type = "allocation_policy"
        self._validate_targets(targets)
        layer_weights = {"safety": 0.0, "market": 0.0, "aspirational": 0.0}
        for target in targets:
            layer = target.get("layer")
            if layer in layer_weights:
                layer_weights[layer] += float(target["target_weight"])
        framework_summary = framework.summary or {}
        allocatable = float(framework_summary.get("allocatable_wealth_cny") or 0)
        safety_required = float(framework_summary.get("safety_required_cny") or 0)
        required_safety_weight = min(1.0, safety_required / allocatable) if allocatable > 0 else 0.0
        if layer_weights["safety"] + 1e-6 < required_safety_weight:
            raise ValueError("SAA安全层权重不足以覆盖已确认财富框架的安全需求")
        if layer_weights["aspirational"] > float(profile.aspirational_cap) + 1e-6:
            raise ValueError("SAA进取层权重超过财富框架上限")
        effective = values["effective_date"]
        review = values["review_date"]
        if review <= effective:
            raise ValueError("SAA复核日期必须晚于生效日期")
        version = int((await self.session.execute(select(func.coalesce(func.max(SaaPolicyVersion.version), 0)).where(
            SaaPolicyVersion.profile_id == profile.id))).scalar_one()) + 1
        constraints = {"framework_summary": framework.summary, "framework_conflicts": framework.conflicts,
                       "aspirational_cap": float(profile.aspirational_cap), "satellite_cap": float(profile.satellite_cap)}
        content = {"framework_version_id": framework.id, "targets": targets, "constraints": constraints,
                   "effective_date": effective, "review_date": review, "source_type": source_type}
        row = SaaPolicyVersion(profile_id=profile.id, framework_version_id=framework.id,
            source_allocation_policy_version_id=UUID(str(source_id)) if source_id else None, version=version,
            name=values["name"], effective_date=effective, review_date=review, targets=targets,
            constraints_snapshot=constraints, source_type=source_type, content_hash=stable_hash(content))
        self.session.add(row)
        await self.session.commit()
        return self._saa(row)

    async def saa_versions(self) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        rows = (await self.session.execute(select(SaaPolicyVersion).where(
            SaaPolicyVersion.profile_id == profile.id).order_by(desc(SaaPolicyVersion.version)))).scalars().all()
        return {"items": [self._saa(row) for row in rows]}

    async def confirm_saa(self, version_id: UUID) -> dict[str, Any]:
        row = await self._owned_saa(version_id, lock=True)
        if row is None:
            raise ValueError("SAA版本不存在")
        await self.session.execute(select(SaaPolicyVersion).where(
            SaaPolicyVersion.profile_id == row.profile_id, SaaPolicyVersion.status == "confirmed").with_for_update())
        await self.session.execute(
            update(SaaPolicyVersion).where(
                SaaPolicyVersion.profile_id == row.profile_id, SaaPolicyVersion.status == "confirmed",
                SaaPolicyVersion.id != row.id).values(status="superseded"))
        row.status = "confirmed"
        await self.session.commit()
        return self._saa(row)

    async def create_taa(self, values: dict[str, Any]) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        saa = await self._owned_saa(UUID(str(values["saa_version_id"])))
        if saa is None or saa.status != "confirmed":
            raise ValueError("TAA只能建立在已确认SAA之上")
        snapshot_id = values.get("opportunity_snapshot_id")
        if snapshot_id:
            snapshot = (await self.session.execute(select(MarketOpportunitySnapshot).join(
                MarketOpportunity, MarketOpportunity.id == MarketOpportunitySnapshot.opportunity_id).where(
                    MarketOpportunitySnapshot.id == UUID(str(snapshot_id)),
                    or_(MarketOpportunity.scope == "global", MarketOpportunity.user_id == self.user_id)
                ))).scalar_one_or_none()
            if snapshot is None:
                raise ValueError("机会证据快照不存在或当前用户不可见")
            values["evidence"] = _response_json(snapshot.evidence)
            values["falsifiers"] = list(snapshot.falsifiers or [])
        self._validate_taa(saa, values)
        content = {key: values.get(key) for key in ("saa_version_id", "opportunity_snapshot_id", "title", "deltas",
                                                     "rationale", "evidence", "falsifiers", "starts_at", "review_at", "expires_at")}
        row = TaaOverlay(profile_id=profile.id, content_hash=stable_hash(content), **values)
        self.session.add(row)
        await self.session.commit()
        return self._taa(row)

    async def taa_overlays(self) -> dict[str, Any]:
        profile = await self._profile(create=True)
        assert profile is not None
        rows = (await self.session.execute(select(TaaOverlay).where(
            TaaOverlay.profile_id == profile.id).order_by(desc(TaaOverlay.created_at)))).scalars().all()
        today = date.today()
        changed = False
        for row in rows:
            if row.status == "confirmed" and row.expires_at < today:
                row.status = "expired"
                changed = True
        if changed:
            await self.session.commit()
        return {"items": [self._taa(row) for row in rows]}

    async def confirm_taa(self, overlay_id: UUID) -> dict[str, Any]:
        row = await self._owned_taa(overlay_id, lock=True)
        if row is None:
            raise ValueError("TAA草案不存在")
        if row.status != "draft" or row.expires_at < date.today():
            raise ValueError("只有未过期的TAA草案可以确认")
        saa = await self._owned_saa(row.saa_version_id)
        if saa is None or saa.status != "confirmed":
            raise ValueError("TAA引用的SAA已不再是当前确认基线")
        row.status = "confirmed"
        await self.session.commit()
        return self._taa(row)

    async def close_taa(self, overlay_id: UUID) -> dict[str, Any]:
        row = await self._owned_taa(overlay_id, lock=True)
        if row is None:
            raise ValueError("TAA记录不存在")
        row.status = "closed"
        await self.session.commit()
        return self._taa(row)

    async def _aggregate(self, profile: WealthProfile) -> dict[str, Any]:
        members = (await self.session.execute(select(HouseholdMember).where(HouseholdMember.profile_id == profile.id)
            .order_by(HouseholdMember.is_primary.desc(), HouseholdMember.birth_date))).scalars().all()
        assets = (await self.session.execute(select(WealthAsset).where(WealthAsset.profile_id == profile.id)
            .order_by(desc(WealthAsset.value_cny)))).scalars().all()
        liabilities = (await self.session.execute(select(WealthLiability).where(WealthLiability.profile_id == profile.id)
            .order_by(desc(WealthLiability.balance_cny)))).scalars().all()
        goals = (await self.session.execute(select(WealthGoal).where(WealthGoal.profile_id == profile.id)
            .order_by(WealthGoal.target_date))).scalars().all()
        assignments = (await self.session.execute(select(WealthAssignment).where(
            WealthAssignment.profile_id == profile.id))).scalars().all()
        asset_map = {row.id: row for row in assets}
        goal_map = {row.id: row for row in goals}
        prepared: dict[UUID, float] = {}
        layer_amounts = {"safety": 0.0, "market": 0.0, "aspirational": 0.0}
        assigned_by_asset: dict[UUID, float] = {}
        conflicts: list[str] = []
        for row in assignments:
            amount = float(row.amount_cny)
            assigned_by_asset[row.asset_id] = assigned_by_asset.get(row.asset_id, 0) + amount
            if row.goal_id:
                prepared[row.goal_id] = prepared.get(row.goal_id, 0) + amount
                goal = goal_map.get(row.goal_id)
                asset = asset_map.get(row.asset_id)
                if goal and goal.priority == "essential" and row.layer == "aspirational":
                    conflicts.append(f"必须保障目标“{goal.name}”不能使用进取层资金")
                if goal and asset and horizon_bucket(goal.target_date, profile.short_bucket_months,
                                                     profile.medium_bucket_months) == "short" and asset.liquidity == "illiquid":
                    conflicts.append(f"短期目标“{goal.name}”不能依赖非流动资产“{asset.name}”")
            if row.layer in layer_amounts:
                layer_amounts[row.layer] += amount
        for asset_id, total in assigned_by_asset.items():
            asset = asset_map.get(asset_id)
            if asset and total > float(asset.value_cny) + 1e-6:
                conflicts.append(f"资产“{asset.name}”的指定金额超过当前价值")
        if not any(row.role == "self" for row in members):
            conflicts.append("请先添加一名家庭成员并将角色设为本人")
        total_assets = sum(float(row.value_cny) for row in assets)
        total_liabilities = sum(float(row.balance_cny) for row in liabilities)
        liquid_wealth = sum(float(row.value_cny) for row in assets if row.liquidity == "liquid")
        allocatable = sum(float(row.value_cny) for row in assets if row.allocatable and row.liquidity != "illiquid")
        income = sum(float(row.annual_income) for row in members)
        goal_rows = []
        essential_gap = 0.0
        for row in goals:
            ready = prepared.get(row.id, 0)
            gap = max(0.0, float(row.target_amount_cny) - ready)
            if row.priority == "essential":
                essential_gap += gap
            goal_rows.append({**self._row(row), "prepared_amount_cny": ready, "funding_gap_cny": gap,
                              "coverage_ratio": min(1.0, ready / float(row.target_amount_cny)),
                              "bucket": horizon_bucket(row.target_date, profile.short_bucket_months,
                                                       profile.medium_bucket_months)})
        emergency_months = int((profile.settings_json or {}).get("emergency_months", 12))
        emergency_reserve = float(profile.annual_essential_spending) / 12 * emergency_months
        safety_required = emergency_reserve + essential_gap
        if safety_required > allocatable + 1e-6:
            conflicts.append("可配置财富不足以覆盖安全层需求")
        aspirational_limit = allocatable * float(profile.aspirational_cap)
        if layer_amounts["aspirational"] > aspirational_limit + 1e-6:
            conflicts.append("进取层指定金额超过当前上限")
        market_available = max(0.0, allocatable - max(safety_required, layer_amounts["safety"]) - layer_amounts["aspirational"])
        satellite_budget = market_available * float(profile.satellite_cap)
        summary = {"total_assets_cny": total_assets, "total_liabilities_cny": total_liabilities,
                   "net_wealth_cny": total_assets - total_liabilities, "liquid_wealth_cny": liquid_wealth,
                   "allocatable_wealth_cny": allocatable, "annual_household_income_cny": income,
                   "essential_spending_coverage_months": (liquid_wealth / float(profile.annual_essential_spending) * 12)
                   if float(profile.annual_essential_spending) > 0 else None,
                   "safety_required_cny": safety_required, "market_available_cny": market_available,
                   "aspirational_limit_cny": aspirational_limit, "core_budget_cny": market_available - satellite_budget,
                   "satellite_budget_cny": satellite_budget, "layer_assignments_cny": layer_amounts,
                   "goal_funding_gap_cny": sum(row["funding_gap_cny"] for row in goal_rows)}
        return {"profile": self._row(profile), "members": [self._member(row) for row in members],
                "assets": [self._row(row) for row in assets], "liabilities": [self._row(row) for row in liabilities],
                "goals": goal_rows, "assignments": [self._row(row) for row in assignments],
                "framework": {"summary": summary, "conflicts": list(dict.fromkeys(conflicts)),
                              "ready": bool(members) and not conflicts}}

    async def _owned(self, kind: str, item_id: UUID, *, lock: bool = False):
        profile = await self._profile()
        if profile is None:
            return None
        models = {"members": HouseholdMember, "assets": WealthAsset, "liabilities": WealthLiability, "goals": WealthGoal}
        model = models[kind]
        query = select(model).where(model.id == item_id, model.profile_id == profile.id)
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def _validate_item_references(self, profile: WealthProfile, kind: str,
                                        values: dict[str, Any]) -> None:
        reference = "member_id" if kind == "goals" else "owner_member_id" if kind in {"assets", "liabilities"} else None
        if reference is None or not values.get(reference):
            return
        member = (await self.session.execute(select(HouseholdMember.id).where(
            HouseholdMember.id == UUID(str(values[reference])),
            HouseholdMember.profile_id == profile.id))).scalar_one_or_none()
        if member is None:
            raise ValueError("关联家庭成员不存在")

    async def _owned_saa(self, version_id: UUID, *, lock: bool = False) -> SaaPolicyVersion | None:
        profile = await self._profile()
        if profile is None:
            return None
        query = select(SaaPolicyVersion).where(SaaPolicyVersion.id == version_id,
                                               SaaPolicyVersion.profile_id == profile.id)
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    async def _owned_taa(self, overlay_id: UUID, *, lock: bool = False) -> TaaOverlay | None:
        profile = await self._profile()
        if profile is None:
            return None
        query = select(TaaOverlay).where(TaaOverlay.id == overlay_id, TaaOverlay.profile_id == profile.id)
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    @staticmethod
    def _validate_targets(targets: list[dict[str, Any]]) -> None:
        if not targets:
            raise ValueError("SAA至少需要一个战略目标")
        keys = [str(item.get("key") or "") for item in targets]
        if len(keys) != len(set(keys)):
            raise ValueError("SAA资产类别标识不能重复")
        total = 0.0
        for item in targets:
            target = float(item.get("target_weight", -1))
            lower = float(item.get("min_weight", -1))
            upper = float(item.get("max_weight", -1))
            if not 0 <= lower <= target <= upper <= 1:
                raise ValueError("SAA目标必须满足 0 ≤ 下限 ≤ 目标 ≤ 上限 ≤ 1")
            total += target
        if abs(total - 1) > 1e-6:
            raise ValueError("SAA目标权重之和必须为100%")

    @staticmethod
    def _validate_taa(saa: SaaPolicyVersion, values: dict[str, Any]) -> None:
        starts, review, expires = values["starts_at"], values["review_at"], values["expires_at"]
        if not starts <= review <= expires:
            raise ValueError("TAA日期必须满足生效日 ≤ 复核日 ≤ 失效日")
        if expires - starts > timedelta(days=180):
            raise ValueError("TAA最长有效期为180天")
        targets = {item["key"]: item for item in saa.targets}
        deltas = {key: float(value) for key, value in values["deltas"].items()}
        if not deltas or not any(abs(value) > 1e-9 for value in deltas.values()):
            raise ValueError("TAA必须包含真实的非零权重偏离")
        if abs(sum(deltas.values())) > 1e-6:
            raise ValueError("TAA所有权重增减之和必须为零")
        for key, delta in deltas.items():
            target = targets.get(key)
            if target is None:
                raise ValueError(f"TAA引用了SAA中不存在的资产类别：{key}")
            if target.get("layer") == "safety" and abs(delta) > 1e-9:
                raise ValueError("TAA不能调整安全层")
            adjusted = float(target["target_weight"]) + delta
            if adjusted < float(target["min_weight"]) - 1e-9 or adjusted > float(target["max_weight"]) + 1e-9:
                raise ValueError(f"TAA调整后的{target.get('label') or key}超出SAA允许区间")

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {column.name: _response_json(getattr(row, column.name)) for column in row.__table__.columns}

    @staticmethod
    def _member(row: HouseholdMember) -> dict[str, Any]:
        payload = WealthService._row(row)
        payload["age"] = age_on(row.birth_date)
        if row.retirement_age is not None:
            years = row.retirement_age - payload["age"]
            payload["life_stage"] = "retired" if years <= 0 else "transition" if years <= 10 else "accumulation"
        else:
            payload["life_stage"] = "unspecified"
        return payload

    @staticmethod
    def _framework_version(row: WealthFrameworkVersion) -> dict[str, Any]:
        return {"id": str(row.id), "profile_id": str(row.profile_id), "version": row.version,
                "snapshot": row.snapshot, "summary": row.summary, "conflicts": row.conflicts,
                "content_hash": row.content_hash, "created_at": row.created_at}

    @staticmethod
    def _saa(row: SaaPolicyVersion) -> dict[str, Any]:
        return {"id": str(row.id), "profile_id": str(row.profile_id),
                "framework_version_id": str(row.framework_version_id),
                "source_allocation_policy_version_id": str(row.source_allocation_policy_version_id) if row.source_allocation_policy_version_id else None,
                "version": row.version, "name": row.name, "effective_date": row.effective_date,
                "review_date": row.review_date, "targets": row.targets, "constraints_snapshot": row.constraints_snapshot,
                "source_type": row.source_type, "status": row.status, "content_hash": row.content_hash,
                "created_at": row.created_at}

    @staticmethod
    def _taa(row: TaaOverlay) -> dict[str, Any]:
        return {"id": str(row.id), "profile_id": str(row.profile_id), "saa_version_id": str(row.saa_version_id),
                "opportunity_snapshot_id": str(row.opportunity_snapshot_id) if row.opportunity_snapshot_id else None,
                "title": row.title, "deltas": row.deltas, "rationale": row.rationale, "evidence": row.evidence,
                "falsifiers": row.falsifiers, "starts_at": row.starts_at, "review_at": row.review_at,
                "expires_at": row.expires_at, "status": row.status, "content_hash": row.content_hash,
                "created_at": row.created_at, "updated_at": row.updated_at}
