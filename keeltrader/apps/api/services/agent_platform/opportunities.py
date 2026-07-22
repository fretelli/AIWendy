"""Deterministic, snapshot-based unified opportunity center.

Detection is deliberately model-free. It materializes source-dated facts in a
background worker; request handlers only read already-built snapshots.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, desc, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import async_session
from core.logging import get_logger
from domain.agent_platform.models import (
    AgentCompanyDossier,
    AgentCompanyDossierVersion,
    AgentCompanyEvidence,
    AgentCompanyWatchlist,
    AgentHolderEvent,
    AgentHolderWatchlist,
    AgentOpportunityFollow,
    AgentRiskProfile,
    AgentTradePlanDraft,
    MarketOpportunity,
    MarketOpportunityEvidence,
    MarketOpportunityRefreshState,
    MarketOpportunitySnapshot,
)
from services.agent_platform.tushare import TushareReadService
from services.agent_platform.research_loop import record_research_event, stable_event_key

logger = get_logger(__name__)
GLOBAL_DOMAINS = ("macro", "rates", "capital", "futures", "options")
PRIVATE_DOMAINS = ("company", "holder")
ACTIVE_STATES = {"new", "active", "changed", "challenged", "invalidated", "stale"}
OPPORTUNITY_REFRESH_LOCK = 731_904_221


class SourceUnavailable(RuntimeError):
    """A required upstream source is absent; this is not a zero-candidate refresh."""


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


def _stable_hash(value: Any, length: int = 40) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _jsonable(value: Any) -> Any:
    """Convert database-native values into stable JSON values before JSONB writes."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, UUID)):
        return str(value)
    return value


def _evidence(stance: str, fact: str, source: str, source_date: Any, source_ref: Any) -> dict[str, Any]:
    return {"stance": stance, "fact": fact, "source": source,
            "source_date": str(source_date) if source_date is not None else None,
            "source_ref": _jsonable(source_ref or {})}


def _candidate(*, domain: str, playbook: str, subject_type: str, subject_key: str, title: str,
               trigger: str, hypothesis: str, affected_assets: list[str], catalysts: list[str],
               falsifiers: list[str], source_dates: dict[str, str], evidence: list[dict[str, Any]],
               chart_refs: list[dict[str, Any]] | None = None, state: str = "active",
               freshness: dict[str, Any] | None = None, scope: str = "global",
               user_id: UUID | None = None) -> dict[str, Any]:
    as_of = max(source_dates.values(), default=None)
    identity = {"scope": scope, "user_id": str(user_id) if user_id else None, "playbook": playbook,
                "subject_type": subject_type, "subject_key": subject_key}
    return _jsonable({"fingerprint": _stable_hash(identity), "scope": scope, "user_id": user_id,
            "domain": domain, "playbook_key": playbook, "subject_type": subject_type,
            "subject_key": subject_key, "title": title, "state": state, "trigger": trigger,
            "hypothesis": hypothesis, "affected_assets": affected_assets, "catalysts": catalysts,
            "falsifiers": falsifiers, "source_dates": source_dates, "as_of": as_of,
            "freshness": freshness or {}, "evidence": evidence, "chart_refs": chart_refs or []})


async def _macro_candidates(reader: TushareReadService) -> list[dict[str, Any]]:
    definitions = {
        "cpi": ("cn_cpi", "month", "nt_yoy", "居民消费价格", "%"),
        "ppi": ("cn_ppi", "month", "ppi_yoy", "工业生产者价格", "%"),
        "pmi": ("cn_pmi", "month", "pmi010000", "制造业 PMI", ""),
        "gdp": ("cn_gdp", "quarter", "gdp_yoy", "国内生产总值", "%"),
        "money_supply": ("cn_m", "month", "m2_yoy", "M2", "%"),
        "social_financing": ("sf_month", "month", "inc_month", "社会融资增量", "源单位"),
    }
    result = []
    for key, (table, period, field, label, unit) in definitions.items():
        if not await reader.table_exists(table):
            continue
        rows = await reader._execute_mappings(text(
            f'SELECT {period} period,"{field}" value FROM {reader.schema}.{table} '
            f'WHERE "{field}" IS NOT NULL ORDER BY {period} DESC LIMIT 2'
        ), {})
        if not rows:
            continue
        latest, previous = rows[0], rows[1] if len(rows) > 1 else None
        latest_value = _number(latest.get("value"))
        previous_value = _number(previous.get("value")) if previous else None
        direction = "上升" if previous_value is not None and latest_value is not None and latest_value > previous_value else (
            "下降" if previous_value is not None and latest_value is not None and latest_value < previous_value else "持平或缺少可比前值")
        stance = "supporting" if direction == "上升" else "challenging" if direction == "下降" else "supporting"
        fact = f"{latest['period']} {label}源值 {latest_value:g}{unit}" if latest_value is not None else f"{latest['period']} {label}源值缺失"
        if previous_value is not None:
            fact += f"，前值 {previous_value:g}{unit}，方向为{direction}"
        result.append(_candidate(
            domain="macro", playbook=f"macro_release_{key}", subject_type="indicator", subject_key=key,
            title=f"{label}最新发布与前值变化", trigger=f"{label}发布新一期源记录",
            hypothesis=f"{label}最新变化可能改变增长、通胀或流动性叙事，需要结合市场价格确认。",
            affected_assets=["A股/ETF", "利率债券", "人民币资产"],
            catalysts=["下一期宏观数据", "政策回应", "市场价格确认"],
            falsifiers=["源数据修订", "后续数据反向", "资产价格未确认"],
            source_dates={key: str(latest["period"])},
            evidence=[_evidence(stance, fact, f"{reader.schema}.{table}", latest["period"], latest)],
            chart_refs=[{"kind": "macro", "key": key, "field": field, "source": f"{reader.schema}.{table}"}],
            state="active" if previous else "new", freshness={key: {"available": True, "as_of": str(latest["period"])}}
        ))
    return result


