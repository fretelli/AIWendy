"""Global research search across active KeelTrader surfaces."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import (
    AgentArtifact,
    AgentCompanyWatchlist,
    AgentHolderWatchlist,
    AgentSession,
    MarketOpportunity,
)
from services.agent_platform.report_kb import ReportKBService


async def global_search(session: AsyncSession, user_id: UUID, query: str, limit: int = 30) -> dict:
    term = f"%{query.strip()}%"
    per_type = max(2, min(8, limit // 5 or 2))
    sessions, companies, holders, opportunities, artifacts = await _search_local(
        session, user_id, term, per_type)
    report_rows = await ReportKBService().search_reports(query, top_k=min(5, per_type))
    items = [
        *[{"type": "session", "id": str(row.id), "title": row.title, "subtitle": row.summary,
           "href": f"/agent?session={row.id}"} for row in sessions],
        *[{"type": "company", "id": row.company_code, "title": row.company_name,
           "subtitle": " · ".join(filter(None, [row.company_code, row.industry])),
           "href": f"/agent?company={row.company_code}"} for row in companies],
        *[{"type": "holder", "id": str(row.id), "title": row.holder_name,
           "subtitle": row.holder_type, "href": f"/agent/holders?watch={row.id}"} for row in holders],
        *[{"type": "opportunity", "id": str(row.id), "title": row.title,
           "subtitle": row.trigger[:160], "href": f"/agent/opportunities?opportunity={row.id}"}
          for row in opportunities],
        *[{"type": "artifact", "id": str(row.id), "title": row.title,
           "subtitle": row.artifact_type, "href": f"/agent?run={row.run_id}"} for row in artifacts],
        *[{"type": "report", "id": str(row.get("report_id") or row.get("id") or ""),
           "title": str(row.get("title") or "未命名研报"),
           "subtitle": "研报导航结果；未带正文定位时不构成公司证据",
           "href": "/agent", "navigation_only": True,
           "citation": {key: row.get(key) for key in ("report_id", "section_id", "page_number", "excerpt")}}
          for row in report_rows],
    ]
    return {"items": items[:limit], "query": query, "scoring": False,
            "note": "结果按对象类型组织；研报标题结果仅用于导航。"}


async def _search_local(session: AsyncSession, user_id: UUID, term: str, limit: int):
    sessions = (await session.execute(select(AgentSession).where(
        AgentSession.user_id == user_id, AgentSession.title.ilike(term)).order_by(
        desc(AgentSession.updated_at)).limit(limit))).scalars().all()
    companies = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user_id,
        or_(AgentCompanyWatchlist.company_name.ilike(term),
            AgentCompanyWatchlist.company_code.ilike(term))).limit(limit))).scalars().all()
    holders = (await session.execute(select(AgentHolderWatchlist).where(
        AgentHolderWatchlist.user_id == user_id,
        AgentHolderWatchlist.holder_name.ilike(term)).limit(limit))).scalars().all()
    opportunities = (await session.execute(select(MarketOpportunity).where(
        or_(MarketOpportunity.scope == "global", MarketOpportunity.user_id == user_id),
        or_(MarketOpportunity.title.ilike(term), MarketOpportunity.trigger.ilike(term))).limit(limit))).scalars().all()
    artifacts = (await session.execute(select(AgentArtifact).where(
        AgentArtifact.user_id == user_id, AgentArtifact.title.ilike(term)).order_by(
        desc(AgentArtifact.created_at)).limit(limit))).scalars().all()
    return sessions, companies, holders, opportunities, artifacts
