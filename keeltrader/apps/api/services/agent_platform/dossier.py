"""Deterministic, citation-first fundamental dossier generation."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from statistics import median
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import os
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
CALCULATION_VERSION = "fundamental-v3"
IMPLEMENTED_DIVIDEND_MARKERS = ("实施", "已实施", "完成")


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
        AgentBackgroundJob.status.in_({"queued", "retry", "running"}),
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
            job_id = item.id
            company_code = str(item.payload["company_code"])
            force = bool(item.payload.get("force"))
            try:
                await refresh_dossier(session, item.user_id, company_code, force=force)
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
                    failed = await session.get(AgentBackgroundJob, job_id, with_for_update=True)
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
                logger.exception("dossier_refresh_failed", job_id=str(job_id), error=str(exc))


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


def _period(row: dict[str, Any]) -> str:
    return str(row.get("end_date") or "").replace("-", "")


def _canonical_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One latest disclosed row per reporting period, preferring consolidated reports."""
    ranked = sorted(rows, key=lambda row: (
        _period(row), str(row.get("ann_date") or ""), str(row.get("f_ann_date") or ""),
        str(row.get("updated_at") or ""), str(row.get("update_flag") or ""),
        1 if str(row.get("report_type") or "1") == "1" else 0,
    ), reverse=True)
    result: dict[str, dict[str, Any]] = {}
    for row in ranked:
        period = _period(row)
        if period and period not in result:
            result[period] = row
    return sorted(result.values(), key=_period, reverse=True)


def _same_period_prior_year(period: str) -> str | None:
    return f"{int(period[:4]) - 1}{period[4:]}" if len(period) == 8 and period[:4].isdigit() else None


def _ttm(rows: list[dict[str, Any]], *fields: str) -> tuple[float | None, dict[str, Any]]:
    canonical = {_period(row): row for row in _canonical_rows(rows)}
    if not canonical:
        return None, {"quality": "missing"}
    latest_period = max(canonical)
    latest = canonical[latest_period]
    latest_value = _num(latest, *fields)
    if latest_period.endswith("1231"):
        return latest_value, {"formula": "latest_fy", "periods": [latest_period]}
    latest_fy_periods = [period for period in canonical if period < latest_period and period.endswith("1231")]
    prior_ytd_period = _same_period_prior_year(latest_period)
    if not latest_fy_periods or prior_ytd_period not in canonical:
        return None, {"quality": "insufficient_periods", "periods": [latest_period, prior_ytd_period]}
    fy_period = max(latest_fy_periods)
    fy_value = _num(canonical[fy_period], *fields)
    prior_ytd_value = _num(canonical[prior_ytd_period], *fields)
    if None in (latest_value, fy_value, prior_ytd_value):
        return None, {"quality": "missing_fields", "periods": [fy_period, latest_period, prior_ytd_period]}
    return fy_value + latest_value - prior_ytd_value, {
        "formula": "latest_fy + latest_ytd - prior_year_same_ytd",
        "periods": [fy_period, latest_period, prior_ytd_period],
    }


def _metric(value: float | None, *, formula: str, table: str, fields: list[str], period: str | None,
            announcement: str | None = None, quality: str = "reported") -> dict[str, Any]:
    return {"value": value, "formula": formula, "table": table, "fields": fields,
            "period": period, "announcement": announcement, "quality": quality if value is not None else "missing"}


def _report_has_content(report: dict[str, Any]) -> bool:
    return bool(report.get("company_match_verified") is True and
                str(report.get("excerpt") or "").strip() and
                (report.get("section_id") or report.get("page_number") is not None))


def _report_evidence_state(
    usable_reports: list[dict[str, Any]],
    company_candidates: list[dict[str, Any]],
) -> tuple[str, str | None]:
    if usable_reports:
        return "sufficient", None
    if not company_candidates:
        return "no_company_report", "知识库中尚未找到与该公司名称或证券代码精确匹配的研报。"
    incomplete = any(
        int(report.get("sections_count") or 0) == 0
        or str(report.get("ingest_status") or "") != "completed"
        for report in company_candidates
    )
    if incomplete:
        return "company_report_processing", "已找到该公司研报，但正文解析、OCR 或章节入库尚未完成，暂不能作为可定位证据。"
    return "company_report_not_locatable", "已找到该公司研报记录，但未检索到同时包含正文摘录与章节/页码定位的证据，需检查实体或检索索引质量。"