async def _liquidity_candidate(reader: TushareReadService) -> dict[str, Any] | None:
    if not await reader.table_exists("repo_daily"):
        return None
    rows = await reader._execute_mappings(text(f"""
        WITH ranked AS (
          SELECT trade_date,repo_maturity,weight,close,amount,
                 ROW_NUMBER() OVER(PARTITION BY repo_maturity ORDER BY trade_date DESC) rn
          FROM {reader.schema}.repo_daily WHERE repo_maturity IN ('DR007','R007')
        ) SELECT * FROM ranked WHERE rn<=2 ORDER BY repo_maturity,rn
    """), {})
    if not rows:
        return None
    by_maturity: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_maturity.setdefault(str(row["repo_maturity"]), []).append(row)
    evidence, changes, dates = [], [], {}
    for maturity, points in by_maturity.items():
        latest, previous = points[0], points[1] if len(points) > 1 else None
        dates[maturity] = str(latest["trade_date"])
        value = _number(latest.get("weight"))
        change_bp = ((value - _number(previous.get("weight"))) * 100
                     if previous and value is not None and _number(previous.get("weight")) is not None else None)
        if change_bp is not None:
            changes.append(change_bp)
        fact = f"{maturity} 加权利率 {value:.4f}%" if value is not None else f"{maturity} 加权利率缺失"
        if change_bp is not None:
            fact += f"，较同期限上一交易记录 {change_bp:+.2f} bp"
        evidence.append(_evidence("challenging" if (change_bp or 0) > 0 else "supporting", fact,
                                  f"{reader.schema}.repo_daily", latest["trade_date"], latest))
    if await reader.table_exists("fut_mapping") and await reader.table_exists("fut_daily"):
        treasury = await reader._execute_mappings(text(f"""WITH latest AS (
            SELECT DISTINCT ON(ts_code) ts_code,trade_date,mapping_ts_code FROM {reader.schema}.fut_mapping
            WHERE split_part(ts_code,'.',1) IN ('T','TF','TS','TL') ORDER BY ts_code,trade_date DESC)
            SELECT l.ts_code,l.trade_date,l.mapping_ts_code,d.close,d.settle,d.oi FROM latest l
            JOIN {reader.schema}.fut_daily d ON d.ts_code=l.mapping_ts_code AND d.trade_date=l.trade_date ORDER BY l.ts_code"""), {})
        if treasury:
            dates["treasury_futures"] = max(str(row["trade_date"]) for row in treasury)
            evidence.append(_evidence("supporting", "国债期货最新主力记录：" + "；".join(
                f"{row['ts_code']}→{row['mapping_ts_code']} 结算 {row.get('settle') or '—'}" for row in treasury),
                f"{reader.schema}.fut_mapping+fut_daily", dates["treasury_futures"], {"contracts": treasury}))
    if await reader.table_exists("stock_daily"):
        breadth = await reader._execute_mappings(text(f"""SELECT trade_date,
            COUNT(*) FILTER(WHERE pct_chg>0)::int advances,COUNT(*) FILTER(WHERE pct_chg<0)::int declines,
            SUM(COALESCE(amount,0))*1000 turnover_cny FROM {reader.schema}.stock_daily
            WHERE trade_date=(SELECT MAX(trade_date) FROM {reader.schema}.stock_daily) GROUP BY trade_date"""), {})
        if breadth:
            item = breadth[0]; dates["a_share"] = str(item["trade_date"])
            stance = "supporting" if int(item.get("advances") or 0) >= int(item.get("declines") or 0) else "challenging"
            evidence.append(_evidence(stance, f"A股上涨 {item['advances']} 家、下跌 {item['declines']} 家，成交额 {float(item.get('turnover_cny') or 0):,.0f} 元",
                                      f"{reader.schema}.stock_daily", item["trade_date"], item))
    direction = "资金价格上行" if changes and sum(changes) > 0 else "资金价格下行或稳定"
    return _candidate(domain="rates", playbook="china_liquidity_transmission", subject_type="market",
        subject_key="china_liquidity", title="中国流动性向债券与风险资产的传导", trigger=direction,
        hypothesis="回购资金价格变化可能先影响国债期货，再传导至权益风险偏好；只展示可核验的确认和冲突。",
        affected_assets=["DR007/R007", "T/TF/TS/TL", "A股/ETF"],
        catalysts=["央行公开市场操作", "税期与跨月", "国债期货和权益价格确认"],
        falsifiers=["回购利率方向反转", "国债期货未确认", "权益资金证据相反"],
        source_dates=dates, evidence=evidence,
        chart_refs=[{"kind": "rates", "key": "repo", "field": "weight", "maturity": "DR007"},
                    {"kind": "rates", "key": "repo", "field": "weight", "maturity": "R007"}],
        state="challenged" if any(item["stance"] == "challenging" for item in evidence) else "active",
        freshness={key: {"available": True, "as_of": value} for key, value in dates.items()})


async def _capital_candidate(reader: TushareReadService) -> dict[str, Any] | None:
    snapshot = await reader.market_capital_snapshot()
    if not snapshot.get("available"):
        return None
    evidence, directions = [], []
    as_of = str(snapshot["as_of"])
    breadth = snapshot.get("breadth") or {}
    advance = int(breadth.get("advances") or 0); decline = int(breadth.get("declines") or 0)
    directions.append(1 if advance >= decline else -1)
    evidence.append(_evidence("supporting" if advance >= decline else "challenging",
        f"A股上涨 {advance} 家、下跌 {decline} 家、平盘 {int(breadth.get('flat') or 0)} 家",
        "tushare.stock_daily", as_of, breadth))
    leverage = snapshot.get("leverage") or {}
    if leverage.get("available"):
        net = float(leverage.get("daily_net_financing_cny") or 0); directions.append(1 if net >= 0 else -1)
        evidence.append(_evidence("supporting" if net >= 0 else "challenging", f"融资当日净额 {net:+,.0f} 元",
                                  f"tushare.{leverage.get('source_table') or 'margin'}", leverage.get("as_of"), leverage))
    etf = snapshot.get("etf_flows") or {}
    if etf.get("available"):
        flow = float(etf.get("estimated_net_flow_cny") or 0); directions.append(1 if flow >= 0 else -1)
        evidence.append(_evidence("supporting" if flow >= 0 else "challenging", f"ETF 份额×净值估算申赎 {flow:+,.0f} 元",
                                  "tushare.fund_share+fund_nav", etf.get("as_of"), etf))
    proxy = snapshot.get("flow_proxy") or {}
    if proxy.get("available"):
        net = float((proxy.get("values") or {}).get("net_amount") or 0) * 10000; directions.append(1 if net >= 0 else -1)
        evidence.append(_evidence("supporting" if net >= 0 else "challenging", f"供应商代理净额 {net:+,.0f} 元；不是逐笔字面净流入",
                                  "tushare.moneyflow_mkt_dc", proxy.get("as_of"), proxy))
    aligned = abs(sum(directions)) >= 2
    trigger = "多个独立资金证据方向一致" if aligned else "资金证据方向分化"
    return _candidate(domain="capital", playbook="a_share_capital_participation", subject_type="market",
        subject_key="a_share", title="A股参与度、杠杆与 ETF 份额变化", trigger=trigger,
        hypothesis="市场广度、融资活动、ETF 申赎和供应商代理资金可共同验证风险参与状态，但不合成为分数。",
        affected_assets=["A股", "ETF"], catalysts=["下一交易日资金数据", "成交活跃度变化", "ETF 份额变化"],
        falsifiers=["独立来源方向继续分化", "来源滞后", "供应商代理口径与可验证数据冲突"],
        source_dates={key: str(value.get("as_of")) for key, value in snapshot.get("sources", {}).items() if value.get("as_of")},
        evidence=evidence, chart_refs=[{"kind": "capital", "key": "all_raw_history"}],
        state="active" if aligned else "challenged", freshness=snapshot.get("sources") or {})


