from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Awaitable, Callable, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from redis.exceptions import RedisError

from core.auth import get_current_user
from core.cache_service import get_cache_service
from core.database import get_session
from core.logging import get_logger
from domain.user.models import User
from domain.agentos.models import PortfolioAccount, PortfolioInstrument, PortfolioTransaction
from domain.agent_platform.models import MarketOpportunityRefreshState
from services.agent_platform.tushare import TushareReadService
from services.agent_platform.opportunities import OpportunityService, plan_payload
from services.agent_platform.publication_status import publication_version, read_publication_status
from services.agent_platform.capabilities import capability_version, read_capability_manifest
from services.agent_platform.market_cache import market_cache_key, market_last_good_key

router = APIRouter()
logger = get_logger(__name__)


async def cached_json(key: str, loader: Callable[[], Awaitable[dict[str, Any]]], ttl: int = 600,
                      request: Request | None = None) -> Response:
    started = time.perf_counter()
    cache = get_cache_service()
    version = publication_version()
    manifest_version = capability_version()
    cache_key = market_cache_key(key)
    cache_started = time.perf_counter()
    payload = await cache.get_async(cache_key)
    cache_ms = (time.perf_counter() - cache_started) * 1000
    cache_state = "hit"
    loader_ms = 0.0
    if not isinstance(payload, dict):
        cache_state = "miss"
        last_good_key = market_last_good_key(key)
        lock_key = f"{cache_key}:singleflight"
        lock_token = hashlib.sha256(f"{time.time_ns()}:{key}".encode()).hexdigest()
        acquired = False
        client = None
        try:
            client = await cache.async_client
            acquired = bool(await client.set(lock_key, lock_token, nx=True, ex=30))
        except RedisError:
            logger.warning("market_singleflight_unavailable", cache_key=key)
        if not acquired and client is not None:
            for _ in range(30):
                await asyncio.sleep(.1)
                payload = await cache.get_async(cache_key)
                if isinstance(payload, dict):
                    cache_state = "coalesced"
                    break
        try:
            if not isinstance(payload, dict):
                loader_started = time.perf_counter()
                try:
                    payload = await loader()
                    loader_ms = (time.perf_counter() - loader_started) * 1000
                    await cache.set_async(cache_key, payload, ttl=ttl)
                    metadata = payload.get("metadata") if isinstance(payload, dict) else None
                    if not isinstance(metadata, dict) or metadata.get("status") != "unavailable":
                        await cache.set_async(last_good_key, payload, ttl=604800)
                except (DBAPIError, TimeoutError):
                    payload = await cache.get_async(last_good_key)
                    if not isinstance(payload, dict):
                        raise
                    cache_state = "last-good"
                    loader_ms = (time.perf_counter() - loader_started) * 1000
        finally:
            if acquired and client is not None:
                try:
                    await client.eval(
                        "if redis.call('get',KEYS[1]) == ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end",
                        1, lock_key, lock_token,
                    )
                except RedisError:
                    logger.warning("market_singleflight_release_failed", cache_key=key)
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    etag = '"' + hashlib.sha256(body).hexdigest()[:24] + '"'
    elapsed_ms = (time.perf_counter() - started) * 1000
    headers = {
        "Cache-Control": "private, max-age=60, stale-while-revalidate=300",
        "ETag": etag, "X-Market-Cache": cache_state, "X-Market-Publication": version,
        "X-Market-Capabilities": manifest_version,
        "X-Payload-Bytes": str(len(body)),
        "Server-Timing": f'cache;dur={cache_ms:.1f}, loader;dur={loader_ms:.1f}, total;dur={elapsed_ms:.1f};desc="{cache_state}"',
    }
    logger.info("market_read", cache_key=key, cache=cache_state, duration_ms=round(elapsed_ms, 1),
                cache_ms=round(cache_ms, 1), loader_ms=round(loader_ms, 1),
                payload_bytes=len(body))
    if request and request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)


def service(session: AsyncSession) -> TushareReadService:
    return TushareReadService(session)


