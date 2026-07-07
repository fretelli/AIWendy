"""
Market data API endpoints for charts
"""

import logging
from datetime import datetime
from typing import List, Optional

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel

from config import get_settings
from core.auth import GUEST_EMAIL, _ensure_guest_user, decode_token, get_current_user
from core.cache import get_redis_client
from core.database import get_session
from core.exceptions import InvalidTokenError
from core.i18n import get_request_locale, t
from domain.user.models import User
from services.market_data_service import MarketDataService
from services.market_data_websocket import market_data_ws_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-data"])
ACCESS_TOKEN_COOKIE = "keeltrader_access_token"

# Initialize service
market_data_service = MarketDataService()


class PriceData(BaseModel):
    """Price data response model"""

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class RealTimePrice(BaseModel):
    """Real-time price response model"""

    symbol: str
    price: float
    change: float
    change_percent: float
    timestamp: str
    volume: int


class IndicatorData(BaseModel):
    """Technical indicator response model"""

    time: str
    value: float


def _extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    authorization = websocket.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return websocket.cookies.get(ACCESS_TOKEN_COOKIE)


async def authenticate_market_data_websocket(
    websocket: WebSocket,
    session: AsyncSession,
) -> User:
    """Authenticate a market-data WebSocket using bearer header or auth cookie."""
    settings = get_settings()
    token = _extract_websocket_token(websocket)
    if not token:
        if settings.auth_required:
            raise InvalidTokenError()
        return await _ensure_guest_user(session)

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise InvalidTokenError()

        user_id = payload.get("sub")
        session_id = payload.get("session_id")
        if not user_id:
            raise InvalidTokenError()

        if session_id:
            redis_client = get_redis_client()
            stored_user_id = redis_client.get(f"session:{session_id}")
            if not stored_user_id or str(stored_user_id) != str(user_id):
                raise InvalidTokenError()
    except (InvalidTokenError, JWTError):
        if not settings.auth_required:
            return await _ensure_guest_user(session)
        raise InvalidTokenError()

    result = await session.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        if not settings.auth_required:
            return await _ensure_guest_user(session)
        raise InvalidTokenError()
    if getattr(user, "email", None) == GUEST_EMAIL and settings.auth_required:
        raise InvalidTokenError()
    return user


@router.get("/historical/{symbol}", response_model=List[PriceData])
async def get_historical_data(
    symbol: str,
    http_request: Request,
    interval: str = Query(
        "1day",
        description="Time interval (1min, 5min, 15min, 30min, 1h, 1day, 1week, 1month)",
    ),
    outputsize: int = Query(60, description="Number of data points", ge=1, le=500),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user),
):
    """
    Get historical price data for a symbol

    Args:
        symbol: Stock symbol (e.g., "AAPL", "SPY")
        interval: Time interval
        outputsize: Number of data points to return
        start_date: Optional start date
        end_date: Optional end date

    Returns:
        List of OHLCV data points
    """
    del current_user
    locale = get_request_locale(http_request)
    try:
        # Parse dates if provided
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        # Fetch data
        data = await market_data_service.get_historical_data(
            symbol=symbol.upper(),
            interval=interval,
            outputsize=outputsize,
            start_date=start_dt,
            end_date=end_dt,
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail=t("errors.market_data_not_found", locale, symbol=symbol.upper()),
            )

        return data
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=t("errors.invalid_date_format", locale, error=str(e)),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=t("errors.market_data_fetch_failed", locale)
        )