async def _futures_candidates(reader: TushareReadService) -> list[dict[str, Any]]:
    if not all([await reader.table_exists("fut_mapping"), await reader.table_exists("fut_daily")]):
        return []
    rows = await reader._execute_mappings(text(f"""WITH ranked AS (
        SELECT m.ts_code product_code,m.trade_date,m.mapping_ts_code,d.close,d.settle,d.oi,d.oi_chg,
               ROW_NUMBER() OVER(PARTITION BY m.ts_code ORDER BY m.trade_date DESC) rn
        FROM {reader.schema}.fut_mapping m JOIN {reader.schema}.fut_daily d
          ON d.ts_code=m.mapping_ts_code AND d.trade_date=m.trade_date)
        SELECT * FROM ranked WHERE rn<=2 ORDER BY product_code,rn"""), {})
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["product_code"]), []).append(row)
    result = []
    for code, points in grouped.items():
        latest, previous = points[0], points[1] if len(points) > 1 else None
        if not previous:
            continue
        close = _number(latest.get("close")); prior = _number(previous.get("close")); oi = _number(latest.get("oi")); prior_oi = _number(previous.get("oi"))
        price_direction = "上涨" if close is not None and prior is not None and close > prior else "下跌" if close is not None and prior is not None and close < prior else "持平"
        oi_direction = "增加" if oi is not None and prior_oi is not None and oi > prior_oi else "减少" if oi is not None and prior_oi is not None and oi < prior_oi else "持平"
        rolled = latest.get("mapping_ts_code") != previous.get("mapping_ts_code")
        trigger = f"主力合约由 {previous['mapping_ts_code']} 切换至 {latest['mapping_ts_code']}" if rolled else f"主力价格{price_direction}、持仓{oi_direction}"
        result.append(_candidate(domain="futures", playbook="futures_price_open_interest", subject_type="contract",
            subject_key=code, title=f"{code} 主力合约价格与持仓状态", trigger=trigger,
            hypothesis="主力合约价格与持仓方向或换月变化可形成结构观察，但不替代真实现货与基差。",
            affected_assets=[code, str(latest["mapping_ts_code"])], catalysts=["下一交易日结算", "主力切换", "现货或底层确认"],
            falsifiers=["价格方向反转", "持仓方向反转", "底层关系不可核验"],
            source_dates={"futures": str(latest["trade_date"])},
            evidence=[_evidence("supporting", trigger, f"{reader.schema}.fut_mapping+fut_daily", latest["trade_date"], latest),
                      _evidence("supporting", f"前一记录 {previous['trade_date']}：{previous['mapping_ts_code']} 收盘 {previous.get('close')}、持仓 {previous.get('oi')}",
                                f"{reader.schema}.fut_mapping+fut_daily", previous["trade_date"], previous)],
            chart_refs=[{"kind": "futures", "code": code}], state="changed" if rolled else "active",
            freshness={"futures": {"available": True, "as_of": str(latest["trade_date"])}}))
    return result


