from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from typing import Any, Awaitable, Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.auth import get_current_user
from core.cache_service import get_cache_service
from core.database import get_session
from core.logging import get_logger
from domain.user.models import User
from domain.agent_platform.models import MarketOpportunityRefreshState
from services.agent_platform.tushare import TushareReadService
from services.agent_platform.opportunities import OpportunityService, plan_payload
from services.agent_platform.publication_status import publication_version, read_publication_status

router = APIRouter()
logger = get_logger(__name__)


async def cached_json(key: str, loader: Callable[[], Awaitable[dict[str, Any]]], ttl: int = 600) -> Response:
    started = time.perf_counter()
    cache = get_cache_service()
    version = publication_version()
    cache_key = f"markets:v4:{version}:{key}"
    payload = await cache.get_async(cache_key)
    cache_state = "hit"
    if not isinstance(payload, dict):
        payload = await loader()
        await cache.set_async(cache_key, payload, ttl=ttl)
        cache_state = "miss"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    etag = '"' + hashlib.sha256(body).hexdigest()[:24] + '"'
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("market_read", cache_key=key, cache=cache_state, duration_ms=round(elapsed_ms, 1),
                payload_bytes=len(body))
    return Response(content=body, media_type="application/json", headers={
        "Cache-Control": "private, max-age=60, stale-while-revalidate=300",
        "ETag": etag, "X-Market-Cache": cache_state, "X-Market-Publication": version,
        "X-Payload-Bytes": str(len(body)),
        "Server-Timing": f'market;dur={elapsed_ms:.1f};desc="{cache_state}"',
    })


def service(session: AsyncSession) -> TushareReadService:
    return TushareReadService(session)


