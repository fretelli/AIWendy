"""
Exchange API endpoints for connecting to crypto exchanges
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core.i18n import get_request_locale, t
from services.exchange_service import ExchangeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])

# Initialize service
exchange_service = ExchangeService()


class ExchangeInfo(BaseModel):
    """Exchange information"""
    name: str


class Balance(BaseModel):
    """Balance information"""
    exchange: str
    timestamp: str
    total: dict
    free: dict
    used: dict


class Position(BaseModel):
    """Position information"""
    symbol: str
    side: str
    contracts: float
    notional: float
    leverage: float
    entry_price: Optional[float] = None
    mark_price: Optional[float] = None
    liquidation_price: Optional[float] = None
    unrealized_pnl: float
    percentage: float
    timestamp: Optional[int] = None


class Order(BaseModel):
    """Order information"""
    id: str
    symbol: str
    type: str
    side: str
    price: Optional[float] = None
    amount: float
    filled: float
    remaining: float
    status: str
    timestamp: Optional[int] = None
    datetime: Optional[str] = None


class Trade(BaseModel):
    """Trade information"""
    id: str
    order_id: Optional[str] = None
    symbol: str
    type: Optional[str] = None
    side: str
    price: float
    amount: float
    cost: float
    fee: Optional[dict] = None
    timestamp: Optional[int] = None
    datetime: Optional[str] = None


class Market(BaseModel):
    """Market information"""
    symbol: str
    base: str
    quote: str
    active: bool
    type: str
    spot: bool
    future: bool
    swap: bool


@router.get("/", response_model=List[ExchangeInfo])
async def get_exchanges(http_request: Request):
    """
    Get list of configured exchanges

    Returns:
        List of available exchanges
    """
    try:
        exchanges = exchange_service.get_available_exchanges()
        return [{"name": name} for name in exchanges]
    except Exception as e:
        locale = get_request_locale(http_request)
        logger.error(f"Error fetching exchanges: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_fetch_failed", locale)
        )


@router.get("/{exchange_name}/balance", response_model=Balance)
async def get_balance(exchange_name: str, http_request: Request):
    """
    Get account balance from exchange

    Args:
        exchange_name: Name of the exchange (binance, okx, bybit)

    Returns:
        Balance information
    """
    locale = get_request_locale(http_request)
    try:
        balance = await exchange_service.get_balance(exchange_name.lower())

        if not balance:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_not_configured", locale, exchange=exchange_name)
            )

        return balance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching balance: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_balance_failed", locale)
        )


@router.get("/{exchange_name}/positions", response_model=List[Position])
async def get_positions(exchange_name: str, http_request: Request):
    """
    Get open positions from exchange

    Args:
        exchange_name: Name of the exchange

    Returns:
        List of open positions
    """
    locale = get_request_locale(http_request)
    try:
        positions = await exchange_service.get_positions(exchange_name.lower())

        if positions is None:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_not_configured", locale, exchange=exchange_name)
            )

        return positions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_positions_failed", locale)
        )


@router.get("/{exchange_name}/orders", response_model=List[Order])
async def get_open_orders(
    exchange_name: str,
    http_request: Request,
    symbol: Optional[str] = Query(None, description="Symbol to filter orders")
):
    """
    Get open orders from exchange

    Args:
        exchange_name: Name of the exchange
        symbol: Optional symbol to filter orders

    Returns:
        List of open orders
    """
    locale = get_request_locale(http_request)
    try:
        orders = await exchange_service.get_open_orders(exchange_name.lower(), symbol)

        if orders is None:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_not_configured", locale, exchange=exchange_name)
            )

        return orders
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_orders_failed", locale)
        )


@router.get("/{exchange_name}/trades", response_model=List[Trade])
async def get_trade_history(
    exchange_name: str,
    http_request: Request,
    symbol: Optional[str] = Query(None, description="Symbol to filter trades"),
    since: Optional[int] = Query(None, description="Timestamp in milliseconds"),
    limit: int = Query(100, description="Maximum number of trades", ge=1, le=1000)
):
    """
    Get trade history from exchange

    Args:
        exchange_name: Name of the exchange
        symbol: Optional symbol to filter trades
        since: Timestamp in milliseconds to fetch trades from
        limit: Maximum number of trades to return

    Returns:
        List of trades
    """
    locale = get_request_locale(http_request)
    try:
        trades = await exchange_service.get_trade_history(
            exchange_name.lower(),
            symbol=symbol,
            since=since,
            limit=limit
        )

        if trades is None:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_not_configured", locale, exchange=exchange_name)
            )

        return trades
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_trades_failed", locale)
        )


@router.get("/{exchange_name}/markets", response_model=List[Market])
async def get_markets(exchange_name: str, http_request: Request):
    """
    Get available trading markets from exchange

    Args:
        exchange_name: Name of the exchange

    Returns:
        List of available markets
    """
    locale = get_request_locale(http_request)
    try:
        markets = await exchange_service.get_markets(exchange_name.lower())

        if markets is None:
            raise HTTPException(
                status_code=404,
                detail=t("errors.exchange_not_configured", locale, exchange=exchange_name)
            )

        return markets
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        raise HTTPException(
            status_code=500,
            detail=t("errors.exchange_markets_failed", locale)
        )


@router.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown"""
    exchange_service.close()