async def _options_candidates(reader: TushareReadService) -> list[dict[str, Any]]:
    if not all([await reader.table_exists("option_analytics_daily"), await reader.table_exists("opt_basic")]):
        return []
    rows = await reader._execute_mappings(text(f"""WITH dates AS (
        SELECT trade_date,DENSE_RANK() OVER(ORDER BY trade_date DESC) rn
        FROM {reader.schema}.option_analytics_daily GROUP BY trade_date), scoped AS (
        SELECT a.*,b.call_put,b.maturity_date FROM {reader.schema}.option_analytics_daily a
        JOIN dates d ON d.trade_date=a.trade_date AND d.rn<=2
        JOIN {reader.schema}.opt_basic b ON b.ts_code=a.ts_code
        WHERE a.convergence_status='converged'), nearest AS (
        SELECT *,MIN(maturity_date) OVER(PARTITION BY opt_code,trade_date) nearest_maturity FROM scoped)
        SELECT opt_code,trade_date,nearest_maturity,
          AVG(implied_volatility) FILTER(WHERE maturity_date=nearest_maturity AND ABS(delta) BETWEEN .40 AND .60) atm_iv,
          AVG(implied_volatility) FILTER(WHERE maturity_date=nearest_maturity AND call_put='C' AND delta BETWEEN .20 AND .35) call_wing_iv,
          AVG(implied_volatility) FILTER(WHERE maturity_date=nearest_maturity AND call_put='P' AND delta BETWEEN -.35 AND -.20) put_wing_iv,
          SUM(gross_oi_gamma) FILTER(WHERE maturity_date=nearest_maturity) gross_oi_gamma,
          COUNT(*) FILTER(WHERE maturity_date=nearest_maturity)::int contracts
        FROM nearest GROUP BY opt_code,trade_date,nearest_maturity ORDER BY opt_code,trade_date DESC"""), {})
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["opt_code"]), []).append(row)
    result = []
    for code, points in grouped.items():
        latest, previous = points[0], points[1] if len(points) > 1 else None
        if not previous:
            continue
        atm = _number(latest.get("atm_iv")); prior_atm = _number(previous.get("atm_iv"))
        put = _number(latest.get("put_wing_iv")); call = _number(latest.get("call_wing_iv"))
        prior_put = _number(previous.get("put_wing_iv")); prior_call = _number(previous.get("call_wing_iv"))
        skew = put - call if put is not None and call is not None else None
        prior_skew = prior_put - prior_call if prior_put is not None and prior_call is not None else None
        # Convergence is only a quality gate. A count of converged contracts is
        # never itself an opportunity and missing comparable values stay absent.
        if (atm is None or prior_atm is None) and (skew is None or prior_skew is None):
            continue
        if atm == prior_atm and skew == prior_skew:
            continue
        iv_direction = "上升" if atm is not None and prior_atm is not None and atm > prior_atm else "下降" if atm is not None and prior_atm is not None and atm < prior_atm else "持平"
        skew_changed = skew is not None and prior_skew is not None and ((skew > 0) != (prior_skew > 0))
        trigger = f"近月 ATM IV {iv_direction}" + ("，看跌/看涨翼偏斜方向改变" if skew_changed else "")
        latest_date = str(latest["trade_date"])
        result.append(_candidate(domain="options", playbook="option_surface_structure", subject_type="option_series",
            subject_key=code, title=f"{code} 近月 IV 与偏斜结构变化", trigger=trigger,
            hypothesis="同一底层和近月到期的 IV 与偏斜变化可形成波动率结构观察；Gross OI 敏感度不代表做市商净头寸。",
            affected_assets=[code], catalysts=["底层价格变化", "到期临近", "IV 与偏斜继续变化"],
            falsifiers=["底层未解析", "模型不收敛", "下一记录结构反转"], source_dates={"options": latest_date},
            evidence=[_evidence("supporting", f"近月 {latest.get('nearest_maturity')} ATM IV {atm if atm is not None else '—'}，前值 {prior_atm if prior_atm is not None else '—'}",
                                f"{reader.schema}.option_analytics_daily", latest_date, latest),
                      _evidence("challenging" if skew_changed else "supporting", f"看跌翼减看涨翼 IV：{skew if skew is not None else '—'}；前值 {prior_skew if prior_skew is not None else '—'}",
                                f"{reader.schema}.option_analytics_daily", latest_date, {"skew": skew, "previous_skew": prior_skew}),
                      _evidence("challenging", "Gross OI-weighted sensitivity 不是做市商净 Gamma，不据此推断净持仓。",
                                f"{reader.schema}.option_analytics_daily", latest_date, {})],
            chart_refs=[{"kind": "options", "code": code}], state="changed" if skew_changed else "active",
            freshness={"options": {"available": True, "as_of": latest_date}}))
    return result


async def _private_candidates(session: AsyncSession) -> dict[UUID, list[dict[str, Any]]]:
    result: dict[UUID, list[dict[str, Any]]] = {}
    watches = (await session.execute(select(AgentCompanyWatchlist))).scalars().all()
    for watch in watches:
        dossier = (await session.execute(select(AgentCompanyDossier).where(
            AgentCompanyDossier.user_id == watch.user_id,
            AgentCompanyDossier.company_code == watch.company_code))).scalar_one_or_none()
        if not dossier:
            continue
        version = (await session.execute(select(AgentCompanyDossierVersion).where(
            AgentCompanyDossierVersion.dossier_id == dossier.id).order_by(desc(AgentCompanyDossierVersion.version)).limit(1))).scalar_one_or_none()
        if not version:
            continue
        snapshot = version.snapshot or {}; quality = version.quality or {}
        evidence = [_evidence("supporting", f"公司档案已更新至版本 {version.version}，财务口径期 {version.financial_as_of or '不可用'}",
                              "keeltrader.company_dossier", version.financial_as_of, {"version": version.version, "quality": quality})]
        citations = (await session.execute(select(AgentCompanyEvidence).where(
            AgentCompanyEvidence.dossier_version_id == version.id,
            AgentCompanyEvidence.source_type == "report"))).scalars().all()
        for citation_row in citations:
            citation = citation_row.citation or {}
            excerpt = str(citation.get("excerpt") or "").strip()
            location = citation.get("page_number") or citation.get("section_id")
            if excerpt and location:
                evidence.append(_evidence(
                    "supporting", f"研报正文摘录：{excerpt}", "report-kb verified company evidence",
                    citation.get("report_date"), citation,
                ))
            else:
                evidence.append(_evidence(
                    "challenging", "研报仅有标题或缺少正文定位，不计为充分公司证据。",
                    "report-kb verified company evidence", citation.get("report_date"), citation,
                ))
        report_state = snapshot.get("evidence_status") or snapshot.get("report_evidence_state")
        if report_state:
            evidence.append(_evidence("supporting" if report_state == "available" else "challenging",
                                      f"公司研报正文证据状态：{report_state}", "report-kb verified company evidence",
                                      version.financial_as_of, {"state": report_state}))
        result.setdefault(watch.user_id, []).append(_candidate(domain="company", playbook="watched_company_dossier_change",
            subject_type="company", subject_key=watch.company_code, title=f"{watch.company_name} 公司证据档案更新",
            trigger=f"自选公司档案版本更新至 {version.version}",
            hypothesis="财务披露与正文可定位研报证据发生变化，需要重新核对原有公司判断和证伪条件。",
            affected_assets=[watch.company_code], catalysts=["下一次财务披露", "新公司研报正文证据", "股东披露"],
            falsifiers=["研报只有标题命中而无正文定位", "财务数据被重述", "证据与公司不匹配"],
            source_dates={"company_dossier": str(version.financial_as_of or version.created_at.date())}, evidence=evidence,
            chart_refs=[{"kind": "company", "code": watch.company_code}], scope="private", user_id=watch.user_id,
            freshness={"company_dossier": {"available": True, "as_of": str(version.financial_as_of or version.created_at.date())}}))
    events = (await session.execute(select(AgentHolderEvent).join(AgentHolderWatchlist,
        AgentHolderWatchlist.id == AgentHolderEvent.watch_id).where(AgentHolderWatchlist.enabled.is_(True))
        .order_by(desc(AgentHolderEvent.detected_at)))).scalars().all()
    latest_events: dict[tuple[UUID, UUID, str], AgentHolderEvent] = {}
    for event in events:
        latest_events.setdefault((event.user_id, event.watch_id, event.ts_code), event)
    for (user_id, watch_id, code), event in latest_events.items():
        stance = "challenging" if event.event_type in {"decrease", "exit"} else "supporting"
        result.setdefault(user_id, []).append(_candidate(domain="holder", playbook="watched_holder_disclosure",
            subject_type="holder", subject_key=f"{watch_id}:{code}",
            title=f"{event.holder_name} · {event.company_name or code} 股东披露变化",
            trigger=f"最新披露事件：{event.event_type}",
            hypothesis="关注股东在十大流通股东披露中的变化可能构成公司研究催化，但披露期不等于实际交易日。",
            affected_assets=[code], catalysts=["下一报告期股东披露", "公司公告", "价格区间核对"],
            falsifiers=["后续披露反转", "名称匹配不精确", "披露变化由股本调整导致"],
            source_dates={"holder": str(event.end_date)},
            evidence=[_evidence(stance, f"{event.end_date} {event.event_type}；公告日 {event.ann_date or '不可用'}",
                                "tushare.top10_floatholders", event.end_date, event.values)],
            chart_refs=[{"kind": "holder", "watch_id": str(watch_id), "code": code}],
            state="challenged" if stance == "challenging" else "active", scope="private", user_id=user_id,
            freshness={"holder": {"available": True, "as_of": str(event.end_date)}}))
    return result


