"""Deterministic, user-owned strategic asset-allocation research."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import numpy as np
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import (
    AllocationAccount,
    AllocationPolicyImplementation,
    AllocationPolicySleeve,
    AllocationPolicyThesisLink,
    AllocationPolicyVersion,
    ResearchThesis,
    ResearchThesisVersion,
)
from services.agent_platform.tushare import TushareReadService


SLEEVE_LABELS = {
    "cny_cash": "人民币流动性",
    "china_equity": "中国股票",
    "global_equity": "全球股票",
    "china_bond": "中国债券",
    "global_bond": "全球债券",
    "gold": "黄金",
    "broad_commodity": "广义商品",
}
RISK_SLEEVES = ["china_equity", "global_equity", "china_bond", "global_bond", "gold"]
STRESS_LIBRARY = {
    "global_growth": {"china_equity": -0.32, "global_equity": -0.35, "china_bond": 0.04, "global_bond": 0.06, "gold": 0.10, "broad_commodity": -0.22},
    "inflation_rates": {"china_equity": -0.16, "global_equity": -0.18, "china_bond": -0.10, "global_bond": -0.12, "gold": 0.12, "broad_commodity": 0.18},
    "china_risk": {"china_equity": -0.30, "global_equity": -0.08, "china_bond": -0.04, "global_bond": 0.02, "gold": 0.08, "broad_commodity": -0.08},
    "liquidity": {"china_equity": -0.28, "global_equity": -0.30, "china_bond": -0.08, "global_bond": -0.10, "gold": -0.06, "broad_commodity": -0.24},
}


def _json(value: Any) -> Any:
    if isinstance(value, (datetime, Decimal, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json(item) for item in value]
    return value


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(_json(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def constrained_risk_parity(returns: np.ndarray, lower: np.ndarray | None = None,
                            upper: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Solve equal-risk contribution with Ledoit-Wolf covariance and transparent bounds."""
    if returns.ndim != 2 or returns.shape[0] < 2 or returns.shape[1] < 2:
        raise ValueError("risk budgeting requires at least two assets and two observations")
    covariance = LedoitWolf().fit(returns).covariance_
    size = returns.shape[1]
    lower = np.zeros(size) if lower is None else lower.astype(float)
    upper = np.full(size, 0.55) if upper is None else upper.astype(float)
    if lower.sum() > 1 + 1e-9 or upper.sum() < 1 - 1e-9:
        raise ValueError("weight bounds cannot sum to one")

    def contributions(weights: np.ndarray) -> np.ndarray:
        variance = float(weights @ covariance @ weights)
        if variance <= 0:
            return np.zeros_like(weights)
        return weights * (covariance @ weights) / variance

    def objective(weights: np.ndarray) -> float:
        rc = contributions(weights)
        return float(np.sum((rc - (1 / size)) ** 2))

    initial = np.clip(np.full(size, 1 / size), lower, upper)
    initial = initial / initial.sum()
    result = minimize(objective, initial, method="SLSQP", bounds=list(zip(lower, upper)),
                      constraints=[{"type": "eq", "fun": lambda weights: float(weights.sum() - 1)}],
                      options={"ftol": 1e-12, "maxiter": 1000})
    if not result.success:
        raise ValueError(f"risk budget optimizer failed: {result.message}")
    weights = np.asarray(result.x)
    return weights, contributions(weights), covariance


def policy_from_returns(*, capital: float, reserve: float, max_drawdown: float,
                        sleeves: list[str], returns: np.ndarray, max_leverage: float = 1.0) -> dict[str, Any]:
    if capital <= 0 or reserve < 0:
        raise ValueError("capital and reserve are invalid")
    if reserve > capital:
        return {"status": "infeasible", "reasons": ["流动性储备与未来现金需求超过总资金"]}
    risky_weights, risk_contributions, covariance = constrained_risk_parity(returns)
    investable_fraction = (capital - reserve) / capital
    stress_at_full_risk = []
    for key, shocks in STRESS_LIBRARY.items():
        loss = float(sum(risky_weights[index] * shocks.get(sleeve, 0) for index, sleeve in enumerate(sleeves)))
        stress_at_full_risk.append((key, loss))
    worst_full = min((loss for _, loss in stress_at_full_risk), default=0)
    risk_fraction = min(investable_fraction, max_leverage)
    if worst_full < 0:
        risk_fraction = min(risk_fraction, max_drawdown / abs(worst_full))
    total_risky = risky_weights * max(0, risk_fraction)
    cash_weight = 1 - float(total_risky.sum())
    portfolio_stress = [{"scenario": key, "return": loss * risk_fraction} for key, loss in stress_at_full_risk]
    annualized_volatility = float(np.sqrt(max(0, total_risky @ covariance @ total_risky) * 12))
    return {
        "status": "feasible",
        "weights": {"cny_cash": cash_weight, **{sleeve: float(total_risky[i]) for i, sleeve in enumerate(sleeves)}},
        "risk_contributions": {sleeve: float(risk_contributions[i]) for i, sleeve in enumerate(sleeves)},
        "stress_results": portfolio_stress,
        "risk_summary": {
            "annualized_volatility": annualized_volatility,
            "worst_stress_return": min((row["return"] for row in portfolio_stress), default=0),
            "gross_underlying_exposure": float(total_risky.sum()),
            "cash_weight": cash_weight,
        },
    }