@router.get("/real-time/{symbol}", response_model=RealTimePrice)
async def get_real_time_price(
    symbol: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get real-time price for a symbol

    Args:
        symbol: Stock symbol

    Returns:
        Current price data
    """
    del current_user
    locale = get_request_locale(http_request)
    try:
        data = await market_data_service.get_real_time_price(symbol.upper())

        if not data:
            raise HTTPException(
                status_code=404,
                detail=t("errors.market_data_not_found", locale, symbol=symbol.upper()),
            )

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=t("errors.market_data_fetch_failed", locale)
        )


@router.get("/indicators/{symbol}/{indicator}", response_model=List[IndicatorData])
async def get_technical_indicators(
    symbol: str,
    indicator: str,
    http_request: Request,
    interval: str = Query("1day", description="Time interval"),
    period: int = Query(20, description="Period for the indicator", ge=5, le=200),
    current_user: User = Depends(get_current_user),
):
    """
    Get technical indicators for a symbol

    Args:
        symbol: Stock symbol
        indicator: Indicator type (sma, ema, rsi, macd, bbands)
        interval: Time interval
        period: Period for the indicator

    Returns:
        List of indicator values
    """
    del current_user
    locale = get_request_locale(http_request)
    try:
        valid_indicators = ["sma", "ema", "rsi", "macd", "bbands"]
        if indicator not in valid_indicators:
            raise HTTPException(
                status_code=400,
                detail=t(
                    "errors.invalid_indicator",
                    locale,
                    valid=", ".join(valid_indicators),
                ),
            )

        data = await market_data_service.get_technical_indicators(
            symbol=symbol.upper(), interval=interval, indicator=indicator, period=period
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail=t(
                    "errors.market_indicator_data_not_found",
                    locale,
                    symbol=symbol.upper(),
                ),
            )

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=t("errors.market_indicators_failed", locale)
        )


@router.get("/symbols/search")
async def search_symbols(
    http_request: Request,
    query: str = Query(..., description="Search query"),
    current_user: User = Depends(get_current_user),
):
    """
    Search for symbols by name or ticker

    Args:
        query: Search query

    Returns:
        List of matching symbols
    """
    del current_user
    locale = get_request_locale(http_request)
    try:
        # For now, return common symbols
        # In production, integrate with a symbol search API
        common_symbols = [
            {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "type": "ETF"},
            {"symbol": "QQQ", "name": "Invesco QQQ Trust", "type": "ETF"},
            {"symbol": "AAPL", "name": "Apple Inc.", "type": "Stock"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "Stock"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "Stock"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "Stock"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "type": "Stock"},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Stock"},
            {"symbol": "META", "name": "Meta Platforms Inc.", "type": "Stock"},
            {"symbol": "BTC", "name": "Bitcoin", "type": "Crypto"},
            {"symbol": "ETH", "name": "Ethereum", "type": "Crypto"},
        ]

        # Filter based on query
        query_lower = query.lower()
        results = [
            s
            for s in common_symbols
            if query_lower in s["symbol"].lower() or query_lower in s["name"].lower()
        ]

        return results
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=t("errors.market_symbol_search_failed", locale)
        )


@router.websocket("/ws/{symbol}")
async def websocket_endpoint(
    websocket: WebSocket,
    symbol: str,
    session: AsyncSession = Depends(get_session),
):
    """
    WebSocket endpoint for real-time price updates

    Args:
        websocket: WebSocket connection
        symbol: Stock symbol to subscribe to

    Usage:
        ws://localhost:8000/api/market-data/ws/AAPL
    """
    try:
        await authenticate_market_data_websocket(websocket, session)
    except InvalidTokenError:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    try:
        # Connect to Twelve Data if not already connected
        if not market_data_ws_service.is_connected:
            await market_data_ws_service.connect_to_twelve_data()

        # Subscribe to the symbol
        await market_data_ws_service.subscribe(websocket, symbol.upper())

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (like unsubscribe requests)
                data = await websocket.receive_json()

                if data.get("action") == "unsubscribe":
                    await market_data_ws_service.unsubscribe(websocket, symbol.upper())
                    break
                elif data.get("action") == "subscribe":
                    new_symbol = data.get("symbol", "").upper()
                    if new_symbol:
                        await market_data_ws_service.subscribe(websocket, new_symbol)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                break

    finally:
        # Clean up on disconnect
        await market_data_ws_service.disconnect(websocket)
