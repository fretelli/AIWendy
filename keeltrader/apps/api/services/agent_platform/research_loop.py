"""User-owned thesis, event inbox, calendar, and global research search."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.agent_platform.models import (
    AgentArtifact,
    AgentCompanyWatchlist,
    AgentHolderWatchlist,
    AgentSchedule,
    AgentSession,
    MarketOpportunity,
    ResearchEvent,
    ResearchThesis,
    ResearchThesisEvidenceLink,
    ResearchThesisVersion,
)
from services.agent_platform.report_kb import ReportKBService

THESIS_STATES = {"draft", "active", "challenged", "invalidated", "closed"}
EVIDENCE_STANCES = {"supporting", "challenging", "invalidating"}


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


def _diff(old: Any, new: Any, path: str = "") -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if isinstance(old, dict) and isinstance(new, dict):
        for key in sorted(set(old) | set(new)):
            changes.update(_diff(old.get(key), new.get(key), f"{path}.{key}".strip(".")))
    elif old != new:
        changes[path] = {"from": old, "to": new}
    return changes


def thesis_snapshot(row: ResearchThesis) -> dict[str, Any]:
    return {
        "title": row.title,
        "subject_type": row.subject_type,
        "subject_key": row.subject_key,
        "status": row.status,
        "thesis": row.thesis,
        "catalysts": row.catalysts,
        "falsifiers": row.falsifiers,
        "review_at": row.review_at.isoformat() if row.review_at else None,
        "origin_resource_type": row.origin_resource_type,
        "origin_resource_id": row.origin_resource_id,
    }


async def record_research_event(
    session: AsyncSession,
    *,
    user_id: UUID,
    event_key: str,
    category: str,
    event_type: str,
    title: str,
    summary: str,
    resource_type: str,
    resource_id: str,
    source_date: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    read: bool = False,
) -> None:
    await session.execute(pg_insert(ResearchEvent).values(
        user_id=user_id,
        event_key=event_key[:96],
        category=category,
        event_type=event_type,
        title=title,
        summary=summary,
        resource_type=resource_type,
        resource_id=resource_id,
        source_date=source_date,
        before_state=before_state or {},
        after_state=after_state or {},
        metadata_json=metadata or {},
        read_at=datetime.now(UTC) if read else None,
        detected_at=datetime.now(UTC),
    ).on_conflict_do_nothing(index_elements=["user_id", "event_key"]))


class ThesisService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def list(self, *, status: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        filters = [ResearchThesis.user_id == self.user_id]
        if status:
            filters.append(ResearchThesis.status == status)
        rows = (await self.session.execute(select(ResearchThesis).where(*filters).order_by(
            desc(ResearchThesis.updated_at), ResearchThesis.title).limit(limit).offset(offset))).scalars().all()
        total = (await self.session.execute(select(func.count()).select_from(ResearchThesis).where(*filters))).scalar_one()
        return {"items": [self._item(row) for row in rows], "total": int(total), "limit": limit, "offset": offset,
                "ordering": "updated_at_desc", "scoring": False}

    async def detail(self, thesis_id: UUID) -> dict[str, Any] | None:
        row = await self._owned(thesis_id)
        if row is None:
            return None
        versions = (await self.session.execute(select(ResearchThesisVersion).where(
            ResearchThesisVersion.thesis_id == row.id).order_by(desc(ResearchThesisVersion.version)))).scalars().all()
        evidence = (await self.session.execute(select(ResearchThesisEvidenceLink).where(
            ResearchThesisEvidenceLink.thesis_id == row.id).order_by(ResearchThesisEvidenceLink.created_at))).scalars().all()
        result = self._item(row)
        result["versions"] = [{"id": str(item.id), "version": item.version, "snapshot": item.snapshot,
                               "diff": item.diff, "created_at": item.created_at} for item in versions]
        result["evidence"] = [{"id": str(item.id), "stance": item.stance, "source_type": item.source_type,
                               "source_id": item.source_id, "citation": item.citation,
                               "created_at": item.created_at} for item in evidence]
        return result

    async def create(self, values: dict[str, Any]) -> dict[str, Any]:
        status = str(values.get("status") or "draft")
        if status not in THESIS_STATES:
            raise ValueError("Invalid thesis status")
        row = ResearchThesis(
            user_id=self.user_id,
            title=values["title"],
            subject_type=values["subject_type"],
            subject_key=values["subject_key"],
            status=status,
            thesis=values["thesis"],
            catalysts=values.get("catalysts") or [],
            falsifiers=values.get("falsifiers") or [],
            review_at=values.get("review_at"),
            origin_resource_type=values.get("origin_resource_type"),
            origin_resource_id=values.get("origin_resource_id"),
            closed_at=datetime.now(UTC) if status == "closed" else None,
        )
        self.session.add(row)
        await self.session.flush()
        self.session.add(ResearchThesisVersion(thesis_id=row.id, version=1, snapshot=thesis_snapshot(row), diff={}))
        for link in values.get("evidence") or []:
            self._validate_evidence(link)
            self.session.add(ResearchThesisEvidenceLink(thesis_id=row.id, **link))
        await self.session.commit()
        return (await self.detail(row.id)) or self._item(row)

    async def update(self, thesis_id: UUID, values: dict[str, Any]) -> dict[str, Any]:
        row = await self._owned(thesis_id, lock=True)
        if row is None:
            raise ValueError("Thesis not found")
        previous = thesis_snapshot(row)
        for key in ("title", "subject_type", "subject_key", "thesis", "catalysts", "falsifiers"):
            if key in values and values[key] is not None:
                setattr(row, key, values[key])
        if "review_at" in values:
            row.review_at = values["review_at"]
        if values.get("status"):
            if values["status"] not in THESIS_STATES:
                raise ValueError("Invalid thesis status")
            row.status = values["status"]
            row.closed_at = datetime.now(UTC) if row.status == "closed" else None
        current = thesis_snapshot(row)
        changes = _diff(previous, current)
        if changes:
            row.current_version += 1
            row.updated_at = datetime.now(UTC)
            self.session.add(ResearchThesisVersion(thesis_id=row.id, version=row.current_version,
                                                   snapshot=current, diff=changes))
            await record_research_event(
                self.session,
                user_id=self.user_id,
                event_key=f"thesis:{row.id}:v{row.current_version}",
                category="thesis",
                event_type="thesis_changed",
                title=f"论点更新 · {row.title}",
                summary="用户确认了新的论点版本；请按变化字段复核证据与证伪条件。",
                resource_type="thesis",
                resource_id=str(row.id),
                before_state=previous,
                after_state=current,
                read=True,
            )
        await self.session.commit()
        return (await self.detail(row.id)) or self._item(row)

    async def add_evidence(self, thesis_id: UUID, values: dict[str, Any]) -> dict[str, Any]:
        row = await self._owned(thesis_id)
        if row is None:
            raise ValueError("Thesis not found")
        self._validate_evidence(values)
        await self.session.execute(pg_insert(ResearchThesisEvidenceLink).values(
            thesis_id=row.id, **values).on_conflict_do_nothing(
            index_elements=["thesis_id", "stance", "source_type", "source_id"]))
        await self.session.commit()
        return (await self.detail(row.id)) or self._item(row)

    async def calendar(self) -> dict[str, Any]:
        theses = (await self.session.execute(select(ResearchThesis).where(
            ResearchThesis.user_id == self.user_id, ResearchThesis.status.not_in({"closed", "invalidated"})))).scalars().all()
        schedules = (await self.session.execute(select(AgentSchedule).where(
            AgentSchedule.user_id == self.user_id, AgentSchedule.enabled.is_(True)))).scalars().all()
        items: list[dict[str, Any]] = []
        for row in theses:
            if row.review_at:
                items.append({"kind": "thesis_review", "date": row.review_at, "title": row.title,
                              "resource_type": "thesis", "resource_id": str(row.id), "source_type": "user_plan"})
            for catalyst in row.catalysts or []:
                if isinstance(catalyst, dict) and catalyst.get("date") and catalyst.get("label"):
                    items.append({"kind": "catalyst", "date": catalyst["date"], "title": catalyst["label"],
                                  "resource_type": "thesis", "resource_id": str(row.id),
                                  "source_type": catalyst.get("source_type") or "user_plan",
                                  "source_ref": catalyst.get("source_ref")})
        for schedule in schedules:
            if schedule.next_run_at:
                items.append({"kind": "scheduled_research", "date": schedule.next_run_at,
                              "title": schedule.name, "resource_type": "schedule",
                              "resource_id": str(schedule.id), "source_type": "system_schedule"})
        return {"items": sorted(items, key=lambda item: str(item["date"])),
                "synthetic_dates": False, "note": "只展示用户计划或有明确来源的日期。"}

    async def _owned(self, thesis_id: UUID, *, lock: bool = False) -> ResearchThesis | None:
        query = select(ResearchThesis).where(ResearchThesis.id == thesis_id,
                                             ResearchThesis.user_id == self.user_id)
        if lock:
            query = query.with_for_update()
        return (await self.session.execute(query)).scalar_one_or_none()

    @staticmethod
    def _validate_evidence(values: dict[str, Any]) -> None:
        if values.get("stance") not in EVIDENCE_STANCES:
            raise ValueError("Invalid evidence stance")
        citation = values.get("citation") if isinstance(values.get("citation"), dict) else {}
        if values.get("source_type") == "report" and not (
            str(citation.get("excerpt") or "").strip()
            and (citation.get("section_id") or citation.get("page_number") is not None)
        ):
            raise ValueError("Report evidence requires a body excerpt and page or section location")

    @staticmethod
    def _item(row: ResearchThesis) -> dict[str, Any]:
        return {"id": str(row.id), "title": row.title, "subject_type": row.subject_type,
                "subject_key": row.subject_key, "status": row.status, "thesis": row.thesis,
                "catalysts": row.catalysts, "falsifiers": row.falsifiers, "review_at": row.review_at,
                "origin_resource_type": row.origin_resource_type, "origin_resource_id": row.origin_resource_id,
                "current_version": row.current_version, "closed_at": row.closed_at,
                "created_at": row.created_at, "updated_at": row.updated_at}


class EventService:
    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id

    async def list(self, *, category: str | None = None, unread: bool = False,
                   limit: int = 100, offset: int = 0) -> dict[str, Any]:
        filters = [ResearchEvent.user_id == self.user_id, ResearchEvent.archived_at.is_(None)]
        if category:
            filters.append(ResearchEvent.category == category)
        if unread:
            filters.append(ResearchEvent.read_at.is_(None))
        rows = (await self.session.execute(select(ResearchEvent).where(*filters).order_by(
            desc(ResearchEvent.detected_at), ResearchEvent.id).limit(limit).offset(offset))).scalars().all()
        unread_count = (await self.session.execute(select(func.count()).select_from(ResearchEvent).where(
            ResearchEvent.user_id == self.user_id, ResearchEvent.archived_at.is_(None),
            ResearchEvent.read_at.is_(None)))).scalar_one()
        return {"items": [self._item(row) for row in rows], "unread": int(unread_count),
                "limit": limit, "offset": offset, "ordering": "detected_at_desc", "scoring": False}

    async def mark_read(self, event_ids: list[UUID] | None = None) -> int:
        query = select(ResearchEvent).where(ResearchEvent.user_id == self.user_id,
                                            ResearchEvent.read_at.is_(None))
        if event_ids:
            query = query.where(ResearchEvent.id.in_(event_ids))
        rows = (await self.session.execute(query)).scalars().all()
        now = datetime.now(UTC)
        for row in rows:
            row.read_at = now
        await self.session.commit()
        return len(rows)

    @staticmethod
    def _item(row: ResearchEvent) -> dict[str, Any]:
        return {"id": str(row.id), "category": row.category, "event_type": row.event_type,
                "title": row.title, "summary": row.summary, "resource_type": row.resource_type,
                "resource_id": row.resource_id, "source_date": row.source_date,
                "before_state": row.before_state, "after_state": row.after_state,
                "metadata": row.metadata_json, "read_at": row.read_at,
                "detected_at": row.detected_at, "created_at": row.created_at}


async def global_search(session: AsyncSession, user_id: UUID, query: str, limit: int = 30) -> dict[str, Any]:
    term = f"%{query.strip()}%"
    per_type = max(2, min(8, limit // 5 or 2))
    sessions, companies, holders, theses, opportunities, artifacts = await _search_local(
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
        *[{"type": "thesis", "id": str(row.id), "title": row.title,
           "subtitle": row.thesis[:160], "href": f"/agent/theses?thesis={row.id}"} for row in theses],
        *[{"type": "opportunity", "id": str(row.id), "title": row.title,
           "subtitle": row.trigger[:160], "href": f"/agent/market/opportunities?opportunity={row.id}"}
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
        AgentSession.user_id == user_id, AgentSession.title.ilike(term)).order_by(desc(AgentSession.updated_at)).limit(limit))).scalars().all()
    companies = (await session.execute(select(AgentCompanyWatchlist).where(
        AgentCompanyWatchlist.user_id == user_id,
        or_(AgentCompanyWatchlist.company_name.ilike(term), AgentCompanyWatchlist.company_code.ilike(term))).limit(limit))).scalars().all()
    holders = (await session.execute(select(AgentHolderWatchlist).where(
        AgentHolderWatchlist.user_id == user_id, AgentHolderWatchlist.holder_name.ilike(term)).limit(limit))).scalars().all()
    theses = (await session.execute(select(ResearchThesis).where(
        ResearchThesis.user_id == user_id,
        or_(ResearchThesis.title.ilike(term), ResearchThesis.thesis.ilike(term))).order_by(desc(ResearchThesis.updated_at)).limit(limit))).scalars().all()
    opportunities = (await session.execute(select(MarketOpportunity).where(
        or_(MarketOpportunity.scope == "global", MarketOpportunity.user_id == user_id),
        or_(MarketOpportunity.title.ilike(term), MarketOpportunity.trigger.ilike(term))).limit(limit))).scalars().all()
    artifacts = (await session.execute(select(AgentArtifact).where(
        AgentArtifact.user_id == user_id, AgentArtifact.title.ilike(term)).order_by(desc(AgentArtifact.created_at)).limit(limit))).scalars().all()
    return sessions, companies, holders, theses, opportunities, artifacts


def stable_event_key(*parts: Any) -> str:
    return hashlib.sha256(json.dumps([_json(part) for part in parts], ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()