async def _domain_candidates(domain: str, reader: TushareReadService) -> list[dict[str, Any]]:
    required = {
        "macro": ("cn_cpi", "cn_ppi", "cn_pmi", "cn_gdp", "cn_m", "sf_month"),
        "rates": ("repo_daily",),
        "futures": ("fut_mapping", "fut_daily"),
        "options": ("option_analytics_daily", "opt_basic"),
    }.get(domain, ())
    missing = [table for table in required if not await reader.table_exists(table)]
    if missing:
        raise SourceUnavailable(f"required source unavailable: {', '.join(missing)}")
    if domain == "macro": return await _macro_candidates(reader)
    if domain == "rates":
        item = await _liquidity_candidate(reader); return [item] if item else []
    if domain == "capital":
        item = await _capital_candidate(reader)
        if item is None: raise SourceUnavailable("market capital snapshot unavailable")
        return [item]
    if domain == "futures": return await _futures_candidates(reader)
    if domain == "options": return await _options_candidates(reader)
    return []


async def _materialize_domain(session: AsyncSession, domain: str, candidates: list[dict[str, Any]],
                              *, scope: str, user_id: UUID | None = None) -> int:
    now = datetime.now(UTC); seen: set[UUID] = set()
    for card in candidates:
        row = (await session.execute(select(MarketOpportunity).where(
            MarketOpportunity.fingerprint == card["fingerprint"]))).scalar_one_or_none()
        created = row is None
        if created:
            row = MarketOpportunity(fingerprint=card["fingerprint"], scope=scope, user_id=user_id,
                domain=domain, subject_type=card["subject_type"], subject_key=card["subject_key"],
                playbook_key=card["playbook_key"], title=card["title"], lifecycle_state="new", state="new",
                trigger=card["trigger"], hypothesis=card["hypothesis"], affected_assets=card["affected_assets"],
                catalysts=card["catalysts"], falsifiers=card["falsifiers"], source_dates=card["source_dates"],
                as_of=card["as_of"], freshness=card["freshness"], first_seen_at=now, last_seen_at=now)
            session.add(row); await session.flush()
        snapshot_data = {key: card[key] for key in ("state", "as_of", "trigger", "hypothesis", "affected_assets",
            "catalysts", "falsifiers", "source_dates", "freshness", "evidence", "chart_refs")}
        snapshot_fingerprint = _stable_hash(snapshot_data, 64)
        latest = (await session.execute(select(MarketOpportunitySnapshot).where(
            MarketOpportunitySnapshot.opportunity_id == row.id).order_by(
                desc(MarketOpportunitySnapshot.created_at), desc(MarketOpportunitySnapshot.id)).limit(1))).scalar_one_or_none()
        existing_snapshot = (await session.execute(select(MarketOpportunitySnapshot).where(
            MarketOpportunitySnapshot.opportunity_id == row.id,
            MarketOpportunitySnapshot.snapshot_fingerprint == snapshot_fingerprint).limit(1))).scalar_one_or_none()
        changed = latest is None or latest.snapshot_fingerprint != snapshot_fingerprint
        state = "new" if created else card["state"] if card["state"] in {"challenged", "invalidated", "stale"} else "changed" if changed else "active"
        row.scope, row.user_id, row.domain = scope, user_id, domain
        row.subject_type, row.subject_key = card["subject_type"], card["subject_key"]
        row.title, row.state, row.lifecycle_state = card["title"], state, state
        row.trigger, row.hypothesis = card["trigger"], card["hypothesis"]
        row.affected_assets, row.catalysts, row.falsifiers = card["affected_assets"], card["catalysts"], card["falsifiers"]
        row.source_dates, row.as_of, row.freshness = card["source_dates"], card["as_of"], card["freshness"]
        row.last_seen_at, row.consecutive_misses, row.closed_at = now, 0, None
        if changed:
            snapshot = existing_snapshot
            if snapshot is None:
                snapshot = MarketOpportunitySnapshot(opportunity_id=row.id, snapshot_fingerprint=snapshot_fingerprint,
                    state=state, as_of=card["as_of"], trigger=card["trigger"], hypothesis=card["hypothesis"],
                    affected_assets=card["affected_assets"], catalysts=card["catalysts"], falsifiers=card["falsifiers"],
                    source_dates=card["source_dates"], freshness=card["freshness"], evidence=card["evidence"],
                    chart_refs=card["chart_refs"])
                session.add(snapshot)
                await session.flush()
            row.latest_snapshot_id = snapshot.id
            if latest is not None:
                if scope == "private" and user_id is not None:
                    recipients = [user_id]
                else:
                    recipients = list((await session.execute(select(AgentOpportunityFollow.user_id).where(
                        AgentOpportunityFollow.opportunity_id == row.id,
                        AgentOpportunityFollow.state != "paused",
                    ))).scalars().all())
                before = {key: _jsonable(getattr(latest, key)) for key in (
                    "state", "as_of", "trigger", "hypothesis", "affected_assets", "catalysts",
                    "falsifiers", "source_dates", "freshness", "evidence", "chart_refs")}
                for recipient in recipients:
                    await record_research_event(
                        session, user_id=recipient,
                        event_key=stable_event_key("opportunity", row.id, snapshot.snapshot_fingerprint),
                        category="opportunity", event_type="opportunity_changed",
                        title=f"机会变化 · {row.title}",
                        summary="底层源数据形成了新的不可变机会快照，请复核触发事实、反例与证伪条件。",
                        resource_type="opportunity", resource_id=str(row.id), source_date=card["as_of"],
                        before_state=before, after_state=snapshot_data,
                        metadata={"snapshot_id": str(snapshot.id), "domain": domain, "scope": scope},
                    )
            # Legacy evidence rows are retained for historical compatibility.
            # All new evidence lives in immutable snapshots and is never deleted.
        seen.add(row.id)
    visible = [MarketOpportunity.scope == scope, MarketOpportunity.domain == domain]
    visible.append(MarketOpportunity.user_id == user_id if user_id else MarketOpportunity.user_id.is_(None))
    previous = (await session.execute(select(MarketOpportunity).where(*visible,
        MarketOpportunity.state.in_(ACTIVE_STATES)))).scalars().all()
    for row in previous:
        if row.id not in seen:
            row.consecutive_misses += 1
            if row.consecutive_misses >= 2:
                row.state = row.lifecycle_state = "closed"; row.closed_at = now
    return len(candidates)