def _implemented_dividend_yield(rows: list[dict[str, Any]], close: float | None,
                                as_of: str | None) -> tuple[float | None, list[str]]:
    if close in (None, 0) or not as_of:
        return None, []
    end = datetime.strptime(as_of.replace("-", ""), "%Y%m%d").date()
    start = end - timedelta(days=365)
    total = 0.0
    used: list[str] = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        status = str(row.get("div_proc") or "")
        date_text = str(row.get("pay_date") or row.get("ex_date") or row.get("imp_ann_date") or "").replace("-", "")
        if not any(marker in status for marker in IMPLEMENTED_DIVIDEND_MARKERS) or len(date_text) != 8:
            continue
        paid = datetime.strptime(date_text, "%Y%m%d").date()
        cash = _num(row, "cash_div_tax", "cash_div")
        key = (row.get("end_date"), date_text, cash)
        if start < paid <= end and cash is not None and key not in seen:
            seen.add(key)
            total += cash
            used.append(str(row.get("end_date") or date_text))
    return (total / close * 100 if used else None), used


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
    income = _canonical_rows(raw.get("income", []))
    indicators = _canonical_rows(raw.get("fina_indicator", []))
    cashflow = _canonical_rows(raw.get("cashflow", []))
    balance = _canonical_rows(raw.get("balancesheet", []))
    latest_income = income[0] if income else {}
    latest_period = _period(latest_income) or (_period(indicators[0]) if indicators else "")
    peers = await tushare.industry_peers(
        str(profile.get("industry") or watch.industry or ""), company_code, latest_period or None,
    )
    report_kb = ReportKBService()
    company_identifiers = [company_code, str(profile.get("name") or watch.company_name)]
    reports, company_report_candidates = await asyncio.gather(
        report_kb.search_reports(
            f"{profile.get('name') or watch.company_name} {company_code} 基本面 盈利 风险", top_k=8,
            companies=company_identifiers, granularity="chunk",
        ),
        report_kb.company_report_candidates(company_identifiers),
    )
    fingerprint_payload = {"calculation_version": CALCULATION_VERSION, "financials": raw,
                           "reports": reports, "report_candidates": company_report_candidates,
                           "profile": profile, "peers": peers}
    fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    dossier = (await session.execute(select(AgentCompanyDossier).where(
        AgentCompanyDossier.user_id == user_id, AgentCompanyDossier.company_code == company_code,
    ))).scalar_one_or_none()
    if dossier and dossier.source_fingerprint == fingerprint:
        dossier.stale = False
        dossier.status = "current"
        dossier.last_refreshed_at = datetime.now(UTC)
        return dossier
    if dossier is None:
        dossier = AgentCompanyDossier(user_id=user_id, company_code=company_code,
            company_name=str(profile.get("name") or watch.company_name), industry=profile.get("industry") or watch.industry)
        session.add(dossier)
        await session.flush()

    income_by_period = {_period(row): row for row in income}
    prior_period = _same_period_prior_year(latest_period)
    prior_income = income_by_period.get(prior_period or "", {})
    latest_i = (indicators + [{}])[0]
    latest_cf = (cashflow + [{}])[0]
    latest_bs = (balance + [{}])[0]
    revenue = _num(latest_income, "revenue", "total_revenue")
    prior_revenue = _num(prior_income, "revenue", "total_revenue")
    profit = _num(latest_income, "n_income_attr_p", "n_income")
    prior_profit = _num(prior_income, "n_income_attr_p", "n_income")
    cfo = _num(latest_cf, "n_cashflow_act")
    capex = _num(latest_cf, "c_pay_acq_const_fiolta", "c_pay_acq_const_fiolta")
    announcement = str(latest_income.get("ann_date") or latest_income.get("f_ann_date") or "") or None
    revenue_ttm, revenue_ttm_lineage = _ttm(income, "revenue", "total_revenue")
    profit_ttm, profit_ttm_lineage = _ttm(income, "n_income_attr_p", "n_income")
    cfo_ttm, cfo_ttm_lineage = _ttm(cashflow, "n_cashflow_act")
    fcf_ttm, fcf_ttm_lineage = _ttm(cashflow, "free_cashflow")
    if fcf_ttm is None:
        capex_ttm, _ = _ttm(cashflow, "c_pay_acq_const_fiolta")
        fcf_ttm = None if cfo_ttm is None else cfo_ttm - (capex_ttm or 0)
        fcf_ttm_lineage = {"formula": "ttm_cfo - ttm_capex", "quality": "derived"}
    roe = _num(latest_i, "roe_yearly", "roe_waa", "roe")
    roic = _num(latest_i, "roic_yearly", "roic")
    metrics = {
        "period": latest_period,
        "revenue": revenue, "revenue_growth_pct": _growth(revenue, prior_revenue),
        "net_profit": profit, "net_profit_growth_pct": _growth(profit, prior_profit),
        "revenue_ttm": revenue_ttm, "net_profit_ttm": profit_ttm,
        "gross_margin_pct": _num(latest_i, "grossprofit_margin"),
        "net_margin_pct": _num(latest_i, "netprofit_margin"),
        "roe_pct": roe, "roic_pct": roic,
        "cfo": cfo, "cfo_ttm": cfo_ttm, "cfo_to_profit": _ratio(cfo_ttm, profit_ttm),
        "free_cash_flow": fcf_ttm,
        "debt_to_assets_pct": _num(latest_i, "debt_to_assets"),
        "accounts_receivable": _num(latest_bs, "accounts_receiv"),
        "inventory": _num(latest_bs, "inventories"),
    }
    bars = raw.get("stock_daily", [])
    close = _num((bars + [{}])[0], "close")
    trade_date = str((bars + [{}])[0].get("trade_date") or "") or None
    total_shares = _num(latest_bs, "total_share")
    parent_equity = _num(latest_bs, "total_hldr_eqy_exc_min_int")
    market_cap = close * total_shares if close is not None and total_shares is not None else None
    dividend_yield, dividend_periods = _implemented_dividend_yield(raw.get("dividend", []), close, trade_date)
    metrics["dividend_yield_pct"] = dividend_yield
    metrics["derived_valuation"] = {
        "as_of": trade_date, "close": close, "market_cap": market_cap,
        "pe": _ratio(market_cap, profit_ttm), "pb": _ratio(market_cap, parent_equity),
        "ps": _ratio(market_cap, revenue_ttm),
        "method": "market capitalization divided by synchronized TTM profit/revenue or latest parent equity",
    }
    metric_lineage = {
        "revenue_growth_pct": _metric(metrics["revenue_growth_pct"], formula="current_same_period / prior_year_same_period - 1",
            table="income", fields=["revenue", "total_revenue"], period=latest_period, announcement=announcement),
        "net_profit_growth_pct": _metric(metrics["net_profit_growth_pct"], formula="current_same_period / prior_year_same_period - 1",
            table="income", fields=["n_income_attr_p", "n_income"], period=latest_period, announcement=announcement),
        "revenue_ttm": _metric(revenue_ttm, formula=str(revenue_ttm_lineage.get("formula")), table="income",
            fields=["revenue", "total_revenue"], period=latest_period, quality=str(revenue_ttm_lineage.get("quality", "derived"))),
        "net_profit_ttm": _metric(profit_ttm, formula=str(profit_ttm_lineage.get("formula")), table="income",
            fields=["n_income_attr_p", "n_income"], period=latest_period, quality=str(profit_ttm_lineage.get("quality", "derived"))),
        "cfo_ttm": _metric(cfo_ttm, formula=str(cfo_ttm_lineage.get("formula")), table="cashflow",
            fields=["n_cashflow_act"], period=latest_period, quality=str(cfo_ttm_lineage.get("quality", "derived"))),
        "free_cash_flow": _metric(fcf_ttm, formula=str(fcf_ttm_lineage.get("formula")), table="cashflow",
            fields=["free_cashflow", "n_cashflow_act", "c_pay_acq_const_fiolta"], period=latest_period,
            quality=str(fcf_ttm_lineage.get("quality", "reported"))),
        "pe": _metric(metrics["derived_valuation"]["pe"], formula="market_cap / ttm_parent_net_profit",
            table="stock_daily+balancesheet+income", fields=["close", "total_share", "n_income_attr_p"], period=latest_period),
        "pb": _metric(metrics["derived_valuation"]["pb"], formula="market_cap / latest_parent_equity",
            table="stock_daily+balancesheet", fields=["close", "total_share", "total_hldr_eqy_exc_min_int"], period=latest_period),
        "ps": _metric(metrics["derived_valuation"]["ps"], formula="market_cap / ttm_revenue",
            table="stock_daily+balancesheet+income", fields=["close", "total_share", "revenue"], period=latest_period),
        "dividend_yield_pct": _metric(dividend_yield, formula="implemented_cash_dividend_per_share_t12m / close",
            table="dividend+stock_daily", fields=["cash_div_tax", "cash_div", "div_proc", "pay_date", "close"],
            period=",".join(dividend_periods) or latest_period),
    }
    flags = []
    if metrics["cfo_to_profit"] is not None and metrics["cfo_to_profit"] < 0.8:
        flags.append("经营现金流低于净利润")
    if metrics["debt_to_assets_pct"] is not None and metrics["debt_to_assets_pct"] > 70:
        flags.append("资产负债率高于70%")
    if metrics["revenue_growth_pct"] is not None and metrics["net_profit_growth_pct"] is not None and metrics["revenue_growth_pct"] > 0 > metrics["net_profit_growth_pct"]:
        flags.append("增收不增利")
    peer_metrics = {"period": latest_period}
    for key in ("roe", "grossprofit_margin", "netprofit_margin", "debt_to_assets"):
        values = [_num(row, key) for row in peers]
        values = [value for value in values if value is not None]
        peer_metrics[key] = median(values) if values else None
    usable_reports = [report for report in reports if _report_has_content(report)]
    evidence_status, evidence_shortage = _report_evidence_state(usable_reports, company_report_candidates)
    calculation_errors = [name for name in ("revenue_ttm", "net_profit_ttm", "pe", "pb", "ps")
                          if (metric_lineage.get(name) or {}).get("value") is None]
    snapshot = {
        "company": {"ts_code": company_code, "name": dossier.company_name, "industry": dossier.industry},
        "metrics": metrics, "industry_peer_medians": peer_metrics, "anomaly_flags": flags,
        "metric_lineage": metric_lineage,
        "calculation_version": CALCULATION_VERSION,
        "financial_as_of": latest_period,
        "calculation_errors": calculation_errors,
        "evidence_status": evidence_status,
        "evidence_shortage": evidence_shortage,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    previous = (await session.execute(select(AgentCompanyDossierVersion).where(
        AgentCompanyDossierVersion.dossier_id == dossier.id).order_by(desc(AgentCompanyDossierVersion.version)).limit(1)
    )).scalar_one_or_none()
    version_number = dossier.current_version + 1
    version = AgentCompanyDossierVersion(dossier_id=dossier.id, version=version_number,
        source_fingerprint=fingerprint, snapshot=snapshot, diff=_diff(previous.snapshot if previous else {}, snapshot),
        calculation_version=CALCULATION_VERSION, financial_as_of=latest_period or None,
        quality={"canonical_rows": True, "same_period_yoy": True, "ttm": True,
                 "peer_period_aligned": True, "usable_report_count": len(usable_reports),
                 "company_report_candidate_count": len(company_report_candidates),
                 "rejected_report_count": max(len(reports) - len(usable_reports), 0),
                 "report_evidence_policy": "strict-company-locatable-v1"},
        calculation_errors=calculation_errors)
    session.add(version)
    await session.flush()
    for table, rows in raw.items():
        for row in rows[:2]:
            session.add(AgentCompanyEvidence(dossier_version_id=version.id, source_type="financial",
                citation={"table": table, "ts_code": company_code, "reporting_period": row.get("end_date") or row.get("trade_date"), "fields": row}))
    for report in usable_reports:
        session.add(AgentCompanyEvidence(dossier_version_id=version.id, source_type="report",
            citation={key: report.get(key) for key in ("report_id", "section_id", "page_number", "broker", "report_date", "title", "excerpt")}))
    dossier.current_version = version_number
    dossier.source_fingerprint = fingerprint
    dossier.status = "current"
    dossier.stale = False
    dossier.calculation_version = CALCULATION_VERSION
    dossier.financial_as_of = latest_period or None
    dossier.calculation_errors = calculation_errors
    dossier.last_error = None
    dossier.next_retry_at = None
    dossier.last_refreshed_at = datetime.now(UTC)
    return dossier
