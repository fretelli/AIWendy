from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import (
    AgentRiskProfile, AgentTradePlanDraft, MarketOpportunity, MarketOpportunityEvidence,
)
from services.agent_platform.tushare import TushareReadService


def _number(value: Any) -> float | None:
    return float(value) if value is not None else None


class OpportunityService:
    """Deterministic evidence cards and private fixed-risk trade-plan drafts."""

    def __init__(self, session: AsyncSession, reader: TushareReadService, user_id: UUID):
        self.session, self.reader, self.user_id = session, reader, user_id

    async def risk_profile(self) -> AgentRiskProfile:
        profile = await self.session.get(AgentRiskProfile, self.user_id)
        if profile is None:
            profile = AgentRiskProfile(user_id=self.user_id)
            self.session.add(profile); await self.session.commit(); await self.session.refresh(profile)
        return profile

    async def update_risk_profile(self, values: dict[str, Any]) -> AgentRiskProfile:
        profile = await self.risk_profile()
        for key in ("account_equity", "currency", "risk_per_trade", "aggregate_open_risk",
                    "single_instrument_notional", "derivative_premium_risk", "max_leverage"):
            if key in values and values[key] is not None: setattr(profile, key, values[key])
        profile.sizing_method = "fixed_risk"; profile.updated_at = datetime.now(timezone.utc)
        await self.session.commit(); await self.session.refresh(profile); return profile

    async def refresh(self) -> None:
        cards = await self._observations()
        now = datetime.now(timezone.utc)
        for card in cards:
            fingerprint = hashlib.sha256(f'{card["playbook_key"]}:{card["source_dates"]}'.encode()).hexdigest()[:40]
            existing = (await self.session.execute(select(MarketOpportunity).where(MarketOpportunity.fingerprint == fingerprint))).scalar_one_or_none()
            if existing is None:
                existing = MarketOpportunity(fingerprint=fingerprint, **{k: card[k] for k in (
                    "playbook_key","title","lifecycle_state","hypothesis","affected_assets","catalysts","falsifiers","source_dates")})
                self.session.add(existing); await self.session.flush()
            else:
                existing.last_seen_at = now; existing.lifecycle_state = card["lifecycle_state"]
                await self.session.execute(delete(MarketOpportunityEvidence).where(MarketOpportunityEvidence.opportunity_id == existing.id))
            for evidence in card["evidence"]:
                self.session.add(MarketOpportunityEvidence(opportunity_id=existing.id, **evidence))
        await self.session.commit()

    async def _observations(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        if await self.reader.table_exists("repo_daily"):
            repo = await self.reader._execute_mappings(text(f"""SELECT trade_date,repo_maturity,weight,close,amount
                FROM {self.reader.schema}.repo_daily WHERE repo_maturity IN ('DR007','R007')
                ORDER BY trade_date DESC,CASE WHEN repo_maturity='DR007' THEN 0 ELSE 1 END LIMIT 2"""), {})
            if repo:
                latest = repo[0]; previous = next((row for row in repo[1:] if row["repo_maturity"] == latest["repo_maturity"]), None)
                change = (_number(latest.get("weight")) - _number(previous.get("weight"))) * 100 if previous and latest.get("weight") is not None and previous.get("weight") is not None else None
                latest_weight = _number(latest.get("weight"))
                evidence = [{"stance":"supporting","fact":f'{latest["repo_maturity"]} 加权利率 {latest_weight:.4f}%' if latest_weight is not None else f'{latest["repo_maturity"]} 加权利率源字段缺失',
                             "source":f"{self.reader.schema}.repo_daily","source_date":str(latest["trade_date"]),"source_ref":latest}]
                if change is not None:
                    evidence.append({"stance":"opposing" if change > 0 else "supporting",
                                     "fact":f"相邻源记录变化 {change:+.2f} bp；上行代表资金价格收紧，下行代表缓和。",
                                     "source":f"{self.reader.schema}.repo_daily","source_date":str(latest["trade_date"]),"source_ref":{"change_bp":change}})
                source_dates = {"repo": str(latest["trade_date"])}
                if all([await self.reader.table_exists("fut_mapping"), await self.reader.table_exists("fut_daily"), await self.reader.table_exists("fut_basic")]):
                    treasury = await self.reader._execute_mappings(text(f"""WITH latest AS (
                        SELECT DISTINCT ON(m.ts_code) m.ts_code,m.trade_date,m.mapping_ts_code FROM {self.reader.schema}.fut_mapping m
                        WHERE split_part(m.ts_code,'.',1) IN ('T','TF','TS','TL') ORDER BY m.ts_code,m.trade_date DESC)
                        SELECT l.ts_code,l.trade_date,l.mapping_ts_code,d.close,d.settle,d.oi FROM latest l
                        JOIN {self.reader.schema}.fut_daily d ON d.ts_code=l.mapping_ts_code AND d.trade_date=l.trade_date
                        ORDER BY l.ts_code"""), {})
                    if treasury:
                        source_dates["treasury_futures"] = max(str(row["trade_date"]) for row in treasury)
                        evidence.append({"stance":"supporting","fact":"国债期货最新源记录：" + "；".join(
                            f'{row["ts_code"]}→{row["mapping_ts_code"]} 结算 {row.get("settle") or "—"}' for row in treasury),
                            "source":f"{self.reader.schema}.fut_mapping+fut_daily","source_date":source_dates["treasury_futures"],
                            "source_ref":{"contracts":treasury}})
                if await self.reader.table_exists("stock_daily"):
                    breadth = await self.reader._execute_mappings(text(f"""SELECT trade_date,COUNT(*)::int stocks,
                        COUNT(*) FILTER(WHERE pct_chg>0)::int advances,COUNT(*) FILTER(WHERE pct_chg<0)::int declines,
                        SUM(COALESCE(amount,0))*1000 turnover_cny FROM {self.reader.schema}.stock_daily
                        WHERE trade_date=(SELECT MAX(trade_date) FROM {self.reader.schema}.stock_daily) GROUP BY trade_date"""), {})
                    if breadth:
                        b = breadth[0]; source_dates["a_share"] = str(b["trade_date"])
                        stance = "supporting" if int(b.get("advances") or 0) >= int(b.get("declines") or 0) else "opposing"
                        evidence.append({"stance":stance,"fact":f'A股最新源记录上涨 {b["advances"]} 家、下跌 {b["declines"]} 家，成交额 {float(b.get("turnover_cny") or 0):,.0f} 元。',
                            "source":f"{self.reader.schema}.stock_daily","source_date":str(b["trade_date"]),"source_ref":b})
                cards.append({"playbook_key":"china_liquidity_transmission","title":"中国流动性向国债期货与风险资产的传导",
                    "lifecycle_state":"observing","hypothesis":"回购资金价格变化可能先影响国债期货，再传导至权益风险偏好；当前仅保留可核验观察，不给综合分数。",
                    "affected_assets":["DR007/R007","T/TF/TS/TL","A股/ETF"],"catalysts":["央行公开市场操作","税期与跨月","国债期货结算"],
                    "falsifiers":["回购利率反向变化","国债期货未确认","权益资金面出现相反证据"],
                    "source_dates":source_dates,"evidence":evidence})
        if await self.reader.table_exists("option_analytics_daily"):
            rows = await self.reader._execute_mappings(text(f"""SELECT trade_date,COUNT(*)::int contracts,
                COUNT(*) FILTER(WHERE convergence_status='converged')::int resolved,
                COUNT(DISTINCT opt_code)::int series FROM {self.reader.schema}.option_analytics_daily
                WHERE trade_date=(SELECT MAX(trade_date) FROM {self.reader.schema}.option_analytics_daily) GROUP BY trade_date"""), {})
            if rows:
                row = rows[0]
                cards.append({"playbook_key":"option_surface_evidence","title":"期权 IV、Greeks 与期限/行权价证据链",
                    "lifecycle_state":"observing","hypothesis":"逐合约模型结果已可用于核对波动率结构和敏感度，但必须在具体底层、到期日和行权价上形成交易假设。",
                    "affected_assets":["指数/ETF/商品期权"],"catalysts":["标的价格变化","到期临近","波动率重定价"],
                    "falsifiers":["底层标的未解析","模型不收敛","源行情缺失"],"source_dates":{"options":str(row["trade_date"])},
                    "evidence":[{"stance":"supporting","fact":f'{row["series"]} 个系列、{row["contracts"]} 个合约中 {row["resolved"]} 个已有收敛模型结果。',
                                 "source":f"{self.reader.schema}.option_analytics_daily","source_date":str(row["trade_date"]),"source_ref":row},
                                {"stance":"opposing","fact":"OI 敏感度为 gross OI-weighted sensitivity，不代表做市商净 Gamma。",
                                 "source":f"{self.reader.schema}.option_analytics_daily","source_date":str(row["trade_date"]),"source_ref":{}}]})
        return cards

    async def list(self) -> dict[str, Any]:
        await self.refresh()
        rows = (await self.session.execute(select(MarketOpportunity).order_by(MarketOpportunity.last_seen_at.desc()))).scalars().all()
        return {"items": [self._card(row) for row in rows], "ordering": "source_date_desc", "scoring": False}

    async def detail(self, opportunity_id: UUID) -> dict[str, Any] | None:
        row = await self.session.get(MarketOpportunity, opportunity_id)
        if row is None: return None
        evidence = (await self.session.execute(select(MarketOpportunityEvidence).where(
            MarketOpportunityEvidence.opportunity_id == row.id).order_by(MarketOpportunityEvidence.created_at))).scalars().all()
        result = self._card(row); result["evidence"] = [{"stance":e.stance,"fact":e.fact,"source":e.source,
            "source_date":e.source_date,"source_ref":e.source_ref} for e in evidence]
        return result

    async def create_trade_plan(self, opportunity_id: UUID, values: dict[str, Any]) -> AgentTradePlanDraft:
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
    def _card(row: MarketOpportunity) -> dict[str, Any]:
        return {"id":str(row.id),"playbook_key":row.playbook_key,"title":row.title,"lifecycle_state":row.lifecycle_state,
                "hypothesis":row.hypothesis,"affected_assets":row.affected_assets,"catalysts":row.catalysts,
                "falsifiers":row.falsifiers,"source_dates":row.source_dates,"first_seen_at":row.first_seen_at,
                "last_seen_at":row.last_seen_at}


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