async def _refresh_opportunities_unlocked() -> dict[str, int]:
    totals: dict[str, int] = {}
    for domain in GLOBAL_DOMAINS:
        started = time.perf_counter(); now = datetime.now(UTC)
        async with async_session() as session:
            state = await session.get(MarketOpportunityRefreshState, domain)
            if state is None:
                state = MarketOpportunityRefreshState(domain=domain); session.add(state)
            state.status, state.last_started_at = "running", now; await session.commit()
            try:
                candidates = await _domain_candidates(domain, TushareReadService(session))
                total = await _materialize_domain(session, domain, candidates, scope="global")
                state = await session.get(MarketOpportunityRefreshState, domain)
                state.status, state.last_succeeded_at, state.last_error = "ok", datetime.now(UTC), None
                state.candidates_seen = total; state.duration_ms = int((time.perf_counter() - started) * 1000)
                state.source_watermark = {card["subject_key"]: card["source_dates"] for card in candidates}
                await session.commit(); totals[domain] = total
            except SourceUnavailable as exc:
                await session.rollback(); state = await session.get(MarketOpportunityRefreshState, domain)
                if state is None: state = MarketOpportunityRefreshState(domain=domain); session.add(state)
                state.status, state.last_error = "unavailable", str(exc)[:2000]
                state.duration_ms = int((time.perf_counter() - started) * 1000); await session.commit()
                totals[domain] = 0
            except Exception as exc:
                await session.rollback(); state = await session.get(MarketOpportunityRefreshState, domain)
                if state is None: state = MarketOpportunityRefreshState(domain=domain); session.add(state)
                state.status, state.last_error = "failed", str(exc)[:2000]
                state.duration_ms = int((time.perf_counter() - started) * 1000); await session.commit()
                logger.exception("opportunity_domain_refresh_failed", domain=domain, error=str(exc))
    private_started = time.perf_counter()
    try:
        async with async_session() as session:
            for domain in PRIVATE_DOMAINS:
                state = await session.get(MarketOpportunityRefreshState, domain)
                if state is None: state = MarketOpportunityRefreshState(domain=domain); session.add(state)
                state.status, state.last_started_at = "running", datetime.now(UTC)
            await session.commit()
            private = await _private_candidates(session)
            user_ids = set(private)
            user_ids.update((await session.execute(select(AgentCompanyWatchlist.user_id).distinct())).scalars().all())
            user_ids.update((await session.execute(select(AgentHolderWatchlist.user_id).distinct())).scalars().all())
            user_ids.update((await session.execute(select(MarketOpportunity.user_id).where(
                MarketOpportunity.scope == "private", MarketOpportunity.user_id.is_not(None)).distinct())).scalars().all())
            domain_totals = {domain: 0 for domain in PRIVATE_DOMAINS}
            domain_watermarks: dict[str, dict[str, Any]] = {domain: {} for domain in PRIVATE_DOMAINS}
            for user_id in user_ids:
                candidates = private.get(user_id, [])
                for domain in PRIVATE_DOMAINS:
                    scoped = [card for card in candidates if card["domain"] == domain]
                    count = await _materialize_domain(session, domain, scoped, scope="private", user_id=user_id)
                    totals[f"{domain}:{user_id}"] = count; domain_totals[domain] += count
                    domain_watermarks[domain][str(user_id)] = {card["subject_key"]: card["source_dates"] for card in scoped}
            for domain in PRIVATE_DOMAINS:
                state = await session.get(MarketOpportunityRefreshState, domain)
                state.status, state.last_succeeded_at, state.last_error = "ok", datetime.now(UTC), None
                state.candidates_seen, state.source_watermark = domain_totals[domain], domain_watermarks[domain]
                state.duration_ms = int((time.perf_counter() - private_started) * 1000)
            await session.commit()
    except Exception as exc:
        async with async_session() as session:
            for domain in PRIVATE_DOMAINS:
                state = await session.get(MarketOpportunityRefreshState, domain)
                if state is None: state = MarketOpportunityRefreshState(domain=domain); session.add(state)
                state.status, state.last_error = "failed", str(exc)[:2000]
                state.duration_ms = int((time.perf_counter() - private_started) * 1000)
            await session.commit()
        raise
    return totals


