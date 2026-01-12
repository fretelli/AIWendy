"""
Market data API endpoints for charts
"""

from datetime import datetime
from typing import List, Optional

from core.i18n import get_request_locale, t
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from services.market_data_service import MarketDataService

router = APIRouter(prefix="/api/market-data", tags=["market-data"])

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
async def get_real_time_price(symbol: str, http_request: Request):
    """
    Get real-time price for a symbol

    Args:
        symbol: Stock symbol

    Returns:
        Current price data
    """
    locale = get_request_locale(http_request)
    try:
        data = await market_data_service.get_real_time_price(symbol.upper())

        if not data:
            raise HTTPException(
                status_code=404,
                detail=t("errors.market_data_not_found", locale, symbol=symbol.upper()),
            )

        return data
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
    http_request: Request, query: str = Query(..., description="Search query")
):
    """
    Search for symbols by name or ticker

    Args:
        query: Search query

    Returns:
        List of matching symbols
    """
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


@router.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown"""
    await market_data_service.close()
