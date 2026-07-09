"""
Market data API endpoints for charts
"""

import logging
from datetime import datetime
from typing import List, Optional

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

from core.auth import get_current_user, get_websocket_user
from core.database import get_session
from core.exceptions import InvalidTokenError
from core.i18n import get_request_locale, t
from domain.user.models import User
from services.market_data_service import MarketDataService
from services.market_data_websocket import market_data_ws_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-data"])

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
        await get_websocket_user(websocket, session)
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