async def _keep_advisory_lock_connection_alive(lock_session: AsyncSession,
                                                stop: asyncio.Event) -> None:
    """Prevent PgBouncer or PostgreSQL from retiring an idle lock connection."""
    interval = max(5, int(os.environ.get("OPPORTUNITY_LOCK_KEEPALIVE_SECONDS", "30")))
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            await lock_session.execute(text("SELECT 1"))


async def refresh_opportunities_once() -> dict[str, int]:
    """Run one refresh under a PostgreSQL advisory lock across worker replicas."""
    async with async_session() as lock_session:
        acquired = bool((await lock_session.execute(text(
            "SELECT pg_try_advisory_lock(:lock_key)"
        ), {"lock_key": OPPORTUNITY_REFRESH_LOCK})).scalar_one())
        if not acquired:
            logger.info("opportunity_refresh_skipped", reason="advisory_lock_busy")
            return {}
        stop_keepalive = asyncio.Event()
        keepalive = asyncio.create_task(
            _keep_advisory_lock_connection_alive(lock_session, stop_keepalive),
            name="opportunity-advisory-lock-keepalive",
        )
        try:
            return await _refresh_opportunities_unlocked()
        finally:
            stop_keepalive.set()
            lock_connection_healthy = True
            try:
                await keepalive
            except Exception as exc:
                lock_connection_healthy = False
                logger.error("opportunity_advisory_lock_keepalive_failed", error=str(exc))
            if lock_connection_healthy:
                try:
                    await lock_session.execute(text("SELECT pg_advisory_unlock(:lock_key)"),
                                               {"lock_key": OPPORTUNITY_REFRESH_LOCK})
                except Exception as exc:
                    # A closed PostgreSQL session releases session-level advisory locks
                    # automatically. Do not turn a completed materialization into a false
                    # refresh failure solely because the explicit unlock raced disconnect.
                    logger.warning("opportunity_advisory_unlock_skipped", error=str(exc))


async def opportunity_worker_loop() -> None:
    """Materialize global and private opportunities outside request latency."""
    while True:
        try:
            totals = await refresh_opportunities_once()
            logger.info("opportunity_refresh_complete", totals=totals)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("opportunity_refresh_loop_failed", error=str(exc))
        await asyncio.sleep(int(os.environ.get("OPPORTUNITY_REFRESH_SECONDS", "300")))