@router.get("/data-status")
async def data_status(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    """Read source coverage and background refresh state without triggering ingestion."""
    refresh_rows = (await session.execute(select(MarketOpportunityRefreshState).order_by(
        MarketOpportunityRefreshState.domain))).scalars().all()
    return {
        "publication": read_publication_status(),
        "capabilities": {key: value for key, value in read_capability_manifest().items() if key != "capabilities"},
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


@router.get("/capabilities")
async def capabilities(user: User = Depends(get_current_user)):
    """Return the complete physical and planned market-data exposure contract."""
    return read_capability_manifest()


@router.get("/capital")
async def market_capital(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("capital:all-raw-history", service(session).market_capital_snapshot)


@router.get("/valuation-board")
async def valuation_board(request: Request, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("valuation-board:v5", service(session).valuation_snapshot, request=request)


@router.get("/valuation/history")
async def valuation_history(request: Request, code: str = Query(..., min_length=1, max_length=20),
                            universe: Literal["broad", "sw_l1"] = Query(...),
                            limit: int = Query(252, ge=1, le=1300),
                            session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    normalized = code.strip().upper()
    return await cached_json(
        f"valuation:history:v2:{universe}:{normalized}:{limit}",
        lambda: service(session).valuation_history(normalized, universe, limit), ttl=60, request=request,
    )


def _a_share_provider_symbol(instrument: PortfolioInstrument) -> str | None:
    if instrument.market.upper() != "CN" or instrument.instrument_type != "stock":
        return None
    value = str(instrument.provider_symbol or instrument.symbol or "").strip().upper()
    if value.endswith((".SH", ".SZ", ".BJ")):
        return value
    if len(value) == 6 and value.isdigit():
        suffix = "SH" if value[0] in {"5", "6", "9"} else "BJ" if value[0] in {"4", "8"} else "SZ"
        return f"{value}.{suffix}"
    return value or None


async def _held_a_share_symbols(session: AsyncSession, user_id: UUID) -> list[str]:
    rows = (await session.execute(select(
        PortfolioTransaction, PortfolioInstrument,
    ).join(PortfolioAccount, PortfolioAccount.id == PortfolioTransaction.account_id).outerjoin(
        PortfolioInstrument, PortfolioInstrument.id == PortfolioTransaction.instrument_id,
    ).where(
        PortfolioTransaction.user_id == user_id,
        PortfolioAccount.user_id == user_id,
        PortfolioAccount.status == "active",
    ).order_by(
        PortfolioTransaction.account_id, PortfolioTransaction.trade_date, PortfolioTransaction.created_at,
    ))).all()
    positions: dict[tuple[UUID, UUID], Decimal] = defaultdict(Decimal)
    instruments: dict[tuple[UUID, UUID], PortfolioInstrument] = {}
    for transaction, instrument in rows:
        if instrument is None:
            continue
        key = (transaction.account_id, instrument.id)
        quantity = Decimal(transaction.quantity)
        if instrument.direction == "short" and transaction.transaction_type in {"buy", "sell"}:
            quantity = -abs(quantity) if transaction.transaction_type == "buy" else abs(quantity)
        elif transaction.transaction_type in {"sell", "reduced", "close", "redeem"}:
            quantity = -abs(quantity)
        elif transaction.transaction_type in {"buy", "opening", "increased", "subscribe"}:
            quantity = abs(quantity)
        positions[key] += quantity
        instruments[key] = instrument
    return sorted({symbol for key, quantity in positions.items() if quantity != 0
                   if (symbol := _a_share_provider_symbol(instruments[key])) is not None})


@router.get("/valuation/held-industries")
async def valuation_held_industries(session: AsyncSession = Depends(get_session),
                                    user: User = Depends(get_current_user)):
    """Map the user's non-zero active-account A-share positions to the published SW L1 map."""
    symbols = await _held_a_share_symbols(session, user.id)
    payload = await service(session).valuation_snapshot(include_membership=True)
    membership = payload.pop("membership_map", {})
    mapped = {symbol: membership[symbol] for symbol in symbols if symbol in membership}
    missing = [symbol for symbol in symbols if symbol not in membership]
    industries = {str(value["code"]): {"code": str(value["code"]), "name": str(value.get("name") or value["code"])}
                  for value in mapped.values()}
    total = len(symbols)
    return {
        "metadata": payload.get("metadata") or {},
        "industry_codes": sorted(industries), "industries": list(industries.values()),
        "position_symbols": symbols, "mapped_symbols": mapped, "missing_symbols": missing,
        "coverage": len(mapped) / total if total else 0.0,
        "covered": len(mapped), "eligible": total,
    }


@router.get("/correlations")
async def correlations(request: Request, window: int = Query(60, ge=20, le=252), session: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user)):
    return await cached_json(f"correlations:v2:{window}", lambda: service(session).correlation_snapshot(window), request=request)


@router.get("/correlations/history")
async def correlations_history(request: Request, window: int = Query(60, ge=20, le=252),
                               limit: int = Query(756, ge=20, le=1300),
                               session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json(f"correlations:history:v1:{window}:{limit}",
                             lambda: service(session).correlation_history(window, limit), ttl=900, request=request)


@router.get("/factors")
async def factors(request: Request, session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("factors:kt_factor_v1:materialized", service(session).factor_snapshot, ttl=900, request=request)


@router.get("/factors/history")
async def factors_history(request: Request, limit: int = Query(756, ge=20, le=1300),
                          session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json(f"factors:history:v1:{limit}", lambda: service(session).factor_history(limit),
                             ttl=900, request=request)


@router.get("/macro/series")
async def macro_catalog(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json("macro:catalog", reader.macro_catalog)


@router.get("/rates/catalog")
async def rates_catalog(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    return await cached_json("rates:catalog", service(session).rates_catalog)


@router.get("/rates/series/{key}")
async def rates_series(key: str, field: str | None = None, bank: str | None = None, maturity: str | None = None,
                       session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    try:
        return await cached_json(f"rates:{key}:{field or 'analysis-v1'}:{bank or '-'}:{maturity or '-'}",
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
async def macro_series(key: str, field: str | None = None, session: AsyncSession = Depends(get_session),
                       user: User = Depends(get_current_user)):
    reader = service(session)
    try:
        return await cached_json(f"macro:{key}:{field or 'analysis-v1'}", lambda: reader.macro_series(key, field))
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