def apply_tactical_tilts(result: dict[str, Any], tilts: list[dict[str, Any]], *, returns: np.ndarray,
                         sleeves: list[str], max_drawdown: float, max_leverage: float) -> dict[str, Any]:
    """Apply only self-financing, thesis-linked tilts and recompute all reported risk."""
    if not tilts:
        return result
    if abs(sum(float(item["weight_delta"]) for item in tilts)) > 1e-8:
        raise ValueError("Tactical tilt deltas must sum to zero; no automatic normalization is allowed")
    weights = dict(result["weights"])
    for item in tilts:
        key = str(item["sleeve_key"])
        if key not in weights:
            raise ValueError(f"Unknown tactical sleeve: {key}")
        weights[key] = float(weights[key]) + float(item["weight_delta"])
    if any(value < -1e-10 or value > 1 + 1e-10 for value in weights.values()) or abs(sum(weights.values()) - 1) > 1e-8:
        raise ValueError("Tactical tilt would create invalid portfolio weights")
    risky = np.asarray([weights[key] for key in sleeves], dtype=float)
    gross = float(np.abs(risky).sum())
    if gross > max_leverage + 1e-8:
        raise ValueError("Tactical tilt exceeds the account leverage limit")
    covariance = LedoitWolf().fit(returns).covariance_
    variance = float(risky @ covariance @ risky)
    contributions = risky * (covariance @ risky) / variance if variance > 0 else np.zeros_like(risky)
    stresses = [{"scenario": name, "return": float(sum(weights.get(key, 0) * shock for key, shock in shocks.items()))}
                for name, shocks in STRESS_LIBRARY.items()]
    worst = min((item["return"] for item in stresses), default=0)
    if worst < -max_drawdown - 1e-8:
        raise ValueError("Tactical tilt exceeds the account maximum stress drawdown")
    result = dict(result)
    result["weights"] = weights
    result["risk_contributions"] = {key: float(contributions[index]) for index, key in enumerate(sleeves)}
    result["stress_results"] = stresses
    result["risk_summary"] = {**result["risk_summary"], "annualized_volatility": float(np.sqrt(max(0, variance) * 12)),
                              "worst_stress_return": worst, "gross_underlying_exposure": gross,
                              "cash_weight": float(weights.get("cny_cash", 0)), "tactical_tilt_count": len(tilts)}
    return result