class OpportunityService:
    """Read-only feed and user actions over materialized opportunity snapshots."""

    def __init__(self, session: AsyncSession, reader: TushareReadService, user_id: UUID):
        self.session, self.reader, self.user_id = session, reader, user_id

    async def risk_profile(self) -> AgentRiskProfile:
        profile = await self.session.get(AgentRiskProfile, self.user_id)
        if profile is None:
            profile = AgentRiskProfile(user_id=self.user_id); self.session.add(profile)
            await self.session.commit(); await self.session.refresh(profile)
        return profile

    async def update_risk_profile(self, values: dict[str, Any]) -> AgentRiskProfile:
        profile = await self.risk_profile()
        for key in ("account_equity", "currency", "risk_per_trade", "aggregate_open_risk",
                    "single_instrument_notional", "derivative_premium_risk", "max_leverage"):
            if key in values and values[key] is not None: setattr(profile, key, values[key])
        profile.sizing_method = "fixed_risk"; profile.updated_at = datetime.now(UTC)
        await self.session.commit(); await self.session.refresh(profile); return profile

    def _visibility(self):
        return or_(MarketOpportunity.scope == "global", MarketOpportunity.user_id == self.user_id)

    async def list(self, *, scope: str = "all", domain: str | None = None, state: str | None = None,
                   followed: bool = False, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        filters = [self._visibility()]
        if scope == "global": filters.append(MarketOpportunity.scope == "global")
        elif scope == "private": filters.append(MarketOpportunity.user_id == self.user_id)
        if domain: filters.append(MarketOpportunity.domain == domain)
        if state: filters.append(MarketOpportunity.state == state)
        followed_ids = set((await self.session.execute(select(AgentOpportunityFollow.opportunity_id).where(
            AgentOpportunityFollow.user_id == self.user_id))).scalars().all())
        if followed: filters.append(MarketOpportunity.id.in_(followed_ids or {UUID(int=0)}))
        rows = (await self.session.execute(select(MarketOpportunity).where(*filters).order_by(
            MarketOpportunity.domain, MarketOpportunity.state, desc(MarketOpportunity.as_of),
            MarketOpportunity.subject_key).limit(limit).offset(offset))).scalars().all()
        visible_rows = (await self.session.execute(select(MarketOpportunity).where(self._visibility()))).scalars().all()
        groups: dict[str, dict[str, int]] = {}
        for row in visible_rows:
            groups.setdefault(row.domain, {})[row.state] = groups.setdefault(row.domain, {}).get(row.state, 0) + 1
        refresh = (await self.session.execute(select(MarketOpportunityRefreshState))).scalars().all()
        return {"items": [self._card(row, row.id in followed_ids) for row in rows], "groups": groups,
                "source_status": {row.domain: {"status": row.status, "last_succeeded_at": row.last_succeeded_at,
                    "last_error": row.last_error, "duration_ms": row.duration_ms} for row in refresh},
                "ordering": "domain_state_source_date", "scoring": False, "limit": limit, "offset": offset}

    async def detail(self, opportunity_id: UUID) -> dict[str, Any] | None:
        row = (await self.session.execute(select(MarketOpportunity).where(
            MarketOpportunity.id == opportunity_id, self._visibility()))).scalar_one_or_none()
        if row is None: return None
        followed = await self.session.get(AgentOpportunityFollow, {"user_id": self.user_id, "opportunity_id": row.id})
        snapshots = (await self.session.execute(select(MarketOpportunitySnapshot).where(
            MarketOpportunitySnapshot.opportunity_id == row.id).order_by(desc(MarketOpportunitySnapshot.created_at)).limit(50))).scalars().all()
        result = self._card(row, followed is not None)
        result["follow"] = {"state": followed.state, "notes": followed.notes} if followed else None
        result["snapshots"] = [self._snapshot(item) for item in snapshots]
        if snapshots:
            current = snapshots[0]; result["evidence"] = current.evidence; result["chart_refs"] = current.chart_refs
        else:
            evidence = (await self.session.execute(select(MarketOpportunityEvidence).where(
                MarketOpportunityEvidence.opportunity_id == row.id).order_by(MarketOpportunityEvidence.created_at))).scalars().all()
            result["evidence"] = [{"stance": e.stance, "fact": e.fact, "source": e.source,
                "source_date": e.source_date, "source_ref": e.source_ref} for e in evidence]
            result["chart_refs"] = []
        return result

    async def follow(self, opportunity_id: UUID, *, state: str = "following", notes: str | None = None) -> dict[str, Any]:
        row = (await self.session.execute(select(MarketOpportunity.id).where(
            MarketOpportunity.id == opportunity_id, self._visibility()))).scalar_one_or_none()
        if row is None: raise ValueError("Opportunity not found")
        await self.session.execute(pg_insert(AgentOpportunityFollow).values(user_id=self.user_id,
            opportunity_id=opportunity_id, state=state, notes=notes).on_conflict_do_update(
            index_elements=["user_id", "opportunity_id"], set_={"state": state, "notes": notes,
            "updated_at": datetime.now(UTC)})); await self.session.commit()
        return {"followed": True, "state": state, "notes": notes}

    async def unfollow(self, opportunity_id: UUID) -> None:
        await self.session.execute(delete(AgentOpportunityFollow).where(
            AgentOpportunityFollow.user_id == self.user_id,
            AgentOpportunityFollow.opportunity_id == opportunity_id)); await self.session.commit()

    async def create_trade_plan(self, opportunity_id: UUID, values: dict[str, Any]) -> AgentTradePlanDraft:
        visible = (await self.session.execute(select(MarketOpportunity.id).where(
            MarketOpportunity.id == opportunity_id, self._visibility()))).scalar_one_or_none()
        if visible is None: raise ValueError("Opportunity not found")
        profile = await self.risk_profile(); required = ("direction","instrument","entry_price","stop_price","target_price","entry_trigger","horizon")
        missing = [key for key in required if values.get(key) in (None, "")]
        reason = None; quantity = max_loss = notional = None; status = "ready_for_human_confirmation"
        if profile.account_equity is None: reason = "请先在私有风险档案填写账户权益。"
        elif missing: reason = "缺少可客观核验的交易计划字段: " + ", ".join(missing)
        else:
            entry, stop = Decimal(str(values["entry_price"])), Decimal(str(values["stop_price"]))
            per_unit = abs(entry - stop); equity = Decimal(profile.account_equity)
            if per_unit <= 0: reason = "止损价必须由论点失效条件产生，且不能等于进场价。"
            else:
                max_loss = equity * Decimal(profile.risk_per_trade); quantity = max_loss / per_unit
                notional_cap = equity * Decimal(profile.single_instrument_notional) * Decimal(profile.max_leverage)
                quantity = min(quantity, notional_cap / abs(entry)); notional = quantity * abs(entry); max_loss = quantity * per_unit
        if reason: status = "unavailable"
        plan = AgentTradePlanDraft(user_id=self.user_id, opportunity_id=opportunity_id, status=status,
            unavailable_reason=reason, direction=values.get("direction"), instrument=values.get("instrument"),
            entry_trigger=values.get("entry_trigger"), entry_price=values.get("entry_price"), stop_price=values.get("stop_price"),
            target_price=values.get("target_price"), horizon=values.get("horizon"), quantity=quantity, max_loss=max_loss,
            notional=notional, checklist=values.get("checklist") or ["核对最新源日期","确认论点失效条件","人工确认后再执行"],
            assumptions={"sizing_method":"fixed_risk","risk_per_trade":str(profile.risk_per_trade)}, human_confirmation_required=True)
        self.session.add(plan); await self.session.commit(); await self.session.refresh(plan); return plan

    @staticmethod
    def _card(row: MarketOpportunity, followed: bool = False) -> dict[str, Any]:
        return {"id": str(row.id), "scope": row.scope, "domain": row.domain,
            "subject_type": row.subject_type, "subject_key": row.subject_key,
            "playbook_key": row.playbook_key, "title": row.title, "state": row.state,
            "lifecycle_state": row.lifecycle_state, "trigger": row.trigger, "as_of": row.as_of,
            "hypothesis": row.hypothesis, "affected_assets": row.affected_assets,
            "catalysts": row.catalysts, "falsifiers": row.falsifiers,
            "source_dates": row.source_dates, "freshness": row.freshness,
            "first_seen_at": row.first_seen_at, "last_seen_at": row.last_seen_at,
            "closed_at": row.closed_at, "followed": followed}

    @staticmethod
    def _snapshot(row: MarketOpportunitySnapshot) -> dict[str, Any]:
        return {"id": str(row.id), "state": row.state, "as_of": row.as_of, "trigger": row.trigger,
            "hypothesis": row.hypothesis, "affected_assets": row.affected_assets,
            "catalysts": row.catalysts, "falsifiers": row.falsifiers,
            "source_dates": row.source_dates, "freshness": row.freshness,
            "evidence": row.evidence, "chart_refs": row.chart_refs, "created_at": row.created_at}


def profile_payload(profile: AgentRiskProfile) -> dict[str, Any]:
    return {key: _number(getattr(profile, key)) if key not in {"currency","sizing_method"} else getattr(profile, key)
            for key in ("account_equity","currency","risk_per_trade","aggregate_open_risk","single_instrument_notional",
                        "derivative_premium_risk","max_leverage","sizing_method")}


def plan_payload(plan: AgentTradePlanDraft) -> dict[str, Any]:
    return {key: (_number(getattr(plan,key)) if key in {"entry_price","stop_price","target_price","quantity","max_loss","notional"}
                  else str(getattr(plan,key)) if key in {"id","opportunity_id"} else getattr(plan,key))
            for key in ("id","opportunity_id","status","unavailable_reason","direction","instrument","entry_trigger",
                        "entry_price","stop_price","target_price","horizon","quantity","max_loss","notional","checklist",
                        "assumptions","human_confirmation_required")}
