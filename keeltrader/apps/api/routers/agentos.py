"""AgentOS research, decision, review, and strategy routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.database import get_session
from domain.agentos.models import (
    FundamentalValidationRun,
    InvestmentBrief,
    InvestmentDecision,
    InvestmentMemo,
    ReviewLesson,
    StrategyHypothesis,
)
from domain.agentos.schemas import (
    BriefRunRequest,
    DecisionCreateRequest,
    DecisionOutcomeRequest,
    FundamentalValidationRequest,
    HypothesisCreateRequest,
    ReportSearchRequest,
    ResearchRunRequest,
    TushareQueryRequest,
)
from domain.user.models import User
from services.agentos.report_kb import ReportKBService
from services.agentos.serializers import model_dict, serialize
from services.agentos.service import AgentOSService
from services.agentos.tushare_read import TushareReadService

router = APIRouter()


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    heartbeat = None
    try:
        import json
        from config import get_settings
        import redis.asyncio as aioredis

        r = aioredis.from_url(get_settings().redis_url)
        raw = await r.get("keeltrader:agentos:heartbeat")
        await r.aclose()
        if raw:
            heartbeat = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except Exception:
        heartbeat = None

    tushare = {"configured": False, "stock_basic_exists": False, "reachable": False}
    try:
        from config import get_settings

        svc = TushareReadService(session)
        stock_basic_exists = await svc.table_exists("stock_basic")
        tushare = {
            "configured": bool(get_settings().tushare_database_url),
            "stock_basic_exists": stock_basic_exists,
            "reachable": True,
        }
    except Exception as exc:
        tushare = {
            "configured": False,
            "stock_basic_exists": False,
            "reachable": False,
            "error": str(exc)[:200],
        }

    report_kb = await ReportKBService().health()

    return {
        "status": "ok",
        "service": "agentos",
        "engine": heartbeat or {"status": "not_running"},
        "tushare": tushare,
        "report_kb": report_kb,
        "tushare_token_required": False,
    }


@router.post("/briefs/run")
async def run_brief(
    req: BriefRunRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    brief = await svc.run_daily_brief(user.id, req.watchlist or req.symbols, req.project_id)
    return {"brief": model_dict(brief)}


@router.get("/briefs/latest")
async def latest_brief(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    brief = await svc.latest_brief(user.id)
    return {"brief": model_dict(brief) if brief else None}


@router.get("/briefs")
async def list_briefs(
    limit: int = 20,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 100))
    result = await session.execute(
        select(InvestmentBrief)
        .where(InvestmentBrief.user_id == user.id)
        .order_by(desc(InvestmentBrief.brief_date))
        .limit(limit)
    )
    return {"briefs": [model_dict(item) for item in result.scalars().all()]}


@router.post("/research/run")
async def run_research(
    req: ResearchRunRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    memo = await svc.run_deep_research(user.id, req.symbol, req.market, req.project_id)
    return {"memo": model_dict(memo)}


@router.get("/research/{memo_id}")
async def get_research(
    memo_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    memo = await svc.get_memo(user.id, memo_id)
    if not memo:
        raise HTTPException(status_code=404, detail="Research memo not found")
    return {"memo": model_dict(memo)}


@router.get("/research")
async def list_research(
    limit: int = 20,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 100))
    result = await session.execute(
        select(InvestmentMemo)
        .where(InvestmentMemo.user_id == user.id)
        .order_by(desc(InvestmentMemo.created_at))
        .limit(limit)
    )
    return {"memos": [model_dict(item) for item in result.scalars().all()]}


@router.post("/reports/search")
async def search_reports(
    req: ReportSearchRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _ = user
    svc = AgentOSService(session)
    reports = await svc.search_reports(user.id, req.query, req.top_k, req.companies or None)
    return {"reports": serialize(reports)}


@router.post("/decisions")
async def create_decision(
    req: DecisionCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    decision = await svc.record_decision(user.id, req.model_dump())
    return {"decision": model_dict(decision)}


@router.get("/decisions")
async def list_decisions(
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 200))
    result = await session.execute(
        select(InvestmentDecision)
        .where(InvestmentDecision.user_id == user.id)
        .order_by(desc(InvestmentDecision.created_at))
        .limit(limit)
    )
    return {"decisions": [model_dict(item) for item in result.scalars().all()]}


@router.post("/decisions/{decision_id}/outcome")
async def update_decision_outcome(
    decision_id: UUID,
    req: DecisionOutcomeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    decision = await svc.update_decision_outcome(user.id, decision_id, req.outcome)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return {"decision": model_dict(decision)}


@router.post("/reviews/weekly/run")
async def run_weekly_review(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    lessons = await svc.run_weekly_review(user.id)
    return {"lessons": [model_dict(l) for l in lessons]}


@router.get("/lessons")
async def list_lessons(
    approved: bool | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 200))
    stmt = select(ReviewLesson).where(ReviewLesson.user_id == user.id)
    if approved is not None:
        stmt = stmt.where(ReviewLesson.approved == approved)
    stmt = stmt.order_by(desc(ReviewLesson.created_at)).limit(limit)
    result = await session.execute(stmt)
    return {"lessons": [model_dict(item) for item in result.scalars().all()]}


@router.post("/lessons/{lesson_id}/approve")
async def approve_lesson(
    lesson_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    lesson = await svc.approve_lesson(user.id, lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return {"lesson": model_dict(lesson)}


@router.post("/strategy/hypotheses")
async def create_hypothesis(
    req: HypothesisCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = AgentOSService(session)
    hypothesis = await svc.create_hypothesis(user.id, req.model_dump())
    return {"hypothesis": model_dict(hypothesis)}


@router.get("/strategy/hypotheses")
async def list_hypotheses(
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 200))
    result = await session.execute(
        select(StrategyHypothesis)
        .where(StrategyHypothesis.user_id == user.id)
        .order_by(desc(StrategyHypothesis.created_at))
        .limit(limit)
    )
    return {"hypotheses": [model_dict(item) for item in result.scalars().all()]}


async def _record_fundamental_validation(
    req: FundamentalValidationRequest,
    user: User,
    session: AsyncSession,
):
    svc = AgentOSService(session)
    run = await svc.record_validation(
        user.id,
        symbol=req.symbol,
        strategy=req.strategy or "fundamental_validation",
        params=req.params,
        hypothesis_id=req.hypothesis_id,
    )
    return run


@router.post("/strategy/validations/run")
async def run_fundamental_validation(
    req: FundamentalValidationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    run = await _record_fundamental_validation(req, user, session)
    return {"validation": model_dict(run)}


@router.get("/strategy/validations")
async def list_validations(
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    limit = max(1, min(limit, 200))
    result = await session.execute(
        select(FundamentalValidationRun)
        .where(FundamentalValidationRun.user_id == user.id)
        .order_by(desc(FundamentalValidationRun.created_at))
        .limit(limit)
    )
    items = [model_dict(item) for item in result.scalars().all()]
    return {"validations": items}


@router.post("/tushare/query")
async def query_tushare(
    req: TushareQueryRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _ = user
    svc = TushareReadService(session)
    rows = await svc.query_table(req.table, req.filters, req.limit)
    return {"rows": serialize(rows), "tushare_token_required": False}