class AllocationService:
    def __init__(self, session: AsyncSession, reader: TushareReadService, user_id: UUID):
        self.session = session
        self.reader = reader
        self.user_id = user_id

    async def data_status(self) -> dict[str, Any]:
        return await self.reader.allocation_catalog()

    async def universe(self) -> dict[str, Any]:
        catalog = await self.reader.allocation_catalog()
        instruments = await self.reader.allocation_instruments()
        return {"catalog": catalog, "instruments": instruments, "scoring": False,
                "derivatives_are_asset_classes": False}

    async def series_history(self, series_id: str) -> dict[str, Any]:
        catalog = await self.reader.allocation_catalog()
        if not any(row.get("series_id") == series_id for row in catalog.get("series") or []):
            raise ValueError("Allocation series not found")
        return await self.reader.allocation_series_history(series_id)

    async def list_accounts(self) -> dict[str, Any]:
        rows = (await self.session.execute(select(AllocationAccount).where(
            AllocationAccount.user_id == self.user_id).order_by(desc(AllocationAccount.updated_at)))).scalars().all()
        return {"items": [self._account(row) for row in rows]}

    async def create_account(self, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_account(values)
        row = AllocationAccount(user_id=self.user_id, **values)
        self.session.add(row)
        await self.session.commit()
        return self._account(row)

    async def update_account(self, account_id: UUID, values: dict[str, Any]) -> dict[str, Any]:
        row = await self._owned_account(account_id, lock=True)
        if row is None:
            raise ValueError("Allocation account not found")
        merged = {**self._account(row), **values}
        self._validate_account(merged)
        for key, value in values.items():
            if key in {"name", "capital", "horizon_months", "liquidity_reserve", "max_drawdown", "max_leverage",
                       "future_cash_needs", "allowed_markets", "allowed_instruments", "hard_restrictions", "status"}:
                setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await self.session.commit()
        return self._account(row)

    async def delete_account(self, account_id: UUID) -> None:
        row = await self._owned_account(account_id)
        if row is None:
            raise ValueError("Allocation account not found")
        await self.session.delete(row)
        await self.session.commit()

    async def list_versions(self, account_id: UUID) -> dict[str, Any]:
        account = await self._owned_account(account_id)
        if account is None:
            raise ValueError("Allocation account not found")
        rows = (await self.session.execute(select(AllocationPolicyVersion).where(
            AllocationPolicyVersion.account_id == account.id).order_by(desc(AllocationPolicyVersion.version)))).scalars().all()
        return {"items": [self._version_summary(row, account) for row in rows],
                "current_policy_version_id": str(account.current_policy_version_id) if account.current_policy_version_id else None}

    async def version_detail(self, version_id: UUID) -> dict[str, Any] | None:
        query = select(AllocationPolicyVersion, AllocationAccount).join(
            AllocationAccount, AllocationAccount.id == AllocationPolicyVersion.account_id).where(
            AllocationPolicyVersion.id == version_id, AllocationAccount.user_id == self.user_id)
        pair = (await self.session.execute(query)).first()
        if pair is None:
            return None
        version, account = pair
        sleeves = (await self.session.execute(select(AllocationPolicySleeve).where(
            AllocationPolicySleeve.policy_version_id == version.id).order_by(AllocationPolicySleeve.sleeve_key))).scalars().all()
        implementations = (await self.session.execute(select(AllocationPolicyImplementation).where(
            AllocationPolicyImplementation.policy_version_id == version.id).order_by(
            AllocationPolicyImplementation.sleeve_key, AllocationPolicyImplementation.instrument_code))).scalars().all()
        links = (await self.session.execute(select(AllocationPolicyThesisLink).where(
            AllocationPolicyThesisLink.policy_version_id == version.id))).scalars().all()
        return {**self._version_summary(version, account), "account": self._account(account),
                "constraint_snapshot": version.constraint_snapshot, "methodology_snapshot": version.methodology_snapshot,
                "data_snapshot": version.data_snapshot, "risk_summary": version.risk_summary,
                "stress_results": version.stress_results, "infeasible_reasons": version.infeasible_reasons,
                "sleeves": [self._sleeve(row) for row in sleeves],
                "implementations": [self._implementation(row) for row in implementations],
                "tactical_tilts": [self._thesis_link(row) for row in links]}

    async def generate_version(self, account_id: UUID, tactical_tilts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        account = await self._owned_account(account_id, lock=True)
        if account is None:
            raise ValueError("Allocation account not found")
        constraints = self._constraint_snapshot(account)
        catalog = await self.reader.allocation_catalog()
        reserve = float(account.liquidity_reserve) + sum(float(item.get("amount") or 0) for item in account.future_cash_needs or [])
        if reserve > float(account.capital):
            result = {"status": "infeasible", "reasons": ["流动性储备与未来现金需求超过总资金"]}
            return await self._persist(account, constraints, catalog, result, [], tactical_tilts or [])
        if not catalog.get("formal_ready"):
            reasons = [f"{SLEEVE_LABELS.get(key, key)}：数据门禁未通过" for key in catalog.get("missing_required") or []]
            result = {"status": "unavailable", "reasons": reasons or ["资产配置数据不可用"]}
            return await self._persist(account, constraints, catalog, result, [], tactical_tilts or [])
        selected = []
        for sleeve in RISK_SLEEVES:
            candidates = [row for row in catalog["series"] if row.get("sleeve_key") == sleeve and row.get("enabled") and row.get("quality_state") == "ready"]
            if not candidates:
                result = {"status": "unavailable", "reasons": [f"{SLEEVE_LABELS[sleeve]}没有通过门禁的总回报序列"]}
                return await self._persist(account, constraints, catalog, result, [], tactical_tilts or [])
            selected.append(sorted(candidates, key=lambda row: row["series_id"])[0])
        monthly = await self.reader.allocation_monthly([row["series_id"] for row in selected])
        dates = sorted(set.intersection(*[
            {str(row["month_end"]) for row in monthly if row["series_id"] == series["series_id"] and row.get("monthly_return") is not None}
            for series in selected
        ])) if monthly else []
        if len(dates) < 120:
            result = {"status": "unavailable", "reasons": [f"共同完整历史只有 {len(dates)} 个月，至少需要120个月"]}
            return await self._persist(account, constraints, catalog, result, selected, tactical_tilts or [])
        lookup = {(row["series_id"], str(row["month_end"])): float(row["monthly_return"]) for row in monthly if row.get("monthly_return") is not None}
        matrix = np.asarray([[lookup[(series["series_id"], month)] for series in selected] for month in dates], dtype=float)
        result = policy_from_returns(capital=float(account.capital), reserve=reserve,
                                     max_drawdown=float(account.max_drawdown), max_leverage=float(account.max_leverage),
                                     sleeves=RISK_SLEEVES, returns=matrix)
        if tactical_tilts:
            await self._validate_tactical_tilts(tactical_tilts)
            result = apply_tactical_tilts(result, tactical_tilts, returns=matrix, sleeves=RISK_SLEEVES,
                                           max_drawdown=float(account.max_drawdown), max_leverage=float(account.max_leverage))
        result["common_history"] = {"start": dates[0], "end": dates[-1], "months": len(dates)}
        return await self._persist(account, constraints, catalog, result, selected, tactical_tilts or [])

    async def confirm_version(self, account_id: UUID, version_id: UUID) -> dict[str, Any]:
        account = await self._owned_account(account_id, lock=True)
        version = await self.session.get(AllocationPolicyVersion, version_id)
        if account is None or version is None or version.account_id != account.id:
            raise ValueError("Allocation policy version not found")
        if version.feasibility_status != "feasible" or version.quality_status != "ready":
            raise ValueError("Only feasible, quality-ready policies can be confirmed")
        account.current_policy_version_id = version.id
        account.updated_at = datetime.now(UTC)
        await self.session.commit()
        return (await self.version_detail(version.id)) or {}

    async def _persist(self, account: AllocationAccount, constraints: dict[str, Any], catalog: dict[str, Any],
                       result: dict[str, Any], selected: list[dict[str, Any]], tactical_tilts: list[dict[str, Any]]) -> dict[str, Any]:
        methodology = {
            "allocation_method": "constrained_equal_risk_contribution", "covariance": "ledoit_wolf_monthly",
            "expected_returns": False, "minimum_common_months": 120, "forward_fill": False,
            "stress_library": STRESS_LIBRARY, "automatic_reallocation": False,
            "derivatives_are_asset_classes": False,
        }
        data_snapshot = {"formal_ready": catalog.get("formal_ready", False), "series": selected or catalog.get("series") or [],
                         "common_history": result.get("common_history")}
        content = {"constraints": constraints, "methodology": methodology, "data": data_snapshot, "result": result,
                   "tactical_tilts": tactical_tilts}
        content_hash = stable_hash(content)
        existing = (await self.session.execute(select(AllocationPolicyVersion).where(
            AllocationPolicyVersion.account_id == account.id,
            AllocationPolicyVersion.content_hash == content_hash).limit(1))).scalar_one_or_none()
        if existing:
            return (await self.version_detail(existing.id)) or {}
        next_version = int((await self.session.execute(select(func.coalesce(func.max(AllocationPolicyVersion.version), 0)).where(
            AllocationPolicyVersion.account_id == account.id))).scalar_one()) + 1
        quality_status = "ready" if catalog.get("formal_ready") else "unavailable"
        row = AllocationPolicyVersion(account_id=account.id, version=next_version,
            feasibility_status=result.get("status", "unavailable"), quality_status=quality_status,
            constraint_snapshot=constraints, methodology_snapshot=methodology, data_snapshot=data_snapshot,
            risk_summary=result.get("risk_summary") or {}, stress_results=result.get("stress_results") or [],
            infeasible_reasons=result.get("reasons") or [], content_hash=content_hash)
        self.session.add(row)
        await self.session.flush()
        if result.get("status") == "feasible":
            selected_by_sleeve = {item["sleeve_key"]: item for item in selected}
            for sleeve_key, weight in result["weights"].items():
                band = max(0.02, weight * 0.20)
                self.session.add(AllocationPolicySleeve(policy_version_id=row.id, sleeve_key=sleeve_key,
                    label=SLEEVE_LABELS[sleeve_key], target_weight=weight, min_weight=max(0, weight-band),
                    max_weight=min(1, weight+band), amount_cny=weight*float(account.capital),
                    risk_contribution=(result["risk_contributions"].get(sleeve_key) or 0),
                    currency_exposure={"CNY": weight} if sleeve_key in {"cny_cash", "china_equity", "china_bond", "gold"} else {},
                    source_series_id=(selected_by_sleeve.get(sleeve_key) or {}).get("series_id")))
            instruments = [item for item in await self.reader.allocation_instruments(list(result["weights"]))
                           if item.get("instrument_type") in (account.allowed_instruments or [])
                           and self._market_allowed(item.get("market"), account.allowed_markets or [])]
            for item in instruments:
                self.session.add(AllocationPolicyImplementation(policy_version_id=row.id,
                    sleeve_key=item["sleeve_key"], instrument_type=item["instrument_type"],
                    instrument_code=item["code"], instrument_name=item["name"], target_weight=0,
                    amount_cny=0, underlying_key=item["underlying_key"], metadata_json={
                        **(item.get("metadata_json") or {}), "selection_required": True,
                    }))
            await self._persist_tactical_links(row, tactical_tilts)
        await self.session.commit()
        return (await self.version_detail(row.id)) or {}

    async def _persist_tactical_links(self, policy: AllocationPolicyVersion, tilts: list[dict[str, Any]]) -> None:
        now = datetime.now(UTC)
        for tilt in tilts:
            thesis = await self.session.get(ResearchThesis, UUID(str(tilt["thesis_id"])))
            version = await self.session.get(ResearchThesisVersion, UUID(str(tilt["thesis_version_id"])))
            if thesis is None or thesis.user_id != self.user_id or thesis.status != "active" or version is None or version.thesis_id != thesis.id:
                raise ValueError("Tactical tilt requires an owned active thesis and immutable version")
            review_at, expires_at = tilt["review_at"], tilt["expires_at"]
            if review_at <= now or expires_at <= review_at:
                raise ValueError("Tactical tilt review and expiry dates are invalid")
            self.session.add(AllocationPolicyThesisLink(policy_version_id=policy.id, thesis_id=thesis.id,
                thesis_version_id=version.id, sleeve_key=tilt["sleeve_key"], weight_delta=tilt["weight_delta"],
                review_at=review_at, expires_at=expires_at, evidence_snapshot=version.snapshot))

    async def _validate_tactical_tilts(self, tilts: list[dict[str, Any]]) -> None:
        now = datetime.now(UTC)
        for tilt in tilts:
            thesis = await self.session.get(ResearchThesis, UUID(str(tilt["thesis_id"])))
            version = await self.session.get(ResearchThesisVersion, UUID(str(tilt["thesis_version_id"])))
            review_at, expires_at = tilt["review_at"], tilt["expires_at"]
            if thesis is None or thesis.user_id != self.user_id or thesis.status != "active" or version is None or version.thesis_id != thesis.id:
                raise ValueError("Tactical tilt requires an owned active thesis and immutable version")
            if review_at.tzinfo is None or expires_at.tzinfo is None or review_at <= now or expires_at <= review_at:
                raise ValueError("Tactical tilt review and expiry dates are invalid")

    async def _owned_account(self, account_id: UUID, *, lock: bool = False) -> AllocationAccount | None:
        query = select(AllocationAccount).where(AllocationAccount.id == account_id,
                                                 AllocationAccount.user_id == self.user_id)
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    @staticmethod
    def _validate_account(values: dict[str, Any]) -> None:
        capital = float(values.get("capital") or 0)
        reserve = float(values.get("liquidity_reserve") or 0)
        if capital <= 0 or reserve < 0:
            raise ValueError("Capital and liquidity reserve are invalid")
        if str(values.get("base_currency") or "CNY").upper() != "CNY":
            raise ValueError("The first allocation universe is CNY-based")
        if not values.get("allowed_markets") or not values.get("allowed_instruments"):
            raise ValueError("At least one permitted market and implementation instrument are required")
        for item in values.get("future_cash_needs") or []:
            if float(item.get("amount") or 0) <= 0 or not item.get("date"):
                raise ValueError("Each future cash need requires a date and positive amount")

    @staticmethod
    def _market_allowed(market: str | None, allowed: list[str]) -> bool:
        if not market:
            return True
        group = {
            "SSE": "CN", "SZSE": "CN", "CFFEX": "CN", "SHFE": "CN", "DCE": "CN", "CZCE": "CN", "GFEX": "CN",
            "HKEX": "HK", "NYSE": "US", "NASDAQ": "US", "ARCA": "US",
        }.get(market.upper(), market.upper())
        return group in {item.upper() for item in allowed} or "GLOBAL" in {item.upper() for item in allowed}

    @staticmethod
    def _constraint_snapshot(row: AllocationAccount) -> dict[str, Any]:
        return {key: _json(getattr(row, key)) for key in (
            "name", "base_currency", "capital", "horizon_months", "liquidity_reserve", "max_drawdown",
            "max_leverage", "future_cash_needs", "allowed_markets", "allowed_instruments", "hard_restrictions")}

    @staticmethod
    def _account(row: AllocationAccount) -> dict[str, Any]:
        return {"id": str(row.id), "name": row.name, "base_currency": row.base_currency, "capital": float(row.capital),
                "horizon_months": row.horizon_months, "liquidity_reserve": float(row.liquidity_reserve),
                "max_drawdown": float(row.max_drawdown), "max_leverage": float(row.max_leverage),
                "future_cash_needs": row.future_cash_needs, "allowed_markets": row.allowed_markets,
                "allowed_instruments": row.allowed_instruments, "hard_restrictions": row.hard_restrictions,
                "status": row.status, "current_policy_version_id": str(row.current_policy_version_id) if row.current_policy_version_id else None,
                "created_at": row.created_at, "updated_at": row.updated_at}

    @staticmethod
    def _version_summary(row: AllocationPolicyVersion, account: AllocationAccount) -> dict[str, Any]:
        return {"id": str(row.id), "account_id": str(row.account_id), "version": row.version,
                "feasibility_status": row.feasibility_status, "quality_status": row.quality_status,
                "content_hash": row.content_hash, "confirmed": account.current_policy_version_id == row.id,
                "created_at": row.created_at}

    @staticmethod
    def _sleeve(row: AllocationPolicySleeve) -> dict[str, Any]:
        return {"id": str(row.id), "sleeve_key": row.sleeve_key, "label": row.label,
                "target_weight": float(row.target_weight), "min_weight": float(row.min_weight),
                "max_weight": float(row.max_weight), "amount_cny": float(row.amount_cny),
                "risk_contribution": float(row.risk_contribution), "currency_exposure": row.currency_exposure,
                "source_series_id": row.source_series_id}

    @staticmethod
    def _implementation(row: AllocationPolicyImplementation) -> dict[str, Any]:
        return {"id": str(row.id), "sleeve_key": row.sleeve_key, "instrument_type": row.instrument_type,
                "instrument_code": row.instrument_code, "instrument_name": row.instrument_name,
                "target_weight": float(row.target_weight), "amount_cny": float(row.amount_cny),
                "underlying_key": row.underlying_key, "margin_cash": float(row.margin_cash) if row.margin_cash is not None else None,
                "premium_cash": float(row.premium_cash) if row.premium_cash is not None else None,
                "delta_equivalent": float(row.delta_equivalent) if row.delta_equivalent is not None else None,
                "gross_notional": float(row.gross_notional) if row.gross_notional is not None else None,
                "net_notional": float(row.net_notional) if row.net_notional is not None else None,
                "max_loss": float(row.max_loss) if row.max_loss is not None else None,
                "gamma": float(row.gamma) if row.gamma is not None else None, "vega": float(row.vega) if row.vega is not None else None,
                "metadata": row.metadata_json}

    @staticmethod
    def _thesis_link(row: AllocationPolicyThesisLink) -> dict[str, Any]:
        return {"id": str(row.id), "thesis_id": str(row.thesis_id), "thesis_version_id": str(row.thesis_version_id),
                "sleeve_key": row.sleeve_key, "weight_delta": float(row.weight_delta),
                "review_at": row.review_at, "expires_at": row.expires_at, "evidence_snapshot": row.evidence_snapshot}
