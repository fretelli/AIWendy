"""Shared market data type contracts."""

from typing import TypedDict


class PricePoint(TypedDict):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class RealTimeQuote(TypedDict):
    symbol: str
    price: float
    change: float
    change_percent: float
    timestamp: str
    volume: int


class IndicatorPoint(TypedDict):
    time: str
    value: float
