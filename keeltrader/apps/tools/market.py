"""Market data tools — get_price, get_klines, calc_indicators.

Wraps CCXT for exchange data and computes technical indicators.
These tools are registered on PydanticAI agents via the registry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import ccxt.async_support as ccxt
import numpy as np

from ._proxy import apply_proxy

logger = logging.getLogger(__name__)

# Shared exchange instances (lazy init)
_exchanges: dict[str, ccxt.Exchange] = {}


async def _get_exchange(name: str = "okx") -> ccxt.Exchange:
    """Get or create a CCXT exchange instance (public data only, no API keys)."""
    if name not in _exchanges:
        exchange_class = getattr(ccxt, name, None)
        if exchange_class is None:
            raise ValueError(f"Unknown exchange: {name}")
        _exchanges[name] = exchange_class(apply_proxy({"enableRateLimit": True}))
    return _exchanges[name]


async def get_price(
    symbol: str,
    exchange: str = "okx",
) -> dict[str, Any]:
    """Get real-time price for a symbol.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        exchange: Exchange name (default: binance)

    Returns:
        Dict with symbol, price, bid, ask, timestamp, change_24h
    """
    ex = await _get_exchange(exchange)
    try:
        ticker = await ex.fetch_ticker(symbol)
        return {
            "symbol": symbol,
            "exchange": exchange,
            "price": ticker.get("last"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "high_24h": ticker.get("high"),
            "low_24h": ticker.get("low"),
            "volume_24h": ticker.get("baseVolume"),
            "change_24h": ticker.get("change"),
            "change_pct_24h": ticker.get("percentage"),
            "timestamp": ticker.get("datetime"),
        }
    except Exception as e:
        logger.error("get_price failed for %s on %s: %s", symbol, exchange, e)
        return {"symbol": symbol, "exchange": exchange, "error": str(e)}


async def get_klines(
    symbol: str,
    interval: str = "1h",
    limit: int = 100,
    exchange: str = "okx",
) -> list[dict[str, Any]]:
    """Get K-line (candlestick) data.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
        limit: Number of candles (max 500)
        exchange: Exchange name

    Returns:
        List of candle dicts with time, open, high, low, close, volume
    """
    ex = await _get_exchange(exchange)
    limit = min(limit, 500)
    try:
        ohlcv = await ex.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        return [
            {
                "time": datetime.utcfromtimestamp(c[0] / 1000).isoformat(),
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            }
            for c in ohlcv
        ]
    except Exception as e:
        logger.error("get_klines failed for %s: %s", symbol, e)
        return []


async def get_orderbook(
    symbol: str,
    depth: int = 10,
    exchange: str = "okx",
) -> dict[str, Any]:
    """Get order book depth.

    Args:
        symbol: Trading pair
        depth: Number of levels per side
        exchange: Exchange name

    Returns:
        Dict with bids, asks, spread
    """
    ex = await _get_exchange(exchange)
    try:
        book = await ex.fetch_order_book(symbol, limit=depth)
        best_bid = book["bids"][0][0] if book["bids"] else 0
        best_ask = book["asks"][0][0] if book["asks"] else 0
        return {
            "symbol": symbol,
            "bids": [{"price": b[0], "amount": b[1]} for b in book["bids"][:depth]],
            "asks": [{"price": a[0], "amount": a[1]} for a in book["asks"][:depth]],
            "spread": best_ask - best_bid if best_bid and best_ask else 0,
            "spread_pct": ((best_ask - best_bid) / best_bid * 100) if best_bid else 0,
        }
    except Exception as e:
        logger.error("get_orderbook failed for %s: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}


async def get_funding_rate(
    symbol: str,
    exchange: str = "okx",
    trading_mode: str = "swap",
) -> dict[str, Any]:
    """Get current funding rate for perpetual contracts.

    Args:
        symbol: Trading pair (e.g., "BTC/USDT")
        exchange: Exchange name
        trading_mode: "spot" or "swap"

    Returns:
        Dict with funding_rate, next_funding_time
    """
    if trading_mode == "spot":
        return {"symbol": symbol, "info": "Funding rate not applicable in spot mode"}
    ex = await _get_exchange(exchange)
    try:
        funding = await ex.fetch_funding_rate(symbol)
        return {
            "symbol": symbol,
            "funding_rate": funding.get("fundingRate"),
            "funding_timestamp": funding.get("fundingDatetime"),
            "next_funding_time": funding.get("nextFundingDatetime"),
            "mark_price": funding.get("markPrice"),
            "index_price": funding.get("indexPrice"),
        }
    except Exception as e:
        logger.error("get_funding_rate failed for %s: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}


def calc_indicators(
    klines: list[dict[str, Any]],
    indicators: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate technical indicators from kline data.

    Args:
        klines: List of candle dicts from get_klines()
        indicators: List of indicator names to calculate.
            Supported: rsi, macd, bb (bollinger bands), ema, sma, atr, volume_profile

    Returns:
        Dict of indicator name -> values/signals
    """
    if not klines:
        return {"error": "No kline data"}

    if indicators is None:
        indicators = ["rsi", "macd", "bb", "ema", "sma"]

    closes = np.array([k["close"] for k in klines], dtype=float)
    highs = np.array([k["high"] for k in klines], dtype=float)
    lows = np.array([k["low"] for k in klines], dtype=float)
    volumes = np.array([k["volume"] for k in klines], dtype=float)

    result: dict[str, Any] = {
        "symbol": klines[0].get("symbol", ""),
        "candle_count": len(klines),
        "latest_close": float(closes[-1]),
        "latest_time": klines[-1].get("time", ""),
    }

    for ind in indicators:
        ind = ind.lower()
        if ind == "rsi":
            result["rsi"] = _calc_rsi(closes)
        elif ind == "macd":
            result["macd"] = _calc_macd(closes)
        elif ind == "bb":
            result["bollinger_bands"] = _calc_bollinger(closes)
        elif ind == "ema":
            result["ema"] = {
                "ema_12": float(_ema(closes, 12)[-1]) if len(closes) >= 12 else None,
                "ema_26": float(_ema(closes, 26)[-1]) if len(closes) >= 26 else None,
                "ema_50": float(_ema(closes, 50)[-1]) if len(closes) >= 50 else None,
            }
        elif ind == "sma":
            result["sma"] = {
                "sma_20": float(np.mean(closes[-20:])) if len(closes) >= 20 else None,
                "sma_50": float(np.mean(closes[-50:])) if len(closes) >= 50 else None,
                "sma_200": float(np.mean(closes[-200:])) if len(closes) >= 200 else None,
            }
        elif ind == "atr":
            result["atr"] = _calc_atr(highs, lows, closes)
        elif ind == "volume_profile":
            result["volume_profile"] = {
                "avg_volume": float(np.mean(volumes)),
                "volume_trend": "increasing" if volumes[-1] > np.mean(volumes[-10:]) else "decreasing",
                "relative_volume": float(volumes[-1] / np.mean(volumes[-20:])) if len(volumes) >= 20 else 1.0,
            }

    return result


