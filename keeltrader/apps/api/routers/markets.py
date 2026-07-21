from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from core.cache_service import get_cache_service
from core.database import get_session
from core.logging import get_logger
from domain.user.models import User
from services.agent_platform.tushare import TushareReadService

router = APIRouter()
logger = get_logger(__name__)


async def cached_json(key: str, loader: Callable[[], Awaitable[dict[str, Any]]], ttl: int = 600) -> Response:
    started = time.perf_counter()
    cache = get_cache_service()
    payload = await cache.get_async(f"markets:v3:{key}")
    cache_state = "hit"
    if not isinstance(payload, dict):
        payload = await loader()
        await cache.set_async(f"markets:v3:{key}", payload, ttl=ttl)
        cache_state = "miss"
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode()
    etag = '"' + hashlib.sha256(body).hexdigest()[:24] + '"'
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info("market_read", cache_key=key, cache=cache_state, duration_ms=round(elapsed_ms, 1),
                payload_bytes=len(body))
    return Response(content=body, media_type="application/json", headers={
        "Cache-Control": "private, max-age=60, stale-while-revalidate=300",
        "ETag": etag, "X-Market-Cache": cache_state, "X-Payload-Bytes": str(len(body)),
        "Server-Timing": f'market;dur={elapsed_ms:.1f};desc="{cache_state}"',
    })


def service(session: AsyncSession) -> TushareReadService:
    return TushareReadService(session)


@router.get("/macro/series")
async def macro_catalog(session: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json("macro:catalog", reader.macro_catalog)


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


@router.get("/underlyings/{relationship}/{code}/series")
async def underlying_series(relationship: str, code: str, session: AsyncSession = Depends(get_session),
                            user: User = Depends(get_current_user)):
    reader = service(session)
    return await cached_json(f"underlying:{relationship}:{code}", lambda: reader.underlying_series(relationship, code))