@router.get("/data-status")
async def data_status(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    """Read source coverage and background refresh state without triggering ingestion."""
    refresh_rows = (await session.execute(select(MarketOpportunityRefreshState).order_by(
        MarketOpportunityRefreshState.domain))).scalars().all()
    return {
        "publication": read_publication_status(),
        "opportunity_refresh": [{
            "domain": row.domain, "status": row.status,
            "last_started_at": row.last_started_at, "last_succeeded_at": row.last_succeeded_at,
            "last_error": row.last_error, "duration_ms": row.duration_ms,
            "candidates_seen": row.candidates_seen, "source_watermark": row.source_watermark,
        } for row in refresh_rows],
        "read_only": True,
        "request_time_refresh": False,
        "scoring": False,
        "methodology": "读取后台原子发布的数据覆盖快照，不在请求时扫描源表；缺失或延迟来源明确标记，不合成替代。",
    }


@router.get("/capital")
async def market_capital(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("capital:all-raw-history", service(session).market_capital_snapshot)


@router.get("/macro/series")
async def macro_catalog(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json("macro:catalog", reader.macro_catalog)


@router.get("/rates/catalog")
async def rates_catalog(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("rates:catalog", service(session).rates_catalog)


@router.get("/rates/series/{key}")
async def rates_series(key: str, field: str = Query(...), bank: str | None = None, maturity: str | None = None,
                       session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    try:
        return await cached_json(f"rates:{key}:{field}:{bank or '-'}:{maturity or '-'}",
                                 lambda: reader.rates_series(key, field, bank, maturity))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/rates/curve")
async def rates_curve(key: str = Query(...), curve_date: date | None = None,
                      session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    try:
        return await cached_json(f"rates:curve:{key}:{curve_date or 'latest'}", lambda: reader.rates_curve(key, curve_date))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/bonds/futures")
async def bond_futures(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("bonds:futures", service(session).treasury_futures)


@router.get("/bonds/convertibles")
async def bond_convertibles(code: str | None = None, limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0),
                            session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json(f"bonds:convertibles:{code or '-'}:{limit}:{offset}",
                             lambda: service(session).convertibles(code, limit, offset))


@router.get("/macro/series/{key}")
async def macro_series(key: str, field: str = Query(...), session: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user)):
    reader = service(session)
    try:
        return await cached_json(f"macro:{key}:{field}", lambda: reader.macro_series(key, field))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/futures/products")
async def futures_products(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json("futures:products", reader.futures_products)


@router.get("/futures/{code}/history")
async def futures_history(code: str, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"futures:{code}:history", lambda: reader.futures_history(code))


@router.get("/futures/{code}/curve")
async def futures_curve(code: str, trade_date: date | None = None, session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"futures:{code}:curve:{trade_date or 'latest'}", lambda: reader.futures_curve(code, trade_date))


@router.get("/futures/{code}/underlying")
async def futures_underlying(code: str, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"futures:{code}:underlying", lambda: reader.futures_underlying(code))


@router.get("/options/underlyings")
async def option_underlyings(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json("options:catalog", reader.options_series)


@router.get("/options/{code}/history")
async def options_history(code: str, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"options:{code}:history", lambda: reader.options_history(code))


@router.get("/options/{code}/chain")
async def options_chain(code: str, trade_date: date | None = None, maturity: date | None = None,
                        limit: int = Query(300, ge=1, le=500), offset: int = Query(0, ge=0),
                        session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    key = f"options:{code}:chain:{trade_date or 'latest'}:{maturity or 'all'}:{limit}:{offset}"
    return await cached_json(key, lambda: reader.options_chain(code, trade_date, maturity, limit, offset), ttl=300)


@router.get("/options/{code}/underlying")
async def option_underlying(code: str, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"options:{code}:underlying", lambda: reader.option_underlying(code))


@router.get("/options/{code}/surface")
async def option_surface(code: str, trade_date: date | None = None, session: AsyncSession = Depends(get_session),
                         user: User = Depends(get_current_user)):
    return await cached_json(f"options:{code}:surface:{trade_date or 'latest'}",
                             lambda: service(session).options_surface(code, trade_date), ttl=300)


@router.get("/options/{code}/exposures")
async def option_exposures(code: str, trade_date: date | None = None, session: AsyncSession = Depends(get_session),
                           user: User = Depends(get_current_user)):
    return await cached_json(f"options:{code}:exposures:{trade_date or 'latest'}",
                             lambda: service(session).options_exposures(code, trade_date), ttl=300)


class TradePlanRequest(BaseModel):
    direction: str | None = None
    instrument: str | None = None
    entry_trigger: str | None = None
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    horizon: str | None = None
    checklist: list[str] = Field(default_factory=list)


class OpportunityFollowRequest(BaseModel):
    state: Literal["following", "watching", "paused"] = "following"
    notes: str | None = Field(default=None, max_length=4000)


@router.get("/opportunities")
async def opportunities(scope: Literal["all", "global", "private"] = "all",
                        domain: str | None = Query(default=None, max_length=40),
                        state: str | None = Query(default=None, max_length=30),
                        followed: bool = False, limit: int = Query(100, ge=1, le=300),
                        offset: int = Query(0, ge=0), session: AsyncSession = Depends(get_session),
                        user: User = Depends(get_current_user)):
    return await OpportunityService(session, service(session), user.id).list(
        scope=scope, domain=domain, state=state, followed=followed, limit=limit, offset=offset)


@router.get("/opportunities/{opportunity_id}")
async def opportunity_detail(opportunity_id: UUID, session: AsyncSession = Depends(get_session),
                             user: User = Depends(get_current_user)):
    result = await OpportunityService(session, service(session), user.id).detail(opportunity_id)
    if result is None: raise HTTPException(404, "Opportunity not found")
    return result


@router.post("/opportunities/{opportunity_id}/follow")
async def opportunity_follow(opportunity_id: UUID, body: OpportunityFollowRequest,
                             session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await OpportunityService(session, service(session), user.id).follow(
            opportunity_id, state=body.state, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/opportunities/{opportunity_id}/follow")
async def opportunity_follow_update(opportunity_id: UUID, body: OpportunityFollowRequest,
                                    session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        return await OpportunityService(session, service(session), user.id).follow(
            opportunity_id, state=body.state, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/opportunities/{opportunity_id}/follow")
async def opportunity_unfollow(opportunity_id: UUID, session: AsyncSession = Depends(get_session),
                               user: User = Depends(get_current_user)):
    await OpportunityService(session, service(session), user.id).unfollow(opportunity_id)
    return {"ok": True}


@router.post("/opportunities/{opportunity_id}/trade-plan")
async def opportunity_trade_plan(opportunity_id: UUID, body: TradePlanRequest,
                                 session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    try:
        plan = await OpportunityService(session, service(session), user.id).create_trade_plan(
            opportunity_id, body.model_dump())
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return plan_payload(plan)


@router.get("/underlyings/{relationship}/{code}/series")
async def underlying_series(relationship: str, code: str, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"underlying:{relationship}:{code}", lambda: reader.underlying_series(relationship, code))