def _calc_rsi(closes: np.ndarray, period: int = 14) -> dict[str, Any]:
    """Calculate RSI."""
    if len(closes) < period + 1:
        return {"value": None, "signal": "insufficient_data"}
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    signal = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
    return {"value": round(rsi, 2), "period": period, "signal": signal}


def _calc_macd(
    closes: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9
) -> dict[str, Any]:
    """Calculate MACD."""
    if len(closes) < slow + signal_period:
        return {"macd_line": None, "signal_line": None, "histogram": None, "signal": "insufficient_data"}
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    cross = "bullish_cross" if histogram[-1] > 0 and histogram[-2] <= 0 else \
            "bearish_cross" if histogram[-1] < 0 and histogram[-2] >= 0 else \
            "bullish" if histogram[-1] > 0 else "bearish"
    return {
        "macd_line": round(float(macd_line[-1]), 4),
        "signal_line": round(float(signal_line[-1]), 4),
        "histogram": round(float(histogram[-1]), 4),
        "signal": cross,
    }


def _calc_bollinger(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> dict[str, Any]:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None, "signal": "insufficient_data"}
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    price = closes[-1]
    pct_b = (price - lower) / (upper - lower) if upper != lower else 0.5
    signal = "near_upper" if pct_b > 0.8 else "near_lower" if pct_b < 0.2 else "middle"
    return {
        "upper": round(float(upper), 2),
        "middle": round(float(sma), 2),
        "lower": round(float(lower), 2),
        "bandwidth": round(float((upper - lower) / sma * 100), 2),
        "pct_b": round(float(pct_b), 2),
        "signal": signal,
    }


def _calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> dict[str, Any]:
    """Calculate Average True Range."""
    if len(closes) < period + 1:
        return {"value": None}
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1]),
        ),
    )
    atr = np.mean(tr[-period:])
    return {
        "value": round(float(atr), 4),
        "pct": round(float(atr / closes[-1] * 100), 2),
    }


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    alpha = 2.0 / (period + 1)
    result = np.zeros_like(data)
    result[0] = data[0]
    for i in range(1, len(data)):
        result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
    return result
