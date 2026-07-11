"""Deterministic, citation-first fundamental dossier generation."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo
from statistics import median
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import os
from datetime import timedelta
from uuid import uuid4

from core.database import async_session
from core.logging import get_logger
from sqlalchemy.dialects.postgresql import insert as pg_insert

from domain.agent_platform.models import (
    AgentBackgroundJob, AgentCompanyDossier, AgentCompanyDossierVersion, AgentCompanyEvidence,
    AgentCompanyWatchlist,
)
from services.agent_platform.report_kb import ReportKBService
from services.agent_platform.tushare import TushareReadService

logger = get_logger(__name__)


async def enqueue_dossier_refresh(session: AsyncSession, user_id, company_code: str, *, force: bool = False) -> None:
    await session.execute(pg_insert(AgentBackgroundJob).values(
        id=uuid4(), user_id=user_id, kind="dossier_refresh",
        entity_key=f"{user_id}:{company_code}", payload={"company_code": company_code, "force": force},
        status="queued", available_at=datetime.now(UTC), attempts=0, max_attempts=3,
    ).on_conflict_do_nothing())


async def _claim_dossier_job(session: AsyncSession, worker_id: str) -> AgentBackgroundJob | None:
    now = datetime.now(UTC)
    item = (await session.execute(select(AgentBackgroundJob).where(
        AgentBackgroundJob.kind == "dossier_refresh",
        AgentBackgroundJob.status.in_({"queued", "retry"}),
        AgentBackgroundJob.available_at <= now,
        (AgentBackgroundJob.lease_expires_at.is_(None) | (AgentBackgroundJob.lease_expires_at < now)),
    ).order_by(AgentBackgroundJob.created_at).with_for_update(skip_locked=True).limit(1))).scalar_one_or_none()
    if item:
        item.status = "running"
        item.attempts += 1
        item.lease_owner = worker_id
        item.lease_expires_at = now + timedelta(minutes=5)
        await session.flush()
    return item


async def dossier_worker_loop() -> None:
    worker_id = f"dossier:{os.uname().nodename}:{os.getpid()}"
    while True:
        async with async_session() as session:
            async with session.begin():
                item = await _claim_dossier_job(session, worker_id)
            if not item:
                await asyncio.sleep(1)
                continue
            try:
                await refresh_dossier(session, item.user_id, item.payload["company_code"],
                                      force=bool(item.payload.get("force")))
                item.status = "completed"
                item.finished_at = datetime.now(UTC)
                item.lease_owner = None
                item.lease_expires_at = None
                await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await session.rollback()
                async with session.begin():
                    failed = await session.get(AgentBackgroundJob, item.id, with_for_update=True)
                    failed.last_error = str(exc)[:2000]
                    failed.lease_owner = None
                    failed.lease_expires_at = None
                    if failed.attempts < failed.max_attempts:
                        failed.status = "retry"
                        failed.available_at = datetime.now(UTC) + timedelta(seconds=2 ** failed.attempts * 15)
                    else:
                        failed.status = "failed"
                        failed.finished_at = datetime.now(UTC)
                    dossier = (await session.execute(select(AgentCompanyDossier).where(
                        AgentCompanyDossier.user_id == failed.user_id,
                        AgentCompanyDossier.company_code == failed.payload["company_code"],
                    ))).scalar_one_or_none()
                    if dossier:
                        dossier.status = "failed"
                        dossier.stale = True
                        dossier.last_error = failed.last_error
                        dossier.next_retry_at = failed.available_at if failed.status == "retry" else None
                logger.exception("dossier_refresh_failed", job_id=str(item.id), error=str(exc))


async def dossier_scheduler_loop() -> None:
    """Queue only enabled watchlist companies once daily after 06:30 Asia/Shanghai."""
    last_date = None
    while True:
        now = datetime.now(ZoneInfo("Asia/Shanghai"))
        if (now.hour, now.minute) >= (6, 30) and last_date != now.date():
            async with async_session() as session:
                rows = (await session.execute(select(AgentCompanyWatchlist).where(
                    AgentCompanyWatchlist.refresh_enabled.is_(True)
                ))).scalars().all()
                for item in rows:
                    await enqueue_dossier_refresh(session, item.user_id, item.company_code)
                await session.commit()
            last_date = now.date()
        await asyncio.sleep(30)


def _num(row: dict[str, Any], *names: str) -> float | None:
    for name in names:
        value = row.get(name)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    return None


def _growth(current: float | None, previous: float | None) -> float | None:
    return None if current is None or previous in (None, 0) else (current / previous - 1) * 100


def _ratio(a: float | None, b: float | None) -> float | None:
    return None if a is None or b in (None, 0) else a / b


def _diff(old: Any, new: Any, path: str = "") -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            changes.update(_diff(old.get(key), new.get(key), f"{path}.{key}".strip(".")))
    elif old != new:
        changes[path] = {"from": old, "to": new}
    return changes


async def refresh_dossier(session: AsyncSession, user_id, company_code: str, *, force: bool = False) -> AgentCompanyDossier:
    watch = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user_id, AgentCompanyWatchlist.company_code == company_code,
        AgentCompanyWatchlist.refresh_enabled.is_(True),
    ))).scalar_one_or_none()
    if not watch:
        raise ValueError("Only companies in 我的自选 can be refreshed")

    tushare = TushareReadService(session)
    raw = await tushare.company_financials(company_code)
    profile = await tushare.stock_profile(company_code) or {}
    peers = await tushare.industry_peers(str(profile.get("industry") or watch.industry or ""), company_code)
    reports = await ReportKBService().search_reports(
        f"{profile.get('name') or watch.company_name} {company_code} 基本面 盈利 风险", top_k=8,
        companies=[company_code, str(profile.get("name") or watch.company_name)], granularity="section",
    )
    fingerprint_payload = {"financials": raw, "reports": reports, "profile": profile, "peers": peers}
    fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    dossier = (await session.execute(select(AgentCompanyDossier).where(
        AgentCompanyDossier.user_id == user_id, AgentCompanyDossier.company_code == company_code,
    ))).scalar_one_or_none()
    if dossier and dossier.source_fingerprint == fingerprint and not force:
        dossier.stale = False
        dossier.status = "current"
        dossier.last_refreshed_at = datetime.now(UTC)
        return dossier
    if dossier is None:
        dossier = AgentCompanyDossier(user_id=user_id, company_code=company_code,
            company_name=str(profile.get("name") or watch.company_name), industry=profile.get("industry") or watch.industry)
        session.add(dossier)
        await session.flush()

    income = raw.get("income", [])
    indicators = raw.get("fina_indicator", [])
    cashflow = raw.get("cashflow", [])
    balance = raw.get("balancesheet", [])
    latest_income, prior_income = (income + [{}, {}])[:2]
    latest_i = (indicators + [{}])[0]
    latest_cf = (cashflow + [{}])[0]
    latest_bs = (balance + [{}])[0]
    revenue = _num(latest_income, "revenue", "total_revenue")
    prior_revenue = _num(prior_income, "revenue", "total_revenue")
    profit = _num(latest_income, "n_income_attr_p", "n_income")
    prior_profit = _num(prior_income, "n_income_attr_p", "n_income")
    cfo = _num(latest_cf, "n_cashflow_act")
    capex = _num(latest_cf, "c_pay_acq_const_fiolta", "c_pay_acq_const_fiolta")
    metrics = {
        "period": latest_income.get("end_date") or latest_i.get("end_date"),
        "revenue": revenue, "revenue_growth_pct": _growth(revenue, prior_revenue),
        "net_profit": profit, "net_profit_growth_pct": _growth(profit, prior_profit),
        "gross_margin_pct": _num(latest_i, "grossprofit_margin"),
        "net_margin_pct": _num(latest_i, "netprofit_margin"),
        "roe_pct": _num(latest_i, "roe", "roe_waa"), "roic_pct": _num(latest_i, "roic"),
        "cfo": cfo, "cfo_to_profit": _ratio(cfo, profit),
        "free_cash_flow": None if cfo is None else cfo - (capex or 0),
        "debt_to_assets_pct": _num(latest_i, "debt_to_assets"),
        "accounts_receivable": _num(latest_bs, "accounts_receiv"),
        "inventory": _num(latest_bs, "inventories"),
        "dividend_yield_pct": _num((raw.get("dividend", []) + [{}])[0], "div_proc", "stk_div"),
    }
    bars = raw.get("stock_daily", [])
    close = _num((bars + [{}])[0], "close")
    eps = _num(latest_i, "eps", "basic_eps")
    bps = _num(latest_i, "bps")
    metrics["derived_valuation"] = {
        "as_of": (bars + [{}])[0].get("trade_date"), "close": close,
        "pe": _ratio(close, eps), "pb": _ratio(close, bps), "ps": None,
        "method": "price divided by latest synchronized per-share field; unavailable values stay null",
    }
    flags = []
    if metrics["cfo_to_profit"] is not None and metrics["cfo_to_profit"] < 0.8:
        flags.append("经营现金流低于净利润")
    if metrics["debt_to_assets_pct"] is not None and metrics["debt_to_assets_pct"] > 70:
        flags.append("资产负债率高于70%")
    if metrics["revenue_growth_pct"] is not None and metrics["net_profit_growth_pct"] is not None and metrics["revenue_growth_pct"] > 0 > metrics["net_profit_growth_pct"]:
        flags.append("增收不增利")
    peer_metrics = {}
    for key in ("roe", "grossprofit_margin", "netprofit_margin", "debt_to_assets"):
        values = [_num(row, key) for row in peers]
        values = [value for value in values if value is not None]
        peer_metrics[key] = median(values) if values else None
    snapshot = {
        "company": {"ts_code": company_code, "name": dossier.company_name, "industry": dossier.industry},
        "metrics": metrics, "industry_peer_medians": peer_metrics, "anomaly_flags": flags,
        "evidence_status": "sufficient" if reports else "shortage",
        "evidence_shortage": None if reports else "未找到与该公司匹配的研报证据；未使用无关近期研报替代。",
        "generated_at": datetime.now(UTC).isoformat(),
    }
    previous = (await session.execute(select(AgentCompanyDossierVersion).where(
        AgentCompanyDossierVersion.dossier_id == dossier.id).order_by(desc(AgentCompanyDossierVersion.version)).limit(1)
    )).scalar_one_or_none()
    version_number = dossier.current_version + 1
    version = AgentCompanyDossierVersion(dossier_id=dossier.id, version=version_number,
        source_fingerprint=fingerprint, snapshot=snapshot, diff=_diff(previous.snapshot if previous else {}, snapshot))
    session.add(version)
    await session.flush()
    for table, rows in raw.items():
        for row in rows[:2]:
            session.add(AgentCompanyEvidence(dossier_version_id=version.id, source_type="financial",
                citation={"table": table, "ts_code": company_code, "reporting_period": row.get("end_date") or row.get("trade_date"), "fields": row}))
    for report in reports:
        session.add(AgentCompanyEvidence(dossier_version_id=version.id, source_type="report",
            citation={key: report.get(key) for key in ("report_id", "section_id", "page_number", "broker", "report_date", "title", "excerpt")}))
    dossier.current_version = version_number
    dossier.source_fingerprint = fingerprint
    dossier.status = "current"
    dossier.stale = False
    dossier.last_refreshed_at = datetime.now(UTC)
    return dossier
